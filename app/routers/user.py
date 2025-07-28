import json
import uuid
from datetime import datetime as dt

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from app.db import AsyncSession, get_db
from app.db.models import UserStatus
from app.models.admin import AdminDetails
from app.models.hiddify_import import (
    HiddifyImportResponse,
    HiddifyUserData,
    convert_hiddify_data_limit,
    generate_custom_uuid,
    generate_unique_batch_id,
    map_hiddify_reset_strategy,
    parse_hiddify_expire_time,
    parse_smart_username,
    should_skip_user,
)
from app.models.stats import Period, UserUsageStatsList
from app.models.user import (
    CreateUserFromTemplate,
    ModifyUserByTemplate,
    RemoveUsersResponse,
    UserCreate,
    UserModify,
    UserResponse,
    UsersResponse,
    BulkUser,
)
from app.operation import OperatorType
from app.operation.node import NodeOperation
from app.operation.user import UserOperation
from app.utils import responses

from .authentication import check_sudo_admin, get_current

user_operator = UserOperation(operator_type=OperatorType.API)
node_operator = NodeOperation(operator_type=OperatorType.API)
router = APIRouter(tags=["User"], prefix="/api/user", responses={401: responses._401})


@router.post(
    "",
    response_model=UserResponse,
    responses={400: responses._400, 409: responses._409},
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    new_user: UserCreate, db: AsyncSession = Depends(get_db), admin: AdminDetails = Depends(get_current)
):
    """
    Create a new user

    - **username**: 3 to 32 characters, can include a-z, 0-9, and underscores.
    - **status**: User's status, defaults to `active`. Special rules if `on_hold`.
    - **expire**: UTC datetime for account expiration. Use `0` for unlimited.
    - **data_limit**: Max data usage in bytes (e.g., `1073741824` for 1GB). `0` means unlimited.
    - **data_limit_reset_strategy**: Defines how/if data limit resets. `no_reset` means it never resets.
    - **proxy_settings**: Dictionary of protocol settings (e.g., `vmess`, `vless`) will generate data for all protocol by default.
    - **group_ids**: List of group IDs to assign to the user.
    - **note**: Optional text field for additional user information or notes.
    - **on_hold_timeout**: UTC timestamp when `on_hold` status should start or end.
    - **on_hold_expire_duration**: Duration (in seconds) for how long the user should stay in `on_hold` status.
    - **next_plan**: Next user plan (resets after use).
    """

    return await user_operator.create_user(db, new_user=new_user, admin=admin)


@router.put(
    "/{username}",
    response_model=UserResponse,
    responses={400: responses._400, 403: responses._403, 404: responses._404},
)
async def modify_user(
    username: str,
    modified_user: UserModify,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(get_current),
):
    """
    Modify an existing user

    - **username**: Cannot be changed. Used to identify the user.
    - **status**: User's new status. Can be 'active', 'disabled', 'on_hold', 'limited', or 'expired'.
    - **expire**: UTC datetime for new account expiration. Set to `0` for unlimited, `null` for no change.
    - **data_limit**: New max data usage in bytes (e.g., `1073741824` for 1GB). Set to `0` for unlimited, `null` for no change.
    - **data_limit_reset_strategy**: New strategy for data limit reset. Options include 'daily', 'weekly', 'monthly', or 'no_reset'.
    - **proxies**: Dictionary of new protocol settings (e.g., `vmess`, `vless`). Empty dictionary means no change.
    - **group_ids**: List of new group IDs to assign to the user. Empty list means no change.
    - **note**: New optional text for additional user information or notes. `null` means no change.
    - **on_hold_timeout**: New UTC timestamp for when `on_hold` status should start or end. Only applicable if status is changed to 'on_hold'.
    - **on_hold_expire_duration**: New duration (in seconds) for how long the user should stay in `on_hold` status. Only applicable if status is changed to 'on_hold'.
    - **next_plan**: Next user plan (resets after use).

    Note: Fields set to `null` or omitted will not be modified.
    """
    return await user_operator.modify_user(db, username=username, modified_user=modified_user, admin=admin)


@router.delete(
    "/{username}", responses={403: responses._403, 404: responses._404}, status_code=status.HTTP_204_NO_CONTENT
)
async def remove_user(username: str, db: AsyncSession = Depends(get_db), admin: AdminDetails = Depends(get_current)):
    """Remove a user"""
    return await user_operator.remove_user(db, username=username, admin=admin)


