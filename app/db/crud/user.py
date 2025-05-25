from typing import Optional
from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserResponse

def get_user_by_subscription_path(db: Session, path: str, token: str) -> Optional[UserResponse]:
    """Find a user by their custom subscription path and token."""
    user = db.query(User).filter(
        User.custom_subscription_path == path,
        User.custom_uuid == token
    ).first()
    if user:
        return UserResponse.model_validate(user)
    return None 