from typing import Optional, Union
from app.models.admin import AdminInDB, AdminValidationResult, Admin
from app.models.user import UserResponse, UserStatus
from app.db import Session, crud, get_db
from config import SUDOERS
from fastapi import Depends, HTTPException
from datetime import datetime, timezone, timedelta
from app.utils.jwt import get_subscription_payload


def validate_admin(db: Session, username: str, password: str) -> Optional[AdminValidationResult]:
    """Validate admin credentials with environment variables or database."""
    if SUDOERS.get(username) == password:
        return AdminValidationResult(username=username, is_sudo=True)

    dbadmin = crud.get_admin(db, username)
    if dbadmin and AdminInDB.model_validate(dbadmin).verify_password(password):
        return AdminValidationResult(username=dbadmin.username, is_sudo=dbadmin.is_sudo)

    return None


def get_admin_by_username(username: str, db: Session = Depends(get_db)):
    """Fetch an admin by username from the database."""
    dbadmin = crud.get_admin(db, username)
    if not dbadmin:
        raise HTTPException(status_code=404, detail="Admin not found")
    return dbadmin


def get_dbnode(node_id: int, db: Session = Depends(get_db)):
    """Fetch a node by its ID from the database, raising a 404 error if not found."""
    dbnode = crud.get_node_by_id(db, node_id)
    if not dbnode:
        raise HTTPException(status_code=404, detail="Node not found")
    return dbnode


def validate_dates(start: Optional[Union[str, datetime]], end: Optional[Union[str, datetime]]) -> (datetime, datetime):
    """Validate if start and end dates are correct and if end is after start."""
    try:
        if start:
            start_date = start if isinstance(start, datetime) else datetime.fromisoformat(
                start).astimezone(timezone.utc)
        else:
            start_date = datetime.now(timezone.utc) - timedelta(days=30)
        if end:
            end_date = end if isinstance(end, datetime) else datetime.fromisoformat(end).astimezone(timezone.utc)
            if start_date and end_date < start_date:
                raise HTTPException(status_code=400, detail="Start date must be before end date")
        else:
            end_date = datetime.now(timezone.utc)

        return start_date, end_date
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date range or format")


def get_user_template(template_id: int, db: Session = Depends(get_db)):
    """Fetch a User Template by its ID, raise 404 if not found."""
    dbuser_template = crud.get_user_template(db, template_id)
    if not dbuser_template:
        raise HTTPException(status_code=404, detail="User Template not found")
    return dbuser_template


def get_validated_sub(
        token: str,
        db: Session = Depends(get_db)
) -> UserResponse:
    sub = get_subscription_payload(token)
    if not sub:
        raise HTTPException(status_code=404, detail="Not Found")

    dbuser = crud.get_user(db, sub['username'])
    if not dbuser or dbuser.created_at > sub['created_at']:
        raise HTTPException(status_code=404, detail="Not Found")

    if dbuser.sub_revoked_at and dbuser.sub_revoked_at > sub['created_at']:
        raise HTTPException(status_code=404, detail="Not Found")

    return dbuser


def get_validated_custom_sub_user(
        path: str,
        token: str, # This is the custom_uuid
        db: Session = Depends(get_db)
) -> UserResponse:
    """Validate and retrieve a user based on custom_subscription_path and custom_uuid."""
    # In custom subscriptions, the token IS the custom_uuid, and path is custom_subscription_path
    # No separate payload decoding needed like in default subscriptions.
    
    db_user_orm = crud.get_user_by_custom_path_and_token(db, path=path, token=token)

    if not db_user_orm:
        raise HTTPException(status_code=404, detail="User not found for the given custom path and token")

    # We need to ensure sub_revoked_at isn't an issue, similar to get_validated_sub
    # However, custom subscriptions don't have a 'created_at' in the token itself to compare against.
    # We assume if a user is found by custom_path and custom_uuid, and not revoked, it's valid.
    # The sub_revoked_at check might need more context if custom subs can be individually revoked 
    # in a way that invalidates older links (which isn't typical for UUID-based links).
    # For now, let's assume if found and not globally revoked for the user, it's fine.
    if db_user_orm.sub_revoked_at:
         # A simple check: if sub_revoked_at is set, the subscription is considered revoked.
         # More complex logic (e.g., comparing with a token creation time) isn't applicable here.
        raise HTTPException(status_code=404, detail="Custom subscription revoked")

    return UserResponse.model_validate(db_user_orm) # Convert ORM user to Pydantic model


def get_validated_user(
        username: str,
        admin: Admin = Depends(Admin.get_current),
        db: Session = Depends(get_db)
) -> UserResponse:
    dbuser = crud.get_user(db, username)
    if not dbuser:
        raise HTTPException(status_code=404, detail="User not found")

    if not (admin.is_sudo or (dbuser.admin and dbuser.admin.username == admin.username)):
        raise HTTPException(status_code=403, detail="You're not allowed")

    return dbuser


def get_expired_users_list(db: Session, admin: Admin, expired_after: Optional[datetime] = None,
                           expired_before: Optional[datetime] = None):
    expired_before = expired_before or datetime.now(timezone.utc)
    expired_after = expired_after or datetime.min.replace(tzinfo=timezone.utc)

    dbadmin = crud.get_admin(db, admin.username)
    dbusers = crud.get_users(
        db=db,
        status=[UserStatus.expired, UserStatus.limited],
        admin=dbadmin if not admin.is_sudo else None
    )

    return [
        u for u in dbusers
        if u.expire and expired_after.timestamp() <= u.expire <= expired_before.timestamp()
    ]