@router.post("/{username}/reset", response_model=UserResponse, responses={403: responses._403, 404: responses._404})
async def reset_user_data_usage(
    username: str, db: AsyncSession = Depends(get_db), admin: AdminDetails = Depends(get_current)
):
    """Reset user data usage"""
    return await user_operator.reset_user_data_usage(db, username=username, admin=admin)


@router.post(
    "/{username}/revoke_sub", response_model=UserResponse, responses={403: responses._403, 404: responses._404}
)
async def revoke_user_subscription(
    username: str, db: AsyncSession = Depends(get_db), admin: AdminDetails = Depends(get_current)
):
    """Revoke users subscription (Subscription link and proxies)"""
    return await user_operator.revoke_user_sub(db, username=username, admin=admin)


@router.post("s/reset", responses={403: responses._403, 404: responses._404})
async def reset_users_data_usage(db: AsyncSession = Depends(get_db), admin: AdminDetails = Depends(check_sudo_admin)):
    """Reset all users data usage"""
    await user_operator.reset_users_data_usage(db, admin)
    await node_operator.restart_all_node(admin)
    return {}


@router.put("/{username}/set_owner", response_model=UserResponse, responses={403: responses._403})
async def set_owner(
    username: str,
    admin_username: str,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(check_sudo_admin),
):
    """Set a new owner (admin) for a user."""
    return await user_operator.set_owner(db, username=username, admin_username=admin_username, admin=admin)


@router.post(
    "/{username}/active_next", response_model=UserResponse, responses={403: responses._403, 404: responses._404}
)
async def active_next_plan(
    username: str, db: AsyncSession = Depends(get_db), admin: AdminDetails = Depends(get_current)
):
    """Reset user by next plan"""
    return await user_operator.active_next_plan(db, username=username, admin=admin)


@router.get("/{username}", response_model=UserResponse, responses={403: responses._403, 404: responses._404})
async def get_user(username: str, db: AsyncSession = Depends(get_db), admin: AdminDetails = Depends(get_current)):
    """Get user information"""
    return await user_operator.get_user(db=db, username=username, admin=admin)


@router.get(
    "s", response_model=UsersResponse, responses={400: responses._400, 403: responses._403, 404: responses._404}
)
async def get_users(
    offset: int = None,
    limit: int = None,
    username: list[str] = Query(None),
    owner: list[str] | None = Query(None, alias="admin"),
    group_ids: list[int] | None = Query(None, alias="group"),
    search: str | None = None,
    status: UserStatus | None = None,
    sort: str | None = None,
    proxy_id: str | None = None,
    load_sub: bool = False,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(get_current),
):
    """Get all users"""
    return await user_operator.get_users(
        db=db,
        admin=admin,
        offset=offset,
        limit=limit,
        username=username,
        search=search,
        owner=owner,
        status=status,
        sort=sort,
        load_sub=load_sub,
        proxy_id=proxy_id,
        group_ids=group_ids,
    )


@router.get(
    "/{username}/usage", response_model=UserUsageStatsList, responses={403: responses._403, 404: responses._404}
)
async def get_user_usage(
    username: str,
    period: Period,
    node_id: int | None = None,
    start: dt | None = Query(None, example="2024-01-01T00:00:00+03:30"),
    end: dt | None = Query(None, example="2024-01-31T23:59:59+03:30"),
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(get_current),
):
    """Get users usage"""
    return await user_operator.get_user_usage(
        db, username=username, admin=admin, start=start, end=end, period=period, node_id=node_id
    )


@router.get("s/usage", response_model=UserUsageStatsList)
async def get_users_usage(
    period: Period,
    node_id: int | None = None,
    start: dt | None = Query(None, example="2024-01-01T00:00:00+03:30"),
    end: dt | None = Query(None, example="2024-01-31T23:59:59+03:30"),
    db: AsyncSession = Depends(get_db),
    owner: list[str] | None = Query(None, alias="admin"),
    admin: AdminDetails = Depends(get_current),
):
    """Get all users usage"""
    return await user_operator.get_users_usage(
        db, admin=admin, start=start, end=end, owner=owner, period=period, node_id=node_id
    )


