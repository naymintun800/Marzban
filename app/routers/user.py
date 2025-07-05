from datetime import datetime, timedelta, timezone
from typing import List, Optional, Union
import json
import re # Added for username sanitization

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError

from app import logger, xray
from app.db import Session, crud, get_db
from app.dependencies import get_expired_users_list, get_validated_user, validate_dates
from app.models.admin import Admin
from app.models.user import (
    UserCreate,
    UserModify,
    UserResponse,
    UsersResponse,
    UserStatus,
    UsersUsagesResponse,
    UserUsagesResponse,
    UserDataLimitResetStrategy,
)
from app.utils import report, responses

# Placeholder for Hiddify Import specific models
class HiddifyImportConfig(BaseModel):
    set_unlimited_expire: bool
    enable_smart_username_parsing: bool
    protocols: List[str]

# TODO: Define a more detailed response model for import summary
class HiddifyImportResponse(BaseModel):
    successful_imports: int
    failed_imports: int
    errors: List[str]

# Regex for Marzban username validation (from User model, slightly simplified for generation)
# Original: ^(?=\w{3,32}\b)[a-zA-Z0-9-_@.]+(?:_[a-zA-Z0-9-_@.]+)*$
# For generation, we focus on allowed characters and length.
# We will ensure the _ is not at the start/end and no consecutive _ via replacement passes.
MARZBAN_USERNAME_ALLOWED_CHARS = re.compile(r"[^a-zA-Z0-9_@.]")
MARZBAN_USERNAME_MAX_LEN = 32
MARZBAN_USERNAME_MIN_LEN = 3

# Hiddify specific constants for mapping
HIDDIFY_PACKAGE_DAYS_UNLIMITED_THRESHOLD = 365 * 10  # 10 years
HIDDIFY_MODE_TO_MARZBAN_RESET_STRATEGY = {
    "no_reset": UserDataLimitResetStrategy.no_reset,
    "monthly": UserDataLimitResetStrategy.month,
    "weekly": UserDataLimitResetStrategy.week,
    "daily": UserDataLimitResetStrategy.day,
    # Add other mappings if Hiddify has more, e.g., yearly
    # "yearly": UserDataLimitResetStrategy.year, # Example, confirm Hiddify value
}

def _sanitize_raw_username(name: str, h_uuid: str) -> str:
    """Internal helper to generate a base username, focusing on allowed chars and length."""
    # Replace disallowed characters with underscore
    sanitized = MARZBAN_USERNAME_ALLOWED_CHARS.sub("_", name)
    # Remove leading/trailing underscores that might have been introduced
    sanitized = sanitized.strip("_")
    # Replace multiple consecutive underscores with a single one
    sanitized = re.sub(r"_{2,}", "_", sanitized)

    # Ensure minimum length
    if len(sanitized) < MARZBAN_USERNAME_MIN_LEN:
        # If too short after sanitization (or was empty), use a UUID-based fallback
        # Ensure it starts with a letter, as per common username conventions, though regexp allows numbers
        return f"h_user_{h_uuid[:8]}" # Ensure this fallback is valid

    # Ensure maximum length
    return sanitized[:MARZBAN_USERNAME_MAX_LEN]

def generate_unique_marzban_username(db: Session, base_username: str, h_uuid: str) -> str:
    """Generates a unique Marzban username, appending a suffix if needed."""
    # First, try the base_username as is, if it's valid
    temp_username = _sanitize_raw_username(base_username, h_uuid)

    # Check if the (potentially sanitized) username is valid according to Marzban rules
    # This is a simplified check; User model validation is the ultimate source of truth
    if not (MARZBAN_USERNAME_MIN_LEN <= len(temp_username) <= MARZBAN_USERNAME_MAX_LEN and \
            not temp_username.startswith("_") and not temp_username.endswith("_") and \
            "__" not in temp_username and MARZBAN_USERNAME_ALLOWED_CHARS.sub("", temp_username) == temp_username):
        # If sanitization itself leads to an invalid format (e.g. too short, or only special chars that got removed)
        # or if the original base_username was something like purely numeric that got truncated too short.
        temp_username = f"h_user_{h_uuid[:max(MARZBAN_USERNAME_MIN_LEN, MARZBAN_USERNAME_MAX_LEN - 7)]}"
        # Ensure this fallback is also sanitized, though it should be by construction
        temp_username = _sanitize_raw_username(temp_username, h_uuid)


    candidate_username = temp_username
    suffix = 1
    while crud.get_user(db, candidate_username):
        # If conflict, generate a new name. Max length needs to be considered for suffix.
        base_len = len(temp_username)
        suffix_str = f"_{suffix}"
        if base_len + len(suffix_str) > MARZBAN_USERNAME_MAX_LEN:
            # Truncate base_username to make space for suffix
            candidate_username = temp_username[:MARZBAN_USERNAME_MAX_LEN - len(suffix_str)] + suffix_str
        else:
            candidate_username = temp_username + suffix_str
        suffix += 1
        if suffix > 999: # Safety break for extreme cases
            logger.error(f"Could not generate unique username for base '{base_username}' and UUID '{h_uuid}' after 999 tries.")
            # Fallback to a more unique name if suffixing fails badly
            return f"h_err_{h_uuid[:MARZBAN_USERNAME_MAX_LEN-6]}"
    return candidate_username

