import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

# Constants for username generation and validation
MARZBAN_USERNAME_ALLOWED_CHARS = re.compile(r"[^a-zA-Z0-9_@.-]")
MARZBAN_USERNAME_MAX_LEN = 32
MARZBAN_USERNAME_MIN_LEN = 3

# Hiddify specific constants for mapping
HIDDIFY_PACKAGE_DAYS_UNLIMITED_THRESHOLD = 3650  # 10 years


class HiddifyImportConfig(BaseModel):
    enable_smart_username_parsing: bool = Field(default=True, description="Enable smart username parsing for 'NUMBER NAME' format")
    group_ids: List[int] = Field(default_factory=list, description="List of group IDs to assign to imported users")
    user_template_id: Optional[int] = Field(default=None, description="Optional template ID to apply to imported users")


class HiddifyImportResponse(BaseModel):
    successful_imports: int = Field(description="Number of successfully imported users")
    failed_imports: int = Field(description="Number of failed imports")
    errors: List[str] = Field(default_factory=list, description="List of error messages for failed imports")
    batch_id: str = Field(description="Unique batch ID for this import operation")


class HiddifyUserData(BaseModel):
    """Model representing a user from Hiddify JSON export"""
    name: str
    uuid: str
    enable: bool = True
    added_by_uuid: Optional[str] = None
    last_online: Optional[str] = None
    expire_time: Optional[str] = None
    usage_limit_GB: Optional[float] = None
    package_days: Optional[int] = None
    comment: Optional[str] = None
    telegram_id: Optional[str] = None
    mode: Optional[str] = "no_reset"  # Default reset strategy


def sanitize_raw_username(name: str, h_uuid: str) -> str:
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
        return f"h_user_{h_uuid[:8]}"

    # Ensure maximum length
    return sanitized[:MARZBAN_USERNAME_MAX_LEN]


def generate_unique_batch_id() -> str:
    """Generate a unique batch ID for tracking imports."""
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    random_suffix = uuid.uuid4().hex[:8]
    return f"hiddify_import_{timestamp}_{random_suffix}"


def parse_hiddify_expire_time(expire_time_str: Optional[str], package_days: Optional[int], set_unlimited: bool) -> Optional[datetime]:
    """Parse Hiddify expiration time and convert to datetime."""
    if set_unlimited:
        return None
    
    # If package_days is very large, treat as unlimited
    if package_days and package_days >= HIDDIFY_PACKAGE_DAYS_UNLIMITED_THRESHOLD:
        return None
    
    # Try to parse expire_time
    if expire_time_str:
        try:
            # Assuming ISO format or similar
            expire_dt = datetime.fromisoformat(expire_time_str.replace('Z', '+00:00'))
            if expire_dt.tzinfo is None:
                expire_dt = expire_dt.replace(tzinfo=timezone.utc)
            return expire_dt
        except (ValueError, AttributeError):
            pass
    
    # Fallback to package_days
    if package_days and package_days > 0:
        return datetime.now(timezone.utc) + timedelta(days=package_days)
    
    # Default to unlimited if no valid expiration found
    return None


def convert_hiddify_data_limit(usage_limit_gb: Optional[float]) -> Optional[int]:
    """Convert Hiddify usage limit from GB to bytes."""
    if usage_limit_gb is None or usage_limit_gb <= 0:
        return None
    
    # Convert GB to bytes
    return int(usage_limit_gb * 1024 * 1024 * 1024)


def map_hiddify_reset_strategy(mode: Optional[str]) -> str:
    """Map Hiddify reset mode to Marzban reset strategy."""
    mode_mapping = {
        "no_reset": "no_reset",
        "monthly": "month",
        "weekly": "week",
        "daily": "day",
    }
    
    return mode_mapping.get(mode or "no_reset", "no_reset")


def generate_custom_uuid() -> str:
    """Generate a custom UUID for subscription links."""
    return str(uuid.uuid4())


def should_skip_user(user_data: HiddifyUserData) -> bool:
    """Determine if a user should be skipped during import."""
    # Skip disabled users
    if not user_data.enable:
        return True
    
    # Skip users with invalid names
    if not user_data.name or len(user_data.name.strip()) == 0:
        return True
    
    return False


def parse_smart_username(name: str, h_uuid: str, enable_smart_parsing: bool) -> tuple[str, Optional[str]]:
    """
    Parse username using smart parsing logic.
    
    Returns (username, note) tuple.
    If smart parsing is enabled and format is "NUMBER NAME", 
    use number as username and name as note.
    """
    if not enable_smart_parsing:
        return sanitize_raw_username(name, h_uuid), None
    
    # Check for "NUMBER NAME" format
    name_parts = name.strip().split(None, 1)  # Split on whitespace, max 2 parts
    
    if len(name_parts) == 2:
        potential_number, potential_name = name_parts
        
        # Check if first part is a number
        if potential_number.isdigit():
            # Use number as username, name as note
            username = sanitize_raw_username(potential_number, h_uuid)
            note = potential_name.strip()
            return username, note
    
    # Default: use full name as username, no note
    return sanitize_raw_username(name, h_uuid), None