@router.get("s/expired", response_model=list[str])
async def get_expired_users(
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(get_current),
    expired_after: dt | None = Query(None, example="2024-01-01T00:00:00+03:30"),
    expired_before: dt | None = Query(None, example="2024-01-31T23:59:59+03:30"),
):
    """
    Get users who have expired within the specified date range.

    - **expired_after** UTC datetime (optional)
    - **expired_before** UTC datetime (optional)
    - At least one of expired_after or expired_before must be provided for filtering
    - If both are omitted, returns all expired users
    """

    return await user_operator.get_expired_users(db, admin, expired_after, expired_before)


@router.delete("s/expired", response_model=RemoveUsersResponse)
async def delete_expired_users(
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(get_current),
    expired_after: dt | None = Query(None, example="2024-01-01T00:00:00+03:30"),
    expired_before: dt | None = Query(None, example="2024-01-31T23:59:59+03:30"),
):
    """
    Delete users who have expired within the specified date range.

    - **expired_after** UTC datetime (optional)
    - **expired_before** UTC datetime (optional)
    - At least one of expired_after or expired_before must be provided
    """
    return await user_operator.delete_expired_users(db, admin, expired_after, expired_before)


@router.post("/from_template", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
async def create_user_from_template(
    new_template_user: CreateUserFromTemplate,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(get_current),
):
    return await user_operator.create_user_from_template(db, new_template_user, admin)


@router.put("/from_template/{username}", response_model=UserResponse)
async def modify_user_with_template(
    username: str,
    modify_template_user: ModifyUserByTemplate,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(get_current),
):
    return await user_operator.modify_user_with_template(db, username, modify_template_user, admin)


@router.post("s/bulk/expire", summary="Bulk sum/sub to expire of users", response_description="Success confirmation")
async def bulk_modify_users_expire(
    bulk_model: BulkUser,
    db: AsyncSession = Depends(get_db),
    _: AdminDetails = Depends(check_sudo_admin),
):
    """
    Bulk expire users based on the provided criteria.

    - **amount**: amount to adjust the user's quota (in seconds, positive to increase, negative to decrease) required
    - **user_ids**: Optional list of user IDs to modify
    - **admins**: Optional list of admin IDs — their users will be targeted
    - **status**: Optional status to filter users (e.g., "expired", "active"), Empty means no filtering
    - **group_ids**: Optional list of group IDs to filter users by their group membership
    """
    return await user_operator.bulk_modify_expire(db, bulk_model)


@router.post(
    "s/bulk/data_limit", summary="Bulk sum/sub to data limit of users", response_description="Success confirmation"
)
async def bulk_modify_users_datalimit(
    bulk_model: BulkUser,
    db: AsyncSession = Depends(get_db),
    _: AdminDetails = Depends(check_sudo_admin),
):
    """
    Bulk modify users' data limit based on the provided criteria.

    - **amount**: amount to adjust the user's quota (positive to increase, negative to decrease) required
    - **user_ids**: Optional list of user IDs to modify
    - **admins**: Optional list of admin IDs — their users will be targeted
    - **status**: Optional status to filter users (e.g., "expired", "active"), Empty means no filtering
    - **group_ids**: Optional list of group IDs to filter users by their group membership
    """
    return await user_operator.bulk_modify_datalimit(db, bulk_model)


@router.post(
    "s/import/hiddify",
    response_model=HiddifyImportResponse,
    responses={400: responses._400},
    summary="Import users from Hiddify JSON backup",
)
async def import_hiddify_users(
    file: UploadFile = File(..., description="Hiddify JSON backup file"),
    set_unlimited_expire: bool = Form(False, description="Set unlimited expiration for all users"),
    enable_smart_username_parsing: bool = Form(True, description="Enable smart username parsing"),
    selected_protocols: str = Form(..., description="JSON array of protocols to enable"),
    proxies: str = Form(..., description="JSON object of proxy settings"),
    inbounds: str = Form("{}", description="JSON object of inbound settings"),
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(get_current),
):
    """
    Import users from a Hiddify JSON backup file.
    
    - **file**: Hiddify JSON backup file
    - **set_unlimited_expire**: Set unlimited expiration for all imported users 
    - **enable_smart_username_parsing**: Parse "NUMBER NAME" format usernames
    - **selected_protocols**: JSON array of protocols to enable (e.g., ["vmess", "vless"])
    - **proxies**: JSON object with proxy settings for each protocol
    - **inbounds**: JSON object with inbound settings (optional)
    
    **Smart Username Parsing Logic:**
    - If enabled and format is "NUMBER NAME": use number as username, name as note
    - Otherwise: sanitize the full name as username
    
    **Features:**
    - Generates unique batch ID for tracking
    - Skips disabled users (enable: false)
    - Converts Hiddify data formats to Marzban equivalents
    - Creates custom subscription UUIDs for imported users
    - Comprehensive error handling and reporting
    """
    
    # Generate unique batch ID
    batch_id = generate_unique_batch_id()
    
    # Parse form parameters
    try:
        selected_protocols_list = json.loads(selected_protocols)
        proxies_dict = json.loads(proxies)
        inbounds_dict = json.loads(inbounds)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON in form parameters: {str(e)}")
    
    if not selected_protocols_list:
        raise HTTPException(status_code=400, detail="At least one protocol must be selected")
    
    # Validate file
    if not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="File must be a JSON file")
    
    # Parse Hiddify JSON file
    try:
        content = await file.read()
        hiddify_data = json.loads(content.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON file: {str(e)}")
    
    # Validate Hiddify data structure
    if not isinstance(hiddify_data, dict) or 'users' not in hiddify_data:
        raise HTTPException(status_code=400, detail="Invalid Hiddify backup format: missing 'users' key")
    
    users_data = hiddify_data.get('users', [])
    if not isinstance(users_data, list):
        raise HTTPException(status_code=400, detail="Invalid Hiddify backup format: 'users' must be an array")
    
    # Import statistics
    successful_imports = 0
    failed_imports = 0
    errors = []
    
    # Process each user
    for user_data_raw in users_data:
        try:
            # Parse user data
            user_data = HiddifyUserData(**user_data_raw)
            
            # Skip if user should be skipped
            if should_skip_user(user_data):
                continue
            
            # Parse username and note using smart parsing
            username, note = parse_smart_username(
                user_data.name, 
                user_data.uuid, 
                enable_smart_username_parsing
            )
            
            # Generate unique username if needed
            existing_user = await user_operator.get_user(db, username)
            if existing_user:
                # Generate unique username with suffix
                counter = 1
                base_username = username
                while existing_user:
                    username = f"{base_username}_{counter}"
                    if len(username) > 32:  # Marzban username limit
                        username = f"{base_username[:28]}_{counter}"
                    existing_user = await user_operator.get_user(db, username)
                    counter += 1
                    if counter > 999:  # Safety break
                        raise Exception(f"Could not generate unique username for {user_data.name}")
            
            # Parse expiration
            expire = parse_hiddify_expire_time(
                user_data.expire_time, 
                user_data.package_days, 
                set_unlimited_expire
            )
            
            # Parse data limit
            data_limit = convert_hiddify_data_limit(user_data.usage_limit_GB)
            
            # Parse reset strategy
            data_limit_reset_strategy = map_hiddify_reset_strategy(user_data.mode)
            
            # Create proxy settings
            proxy_settings = {}
            for protocol in selected_protocols_list:
                if protocol in proxies_dict:
                    proxy_settings[protocol] = proxies_dict[protocol]
                else:
                    # Default empty settings for the protocol
                    proxy_settings[protocol] = {}
            
            # Generate custom subscription UUID
            custom_uuid = generate_custom_uuid()
            
            # Combine note with comment if both exist
            final_note = note
            if user_data.comment:
                if final_note:
                    final_note = f"{final_note} | {user_data.comment}"
                else:
                    final_note = user_data.comment
            
            # Add batch ID to note for tracking
            if final_note:
                final_note = f"[{batch_id}] {final_note}"
            else:
                final_note = f"[{batch_id}] Imported from Hiddify"
            
            # Create user
            new_user = UserCreate(
                username=username,
                proxy_settings=proxy_settings,
                expire=expire,
                data_limit=data_limit,
                data_limit_reset_strategy=data_limit_reset_strategy,
                note=final_note,
                custom_uuid=custom_uuid,
                # Set default values for other fields
                status=UserStatus.active,
                group_ids=[],  # Can be extended to support group mapping
            )
            
            # Create the user
            created_user = await user_operator.create_user(db, new_user=new_user, admin=admin)
            successful_imports += 1
            
        except Exception as e:
            failed_imports += 1
            error_msg = f"User '{user_data_raw.get('name', 'unknown')}': {str(e)}"
            errors.append(error_msg)
            continue
    
    return HiddifyImportResponse(
        successful_imports=successful_imports,
        failed_imports=failed_imports,
        errors=errors,
        batch_id=batch_id,
    )