router = APIRouter(tags=["User"], prefix="/api", responses={401: responses._401})


@router.post("/user", response_model=UserResponse, responses={400: responses._400, 409: responses._409})
def add_user(
    new_user: UserCreate,
    bg: BackgroundTasks,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    """
    Add a new user

    - **username**: 3 to 32 characters, can include a-z, 0-9, and underscores.
    - **status**: User's status, defaults to `active`. Special rules if `on_hold`.
    - **expire**: UTC timestamp for account expiration. Use `0` for unlimited.
    - **data_limit**: Max data usage in bytes (e.g., `1073741824` for 1GB). `0` means unlimited.
    - **data_limit_reset_strategy**: Defines how/if data limit resets. `no_reset` means it never resets.
    - **proxies**: Dictionary of protocol settings (e.g., `vmess`, `vless`).
    - **inbounds**: Dictionary of protocol tags to specify inbound connections.
    - **note**: Optional text field for additional user information or notes.
    - **on_hold_timeout**: UTC timestamp when `on_hold` status should start or end.
    - **on_hold_expire_duration**: Duration (in seconds) for how long the user should stay in `on_hold` status.
    - **next_plan**: Next user plan (resets after use).
    """

    # TODO expire should be datetime instead of timestamp

    for proxy_type in new_user.proxies:
        if not xray.config.inbounds_by_protocol.get(proxy_type):
            raise HTTPException(
                status_code=400,
                detail=f"Protocol {proxy_type} is disabled on your server",
            )

    try:
        dbuser = crud.create_user(
            db, new_user, admin=crud.get_admin(db, admin.username)
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="User already exists")

    bg.add_task(xray.operations.add_user, dbuser=dbuser)
    user = UserResponse.model_validate(dbuser)
    report.user_created(user=user, user_id=dbuser.id, by=admin, user_admin=dbuser.admin)
    logger.info(f'New user "{dbuser.username}" added')
    return user


@router.get("/user/{username}", response_model=UserResponse, responses={403: responses._403, 404: responses._404})
def get_user(dbuser: UserResponse = Depends(get_validated_user)):
    """Get user information"""
    return dbuser


@router.put("/user/{username}", response_model=UserResponse, responses={400: responses._400, 403: responses._403, 404: responses._404})
def modify_user(
    modified_user: UserModify,
    bg: BackgroundTasks,
    db: Session = Depends(get_db),
    dbuser: UsersResponse = Depends(get_validated_user),
    admin: Admin = Depends(Admin.get_current),
):
    """
    Modify an existing user

    - **username**: Cannot be changed. Used to identify the user.
    - **status**: User's new status. Can be 'active', 'disabled', 'on_hold', 'limited', or 'expired'.
    - **expire**: UTC timestamp for new account expiration. Set to `0` for unlimited, `null` for no change.
    - **data_limit**: New max data usage in bytes (e.g., `1073741824` for 1GB). Set to `0` for unlimited, `null` for no change.
    - **data_limit_reset_strategy**: New strategy for data limit reset. Options include 'daily', 'weekly', 'monthly', or 'no_reset'.
    - **proxies**: Dictionary of new protocol settings (e.g., `vmess`, `vless`). Empty dictionary means no change.
    - **inbounds**: Dictionary of new protocol tags to specify inbound connections. Empty dictionary means no change.
    - **note**: New optional text for additional user information or notes. `null` means no change.
    - **on_hold_timeout**: New UTC timestamp for when `on_hold` status should start or end. Only applicable if status is changed to 'on_hold'.
    - **on_hold_expire_duration**: New duration (in seconds) for how long the user should stay in `on_hold` status. Only applicable if status is changed to 'on_hold'.
    - **next_plan**: Next user plan (resets after use).

    Note: Fields set to `null` or omitted will not be modified.
    """

    for proxy_type in modified_user.proxies:
        if not xray.config.inbounds_by_protocol.get(proxy_type):
            raise HTTPException(
                status_code=400,
                detail=f"Protocol {proxy_type} is disabled on your server",
            )

    old_status = dbuser.status
    dbuser = crud.update_user(db, dbuser, modified_user)
    user = UserResponse.model_validate(dbuser)

    if user.status in [UserStatus.active, UserStatus.on_hold]:
        bg.add_task(xray.operations.update_user, dbuser=dbuser)
    else:
        bg.add_task(xray.operations.remove_user, dbuser=dbuser)

    bg.add_task(report.user_updated, user=user, user_admin=dbuser.admin, by=admin)

    logger.info(f'User "{user.username}" modified')

    if user.status != old_status:
        bg.add_task(
            report.status_change,
            username=user.username,
            status=user.status,
            user=user,
            user_admin=dbuser.admin,
            by=admin,
        )
        logger.info(
            f'User "{dbuser.username}" status changed from {old_status} to {user.status}'
        )

    return user


@router.delete("/user/{username}", responses={403: responses._403, 404: responses._404})
def remove_user(
    bg: BackgroundTasks,
    db: Session = Depends(get_db),
    dbuser: UserResponse = Depends(get_validated_user),
    admin: Admin = Depends(Admin.get_current),
):
    """Remove a user"""
    crud.remove_user(db, dbuser)
    bg.add_task(xray.operations.remove_user, dbuser=dbuser)

    bg.add_task(
        report.user_deleted, username=dbuser.username, user_admin=Admin.model_validate(dbuser.admin), by=admin
    )

    logger.info(f'User "{dbuser.username}" deleted')
    return {"detail": "User successfully deleted"}


@router.post("/user/{username}/reset", response_model=UserResponse, responses={403: responses._403, 404: responses._404})
def reset_user_data_usage(
    bg: BackgroundTasks,
    db: Session = Depends(get_db),
    dbuser: UserResponse = Depends(get_validated_user),
    admin: Admin = Depends(Admin.get_current),
):
    """Reset user data usage"""
    dbuser = crud.reset_user_data_usage(db=db, dbuser=dbuser)
    if dbuser.status in [UserStatus.active, UserStatus.on_hold]:
        bg.add_task(xray.operations.add_user, dbuser=dbuser)

    user = UserResponse.model_validate(dbuser)
    bg.add_task(
        report.user_data_usage_reset, user=user, user_admin=dbuser.admin, by=admin
    )

    logger.info(f'User "{dbuser.username}"\'s usage was reset')
    return dbuser


@router.post("/user/{username}/revoke_sub", response_model=UserResponse, responses={403: responses._403, 404: responses._404})
def revoke_user_subscription(
    bg: BackgroundTasks,
    db: Session = Depends(get_db),
    dbuser: UserResponse = Depends(get_validated_user),
    admin: Admin = Depends(Admin.get_current),
):
    """Revoke users subscription (Subscription link and proxies)"""
    dbuser = crud.revoke_user_sub(db=db, dbuser=dbuser)

    if dbuser.status in [UserStatus.active, UserStatus.on_hold]:
        bg.add_task(xray.operations.update_user, dbuser=dbuser)
    user = UserResponse.model_validate(dbuser)
    bg.add_task(
        report.user_subscription_revoked, user=user, user_admin=dbuser.admin, by=admin
    )

    logger.info(f'User "{dbuser.username}" subscription revoked')

    return user


@router.get("/users", response_model=UsersResponse, responses={400: responses._400, 403: responses._403, 404: responses._404})
def get_users(
    offset: int = None,
    limit: int = None,
    username: List[str] = Query(None),
    search: Union[str, None] = None,
    owner: Union[List[str], None] = Query(None, alias="admin"),
    status: UserStatus = None,
    sort: str = None,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    """Get all users"""
    if sort is not None:
        opts = sort.strip(",").split(",")
        sort = []
        for opt in opts:
            try:
                sort.append(crud.UsersSortingOptions[opt])
            except KeyError:
                raise HTTPException(
                    status_code=400, detail=f'"{opt}" is not a valid sort option'
                )

    users, count = crud.get_users(
        db=db,
        offset=offset,
        limit=limit,
        search=search,
        usernames=username,
        status=status,
        sort=sort,
        admins=owner if admin.is_sudo else [admin.username],
        return_with_count=True,
    )

    return {"users": users, "total": count}


@router.post("/users/reset", responses={403: responses._403, 404: responses._404})
def reset_users_data_usage(
    db: Session = Depends(get_db), admin: Admin = Depends(Admin.check_sudo_admin)
):
    """Reset all users data usage"""
    dbadmin = crud.get_admin(db, admin.username)
    crud.reset_all_users_data_usage(db=db, admin=dbadmin)
    startup_config = xray.config.include_db_users()
    xray.core.restart(startup_config)
    for node_id, node in list(xray.nodes.items()):
        if node.connected:
            xray.operations.restart_node(node_id, startup_config)
    return {"detail": "Users successfully reset."}


@router.get("/user/{username}/usage", response_model=UserUsagesResponse, responses={403: responses._403, 404: responses._404})
def get_user_usage(
    dbuser: UserResponse = Depends(get_validated_user),
    start: str = "",
    end: str = "",
    db: Session = Depends(get_db),
):
    """Get users usage"""
    start, end = validate_dates(start, end)

    usages = crud.get_user_usages(db, dbuser, start, end)

    return {"usages": usages, "username": dbuser.username}


@router.post("/user/{username}/active-next", response_model=UserResponse, responses={403: responses._403, 404: responses._404})
def active_next_plan(
    bg: BackgroundTasks,
    db: Session = Depends(get_db),
    dbuser: UserResponse = Depends(get_validated_user),
):
    """Reset user by next plan"""
    dbuser = crud.reset_user_by_next(db=db, dbuser=dbuser)

    if (dbuser is None or dbuser.next_plan is None):
        raise HTTPException(
            status_code=404,
            detail=f"User doesn't have next plan",
        )

    if dbuser.status in [UserStatus.active, UserStatus.on_hold]:
        bg.add_task(xray.operations.add_user, dbuser=dbuser)

    user = UserResponse.model_validate(dbuser)
    bg.add_task(
        report.user_data_reset_by_next, user=user, user_admin=dbuser.admin,
    )

    logger.info(f'User "{dbuser.username}"\'s usage was reset by next plan')
    return dbuser


@router.get("/users/usage", response_model=UsersUsagesResponse)
def get_users_usage(
    start: str = "",
    end: str = "",
    db: Session = Depends(get_db),
    owner: Union[List[str], None] = Query(None, alias="admin"),
    admin: Admin = Depends(Admin.get_current),
):
    """Get all users usage"""
    start, end = validate_dates(start, end)

    usages = crud.get_all_users_usages(
        db=db, start=start, end=end, admin=owner if admin.is_sudo else [admin.username]
    )

    return {"usages": usages}


@router.put("/user/{username}/set-owner", response_model=UserResponse)
def set_owner(
    admin_username: str,
    dbuser: UserResponse = Depends(get_validated_user),
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.check_sudo_admin),
):
    """Set a new owner (admin) for a user."""
    new_admin = crud.get_admin(db, username=admin_username)
    if not new_admin:
        raise HTTPException(status_code=404, detail="Admin not found")

    dbuser = crud.set_owner(db, dbuser, new_admin)
    user = UserResponse.model_validate(dbuser)

    logger.info(f'{user.username}"owner successfully set to{admin.username}')

    return user


@router.get("/users/expired", response_model=List[str])
def get_expired_users(
    expired_after: Optional[datetime] = Query(None, example="2024-01-01T00:00:00"),
    expired_before: Optional[datetime] = Query(None, example="2024-01-31T23:59:59"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    """
    Get users who have expired within the specified date range.

    - **expired_after** UTC datetime (optional)
    - **expired_before** UTC datetime (optional)
    - At least one of expired_after or expired_before must be provided for filtering
    - If both are omitted, returns all expired users
    """

    expired_after, expired_before = validate_dates(expired_after, expired_before)

    expired_users = get_expired_users_list(db, admin, expired_after, expired_before)
    return [u.username for u in expired_users]


@router.delete("/users/expired", response_model=List[str])
def delete_expired_users(
    bg: BackgroundTasks,
    expired_after: Optional[datetime] = Query(None, example="2024-01-01T00:00:00"),
    expired_before: Optional[datetime] = Query(None, example="2024-01-31T23:59:59"),
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    """
    Delete users who have expired within the specified date range.

    - **expired_after** UTC datetime (optional)
    - **expired_before** UTC datetime (optional)
    - At least one of expired_after or expired_before must be provided
    """
    expired_after, expired_before = validate_dates(expired_after, expired_before)

    expired_users = get_expired_users_list(db, admin, expired_after, expired_before)
    removed_users = [u.username for u in expired_users]

    if not removed_users:
        raise HTTPException(
            status_code=404, detail="No expired users found in the specified date range"
        )

    crud.remove_users(db, expired_users)

    for removed_user in removed_users:
        logger.info(f'User "{removed_user}" deleted')
        bg.add_task(
            report.user_deleted,
            username=removed_user,
            user_admin=next(
                (u.admin for u in expired_users if u.username == removed_user), None
            ),
            by=admin,
        )

    return removed_users


class UsersDeleteRequest(BaseModel):
    usernames: List[str]


@router.delete("/users", response_model=List[str], tags=["User"])
def remove_users(
    body: UsersDeleteRequest,
    bg: BackgroundTasks,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
):
    """Delete multiple users by their usernames."""
    # Sudo admin can delete any user, other admins can only delete their own users
    admins_filter = None if admin.is_sudo else [admin.username]
    users_to_delete, count = crud.get_users(
        db, usernames=body.usernames, admins=admins_filter, return_with_count=True
    )

    if not users_to_delete:
        raise HTTPException(
            status_code=404,
            detail="No users found for the provided usernames under your administration.",
        )

    # Log if some users were not found or not permitted
    if count != len(body.usernames):
        found_usernames = {u.username for u in users_to_delete}
        not_found_or_permitted = [
            u for u in body.usernames if u not in found_usernames
        ]
        logger.warning(
            f"Admin '{admin.username}' attempted to bulk delete users, but some were not found or not permitted: {not_found_or_permitted}"
        )

    removed_usernames = [u.username for u in users_to_delete]
    # Extract usernames before deletion for logging and reporting
    removed_usernames = [u.username for u in users_to_delete]
    
    # Prepare data for background tasks before the user objects are deleted
    # This avoids issues with detached instances after the commit in remove_users
    xray_tasks_data = [{"username": u.username, "proxies": u.proxies} for u in users_to_delete]
    report_tasks_data = [{"username": u.username, "admin_username": u.admin.username if u.admin else None} for u in users_to_delete]

    # Perform the bulk deletion
    crud.remove_users(db, users_to_delete)

    # Schedule background tasks in a more efficient manner
    # For Xray, we can pass the necessary info instead of the whole dbuser object
    for xray_data in xray_tasks_data:
        # We need a dictionary that can be handled by xray.operations.remove_user
        # Assuming it can work with a dict that has .username and .proxies
        # This might require a small adjustment in xray.operations.remove_user if it strictly expects a User object
        # For now, we construct a simple object-like structure if needed, or pass the dict.
        # Let's assume we can pass a dictionary-like object.
        class MinimalUserInfo:
            def __init__(self, username, proxies):
                self.username = username
                self.proxies = proxies
        
        bg.add_task(xray.operations.remove_user, dbuser=MinimalUserInfo(xray_data['username'], xray_data['proxies']))

    # For reporting, we can also pass simplified data
    for report_data in report_tasks_data:
        # Create a minimal admin object for the report task if needed
        minimal_admin_obj = Admin(username=report_data['admin_username']) if report_data['admin_username'] else None
        bg.add_task(
            report.user_deleted,
            username=report_data['username'],
            user_admin=minimal_admin_obj,
            by=admin,
        )

    logger.info(f'Bulk deleted {len(removed_usernames)} users: {", ".join(removed_usernames)}')
    return removed_usernames


@router.post("/users/import/hiddify", response_model=HiddifyImportResponse, tags=["User"])
async def import_hiddify_users(
    bg: BackgroundTasks,  # Required, no default
    file: UploadFile = File(...),
    selected_protocols: str = Form(...),  # Changed from 'protocols' to 'selected_protocols'
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.get_current),
    set_unlimited_expire: bool = Form(False),
    enable_smart_username_parsing: bool = Form(True),
    proxies: str = Form("{}"),  # Add proxies parameter to receive proxy settings
    inbounds: str = Form("{}"),  # Add inbounds parameter to receive inbound settings
):
    """
    Import users from a Hiddify backup JSON file.

    - **file**: The Hiddify backup .json file.
    - **set_unlimited_expire**: If true, all users will have `expire` set to 0.
    - **enable_smart_username_parsing**: If true, use smart parsing for username and note.
    - **selected_protocols**: JSON string of protocols (e.g., '["vless", "vmess"]') to enable for imported users.
    - **proxies**: JSON string of proxy settings (e.g., '{"vless": {"flow": "xtls-rprx-vision"}}').
    - **inbounds**: JSON string of inbound settings.
    """

    # Parse the protocols JSON string
    try:
        protocol_list = json.loads(selected_protocols)
        if not isinstance(protocol_list, list):
            raise ValueError("Protocols must be a list")
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid protocols format: {str(e)}")

    # Parse the proxies JSON string
    try:
        proxies_dict = json.loads(proxies)
        if not isinstance(proxies_dict, dict):
            raise ValueError("Proxies must be a dictionary")
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid proxies format: {str(e)}")

    # Parse the inbounds JSON string
    try:
        inbounds_dict = json.loads(inbounds)
        if not isinstance(inbounds_dict, dict):
            raise ValueError("Inbounds must be a dictionary")
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid inbounds format: {str(e)}")

    # Create config object for internal use
    config = HiddifyImportConfig(
        set_unlimited_expire=set_unlimited_expire,
        enable_smart_username_parsing=enable_smart_username_parsing,
        protocols=protocol_list
    )

    logger.info(
        f"Starting Hiddify import by admin '{admin.username}' with config: {config.model_dump_json()}"
    )

    successful_imports = 0
    failed_imports = 0
    errors = []
    # Ensure admin context is available for crud operations if needed later
    current_admin_db = crud.get_admin(db, admin.username)
    if not current_admin_db:
        # This should ideally not happen if Admin.get_current works
        raise HTTPException(status_code=403, detail="Admin not found in database")

    try:
        contents = await file.read()
        hiddify_data = json.loads(contents)
    except json.JSONDecodeError:
        logger.error("Hiddify import: Invalid JSON file.")
        errors.append("Invalid JSON file provided.")
        # No need to set failed_imports here, as it will be caught by the final check
    except Exception as e:
        logger.error(f"Hiddify import: Error reading file: {e}")
        errors.append(f"Error reading or parsing file: {str(e)}")
    finally:
        await file.close()

    if errors: # If file reading/parsing failed, return early
        return HiddifyImportResponse(
            successful_imports=0,
            failed_imports=1, # Count as one major failure (file processing)
            errors=errors,
        )

    hiddify_users = hiddify_data.get("users")
    hconfigs_list = hiddify_data.get("hconfigs", []) # Expecting a list of dicts
    
    proxy_path_client = ""
    if isinstance(hconfigs_list, list):
        for h_config_item in hconfigs_list:
            if isinstance(h_config_item, dict) and h_config_item.get("key") == "proxy_path_client":
                proxy_path_client = h_config_item.get("value", "")
                break
    else:
        logger.warning("Hiddify import: 'hconfigs' is not a list as expected. Cannot determine proxy_path_client.")


    if not hiddify_users or not isinstance(hiddify_users, list):
        logger.error("Hiddify import: 'users' array not found or not a list in the backup file.")
        errors.append("'users' array not found or not a list in the backup file.")
        return HiddifyImportResponse(
            successful_imports=0,
            failed_imports=1, # Count as one major failure (data structure)
            errors=errors,
        )

    if not config.protocols:
        logger.warning("Hiddify import: No protocols selected for import. Users will be created without active proxies.")
        # Not an error that stops the process, but good to log. Users might get default proxies or can be edited later.

    for h_user in hiddify_users:
        marzban_username = ""
        marzban_note = ""
        original_hiddify_name = h_user.get("name", "").strip()

        h_uuid = h_user.get("uuid")
        if not h_uuid:
            errors.append(f"Skipping user due to missing UUID: {h_user.get('name', 'Unknown Hiddify User')}")
            failed_imports += 1
            continue

        # Initialize UserCreate fields
        # Build proxies dict with settings from frontend
        user_proxies = {}
        for protocol in config.protocols:
            if protocol in proxies_dict and proxies_dict[protocol]:
                # Use proxy settings from frontend
                user_proxies[protocol] = proxies_dict[protocol].copy()
            else:
                # Use empty dict as default
                user_proxies[protocol] = {}

        # Build inbounds dict with settings from frontend or defaults
        user_inbounds = {}
        if inbounds_dict:
            # Use inbounds from frontend
            for protocol in config.protocols:
                if protocol in inbounds_dict:
                    user_inbounds[protocol] = inbounds_dict[protocol]
        # If no inbounds specified, Marzban will use defaults based on selected proxies

        user_create_data = {
            "username": "", # Will be set by parsing logic
            "proxies": user_proxies,
            "inbounds": user_inbounds,
            "status": "active", # Use string instead of enum for UserCreate
            "data_limit": 0, # Default, will be mapped
            "data_limit_reset_strategy": UserDataLimitResetStrategy.no_reset, # Default, will be mapped
            "expire": 0, # Default, will be mapped
            "note": "", # Will be set by parsing logic
            "custom_uuid": h_uuid,
            "custom_subscription_path": proxy_path_client,
            # Other fields like on_hold_timeout, on_hold_expire_duration, next_plan can be added if needed
        }

        if config.enable_smart_username_parsing:
            # Check for "NUMBER NAME" format first, where number is the order number
            match = re.match(r"^(\d+)\s+(.+)$", original_hiddify_name)
            if match:
                potential_username_num = match.group(1)
                potential_note_name = match.group(2).strip()
                marzban_username = generate_unique_marzban_username(db, potential_username_num, h_uuid)
                marzban_note = potential_note_name
            else:
                # For other names (no leading number + space, or non-Latin etc.)
                # Original Hiddify name becomes Marzban note. Marzban username is generated.
                marzban_note = original_hiddify_name if original_hiddify_name else f"Imported Hiddify user {h_uuid[:8]}"
                base_gen_username = f"h_user_{h_uuid[:8]}" # Generic base for generation
                marzban_username = generate_unique_marzban_username(db, base_gen_username, h_uuid)
        else: # Direct username attempt (smart parsing OFF)
            if original_hiddify_name:
                # Sanitize the original Hiddify name to attempt to use it as Marzban username
                # _sanitize_raw_username itself handles falling back to a UUID-based name if sanitization results in an invalid/too short name
                sanitized_h_name_for_username = _sanitize_raw_username(original_hiddify_name, h_uuid)
                marzban_username = generate_unique_marzban_username(db, sanitized_h_name_for_username, h_uuid)
                
                # If the final username is different from the original Hiddify name, set original name as note.
                # This covers cases where sanitization changed the name, or a suffix was added for uniqueness.
                if marzban_username != original_hiddify_name:
                    marzban_note = original_hiddify_name
                # If marzban_username IS original_hiddify_name, note remains empty (as per plan)
            else: # No original name, generate one
                base_gen_username = f"h_user_{h_uuid[:8]}"
                marzban_username = generate_unique_marzban_username(db, base_gen_username, h_uuid)
                marzban_note = f"Imported Hiddify user {h_uuid[:8]}" # Default note
        
        user_create_data["username"] = marzban_username
        user_create_data["note"] = marzban_note if marzban_note else None # Ensure note is None if empty

        # Map current_usage_GB to used_traffic
        h_current_usage_gb = h_user.get("current_usage_GB")
        if h_current_usage_gb is not None:
            try:
                user_create_data["used_traffic"] = int(float(h_current_usage_gb) * 1024 * 1024 * 1024) if float(h_current_usage_gb) > 0 else 0
            except ValueError:
                errors.append(f"Invalid current_usage_GB \'{h_current_usage_gb}\' for Hiddify user {original_hiddify_name} (UUID: {h_uuid}). Setting used_traffic to 0.")
                user_create_data["used_traffic"] = 0
        else:
            user_create_data["used_traffic"] = 0 # Default to 0 if not present

        # Map data_limit
        h_usage_limit_gb = h_user.get("usage_limit_GB")
        if h_usage_limit_gb is not None:
            try:
                user_create_data["data_limit"] = int(float(h_usage_limit_gb) * 1024 * 1024 * 1024) if float(h_usage_limit_gb) > 0 else 0
            except ValueError:
                errors.append(f"Invalid usage_limit_GB \'{h_usage_limit_gb}\' for Hiddify user {original_hiddify_name} (UUID: {h_uuid}). Setting to 0.")
                user_create_data["data_limit"] = 0
        else:
            user_create_data["data_limit"] = 0 # Default to unlimited if not present

        # Map expire
        if config.set_unlimited_expire:
            user_create_data["expire"] = 0
        else:
            h_package_days = h_user.get("package_days")
            h_start_date_str = h_user.get("start_date") # Format "YYYY-MM-DD" or "YYYY-MM-DD HH:MM:SS"

            if h_package_days is not None:
                try:
                    package_days_int = int(h_package_days)
                    if package_days_int >= HIDDIFY_PACKAGE_DAYS_UNLIMITED_THRESHOLD or package_days_int <= 0: # Also treat 0 or negative as unlimited
                        user_create_data["expire"] = 0
                    else:
                        start_datetime_utc = None
                        if h_start_date_str:
                            try:
                                # Attempt to parse both "YYYY-MM-DD" and "YYYY-MM-DD HH:MM:SS"
                                if ' ' in h_start_date_str:
                                    start_datetime_utc = datetime.strptime(h_start_date_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                                else:
                                    start_datetime_utc = datetime.strptime(h_start_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                            except ValueError:
                                errors.append(f"Invalid start_date format \'{h_start_date_str}\' for Hiddify user {original_hiddify_name} (UUID: {h_uuid}). Using current date.")
                                start_datetime_utc = datetime.now(timezone.utc)
                        else: # No start_date, use current date
                            start_datetime_utc = datetime.now(timezone.utc)

                        # If start_date is in the past, calculate expiry from now, otherwise from start_date
                        # This interpretation might need refinement based on exact Hiddify behavior for past start_dates.
                        # For now, if start_date is past, effectively the package starts "now" for expiry calculation.
                        # if start_datetime_utc < datetime.now(timezone.utc):
                        #     start_datetime_utc = datetime.now(timezone.utc)
                        # The above logic is often what users expect if a package is "activated" late.
                        # However, if Hiddify strictly adheres to start_date, we'd use it regardless.
                        # For this implementation, let's use the later of start_date or now to begin counting package_days.
                        effective_start_date = max(start_datetime_utc, datetime.now(timezone.utc))

                        user_create_data["expire"] = int((effective_start_date + timedelta(days=package_days_int)).timestamp())

                except ValueError:
                    errors.append(f"Invalid package_days \'{h_package_days}\' for Hiddify user {original_hiddify_name} (UUID: {h_uuid}). Setting to unlimited.")
                    user_create_data["expire"] = 0
            else: # No package_days, assume unlimited
                user_create_data["expire"] = 0

        # Map status - UserCreate only allows 'active' and 'on_hold'
        h_enable = h_user.get("enable") # boolean
        if isinstance(h_enable, bool):
            # For UserCreate, we can only use 'active' or 'on_hold'
            # If disabled in Hiddify, we'll create as active but could add a note
            user_create_data["status"] = "active"
            if not h_enable:
                # Add note about original disabled status
                original_note = user_create_data.get("note", "")
                disabled_note = "[Originally disabled in Hiddify]"
                if original_note:
                    user_create_data["note"] = f"{original_note} {disabled_note}"
                else:
                    user_create_data["note"] = disabled_note
        else:
            # Default to active if 'enable' field is missing or not a boolean
            user_create_data["status"] = "active"
            if h_enable is not None: # Log if it's present but not bool
                 errors.append(f"Invalid 'enable' field value \'{h_enable}\' for Hiddify user {original_hiddify_name} (UUID: {h_uuid}). Defaulting to active.")


        # Map data_limit_reset_strategy
        h_mode = h_user.get("mode") # e.g., "no_reset", "monthly"
        if h_mode in HIDDIFY_MODE_TO_MARZBAN_RESET_STRATEGY:
            user_create_data["data_limit_reset_strategy"] = HIDDIFY_MODE_TO_MARZBAN_RESET_STRATEGY[h_mode]
        else:
            # Default to no_reset if mode is missing or not recognized
            user_create_data["data_limit_reset_strategy"] = UserDataLimitResetStrategy.no_reset
            if h_mode: # Log if a mode was provided but not recognized
                errors.append(f"Unrecognized Hiddify mode \'{h_mode}\' for user {original_hiddify_name} (UUID: {h_uuid}). Defaulting to no_reset.")


        try:
            # Prepare UserCreate Pydantic model
            # Ensure all required fields for UserCreate are present in user_create_data
            # UserCreate might have specific requirements or default factories for some fields
            # For example, 'proxies' and 'inbounds' are dicts. 'status' and 'data_limit_reset_strategy' are enums.
            # 'expire' and 'data_limit' can be None.

            # Ensure enum values are correctly passed if UserCreate expects enum objects directly
            # However, crud.create_user likely handles string versions of enums if UserCreate model does.
            # For now, assuming string enum values are acceptable if UserCreate takes them.
            # If UserCreate model is strict, convert to enum: e.g. UserStatus(user_create_data["status"])

            # Minimal UserCreate needs: username, proxies. Others have defaults or are Optional.
            # We are providing more than minimal.
            user_to_create = UserCreate(
                username=user_create_data["username"],
                proxies=user_create_data["proxies"],
                inbounds=user_create_data.get("inbounds", {}),
                status=user_create_data.get("status", "active"),
                data_limit=user_create_data.get("data_limit"),
                data_limit_reset_strategy=user_create_data.get("data_limit_reset_strategy", UserDataLimitResetStrategy.no_reset),
                expire=user_create_data.get("expire"),
                note=user_create_data.get("note"),
                used_traffic=user_create_data.get("used_traffic", 0),
                custom_uuid=user_create_data.get("custom_uuid"),
                custom_subscription_path=user_create_data.get("custom_subscription_path"),
                # Ensure other UserCreate fields like on_hold_timeout, on_hold_expire_duration, next_plan are handled if they are part of your plan.
                # For this implementation, they are not explicitly mapped from Hiddify, so they'd take defaults or be None.
            )

            logger.debug(f"Attempting to create Marzban user: {user_to_create.model_dump_json(exclude_none=True)}")
            created_db_user = crud.create_user(db, user_to_create, admin=current_admin_db)

            if created_db_user:
                successful_imports += 1
                logger.info(f"Successfully imported Hiddify user '{original_hiddify_name}' as Marzban user '{created_db_user.username}' (UUID: {h_uuid})")

                # Refresh the user object to ensure it's properly attached to the session
                db.refresh(created_db_user)

                # Create UserResponse within the session context to avoid detachment issues
                user_response = UserResponse.model_validate(created_db_user)

                # Create a simple object for xray operations that doesn't rely on SQLAlchemy session
                class SimpleUser:
                    def __init__(self, user_response):
                        self.id = user_response.id
                        self.username = user_response.username
                        self.proxies = user_response.proxies
                        self.inbounds = user_response.inbounds
                        self.status = user_response.status

                simple_user = SimpleUser(user_response)
                bg.add_task(xray.operations.add_user, dbuser=simple_user)

                # Use the already created user_response for reporting
                try:
                    bg.add_task(report.user_created, user=user_response, user_id=created_db_user.id, by=admin, user_admin=created_db_user.admin)
                except Exception as e:
                    logger.warning(f"Failed to create report for user {created_db_user.username}: {e}")
                    # Continue without failing the import
            else:
                # This case should ideally not be reached if crud.create_user raises an exception on failure.
                failed_imports += 1
                error_msg = f"Failed to import Hiddify user '{original_hiddify_name}' (UUID: {h_uuid}). crud.create_user returned None."
                logger.error(error_msg)
                errors.append(error_msg)

        except IntegrityError as e:
            db.rollback()
            failed_imports += 1
            error_msg = f"Failed to import Hiddify user '{original_hiddify_name}' (UUID: {h_uuid}) due to database integrity error (e.g., username exists or other constraint): {e}"
            logger.error(error_msg)
            errors.append(error_msg)
        except ValueError as e: # Catch Pydantic validation errors or other ValueErrors
            db.rollback() # Rollback if any model validation fails within crud or UserCreate instantiation
            failed_imports += 1
            error_msg = f"Failed to import Hiddify user '{original_hiddify_name}' (UUID: {h_uuid}) due to data validation error: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
        except Exception as e:
            db.rollback()
            failed_imports += 1
            error_msg = f"An unexpected error occurred while importing Hiddify user '{original_hiddify_name}' (UUID: {h_uuid}): {e}"
            logger.error(error_msg, exc_info=True)
            errors.append(error_msg)

    if not errors and successful_imports == 0 and failed_imports == 0 and hiddify_users:
        # This case means we iterated users but didn't actually do anything (e.g. if all users had missing UUIDs)
        # or if the loop for h_user in hiddify_users was empty but hiddify_users itself was not.
        if not hiddify_users: # if hiddify_users was empty from the start
             errors.append("No users found in the Hiddify backup file.")
        else: # if users were present but all failed early (e.g. no UUID)
            if not errors: # if no specific errors were added, add a generic one
                 errors.append("No users could be processed from the Hiddify backup.")
        # If errors list already has items, failed_imports should reflect that.
        # If successful_imports is 0 and failed_imports is 0, but there were users,
        # it means all of them failed in a way that incremented failed_imports OR the processing logic is incomplete.
        # The primary goal here is to avoid returning 0 successful, 0 failed, and 0 errors if there was data to process.
        if not failed_imports and not errors:
            errors.append("Import logic partially implemented or no valid users found to import.")
        if not failed_imports and errors:
             failed_imports = len(hiddify_users) # assume all failed if errors exist but counter wasn't hit

    elif not errors and successful_imports == 0 and failed_imports == 0 and not hiddify_users:
        errors.append("No users found in the Hiddify backup file to import.")

    logger.info(
        f"Hiddify import completed for admin '{admin.username}'. Successful: {successful_imports}, Failed: {failed_imports}. Errors: {errors}"
    )
    return HiddifyImportResponse(
        successful_imports=successful_imports,
        failed_imports=failed_imports,
        errors=errors,
    )
