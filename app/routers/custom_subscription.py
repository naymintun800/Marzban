import re
from datetime import datetime as dt

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from fastapi.responses import HTMLResponse

from app.db import AsyncSession, get_db
from app.db.crud import get_user_by_custom_path_and_uuid
from app.db.crud.user import get_user_usages, update_user_sub
from app.models.settings import ConfigFormat, SubRule, Subscription as SubSettings
from app.models.stats import Period, UserUsageStatsList
from app.models.user import SubscriptionUserResponse, UserResponse
from app.settings import subscription_settings
from app.subscription.share import encode_title, generate_subscription
from app.templates import render_template
from config import SUBSCRIPTION_PAGE_TEMPLATE

# Reserved paths that should not be treated as subscription paths
RESERVED_PATHS = {'api', 'dashboard', 'statics', 'docs', 'redoc', 'openapi.json', 'sub'}

# Client configuration (same as in SubscriptionOperation)
client_config = {
    ConfigFormat.clash_meta: {"config_format": "clash-meta", "media_type": "text/yaml", "as_base64": False},
    ConfigFormat.clash: {"config_format": "clash", "media_type": "text/yaml", "as_base64": False},
    ConfigFormat.sing_box: {"config_format": "sing-box", "media_type": "application/json", "as_base64": False},
    ConfigFormat.links_base64: {"config_format": "links", "media_type": "text/plain", "as_base64": True},
    ConfigFormat.links: {"config_format": "links", "media_type": "text/plain", "as_base64": False},
    ConfigFormat.outline: {"config_format": "outline", "media_type": "application/json", "as_base64": False},
    ConfigFormat.xray: {"config_format": "xray", "media_type": "application/json", "as_base64": False},
}

router = APIRouter(tags=["Custom Subscription"])


async def validate_custom_subscription_user(path: str, token: str, db: AsyncSession):
    """Validate and retrieve a user based on custom_subscription_path and custom_uuid."""
    # Skip if this is a reserved path
    if path.lower() in RESERVED_PATHS:
        raise HTTPException(status_code=404, detail="Not found")

    # Find user by custom path and token
    user = await get_user_by_custom_path_and_uuid(db, path=path, token=token)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if subscription is revoked
    if user.sub_revoked_at:
        raise HTTPException(status_code=404, detail="Custom subscription revoked")

    return user


async def detect_client_type(user_agent: str, rules: list[SubRule]) -> ConfigFormat | None:
    """Detect the appropriate client configuration based on the user agent."""
    for rule in rules:
        if re.match(rule.pattern, user_agent):
            return rule.target


def create_response_headers(user, request_url: str, sub_settings: SubSettings) -> dict:
    """Create response headers for subscription responses, including user subscription info."""
    # Generate user subscription info
    user_info = {
        "upload": 0,
        "download": user.used_traffic,
        "total": user.data_limit if user.data_limit is not None else 0,
        "expire": user.expire if user.expire is not None else 0,
    }

    # Create and return headers
    return {
        "content-disposition": f'attachment; filename="{user.username}"',
        "profile-web-page-url": request_url,
        "support-url": user.admin.support_url
        if user.admin and user.admin.support_url
        else sub_settings.support_url,
        "profile-title": encode_title(user.admin.profile_title)
        if user.admin and user.admin.profile_title
        else encode_title(sub_settings.profile_title),
        "profile-update-interval": str(sub_settings.update_interval),
        "subscription-userinfo": "; ".join(f"{key}={val}" for key, val in user_info.items()),
    }


async def fetch_config(db: AsyncSession, user, client_type: ConfigFormat) -> tuple[str, str]:
    """Fetch configuration for a specific client type."""
    # Update subscription access time
    updated_user = await update_user_sub(db, user, "custom-subscription")
    
    # Get client configuration
    config = client_config.get(client_type)

    # Generate subscription content
    content = await generate_subscription(
        user=updated_user,
        config_format=config["config_format"],
        as_base64=config["as_base64"],
    )
    
    return content, config["media_type"]


@router.get("/{path}/{token}/")
@router.get("/{path}/{token}", include_in_schema=False)
async def user_subscription_custom_path(
    request: Request,
    path: str,
    token: str,
    db: AsyncSession = Depends(get_db),
    user_agent: str = Header(default="")
):
    """Provides a subscription link based on the user agent (Clash, V2Ray, etc.) with custom path."""
    # Validate user and get user object
    user = await validate_custom_subscription_user(path, token, db)
    
    # Handle HTML request (subscription page)
    sub_settings: SubSettings = await subscription_settings()

    if "text/html" in request.headers.get("Accept", ""):
        conf, media_type = await fetch_config(db, user=user, client_type=ConfigFormat.links)
        template = (
            user.admin.sub_template
            if user.admin and user.admin.sub_template
            else SUBSCRIPTION_PAGE_TEMPLATE
        )
        return HTMLResponse(render_template(template, {"user": user, "links": conf.split("\n")}))

    # Detect client type based on user agent
    client_type = await detect_client_type(user_agent, sub_settings.sub_rules)
    
    # Default to links if no specific client is detected
    if not client_type:
        client_type = ConfigFormat.links

    # Fetch configuration
    conf, media_type = await fetch_config(db, user=user, client_type=client_type)
    
    # Create response headers
    headers = create_response_headers(user, str(request.url), sub_settings)
    
    return Response(content=conf, media_type=media_type, headers=headers)


@router.get("/{path}/{token}/info", response_model=SubscriptionUserResponse)
async def user_subscription_info_custom_path(
    path: str, 
    token: str, 
    db: AsyncSession = Depends(get_db)
):
    """Retrieves detailed information about the user's subscription with custom path."""
    # Validate user and get user object
    user = await validate_custom_subscription_user(path, token, db)
    
    # Return user information
    return UserResponse.model_validate(user)


@router.get("/{path}/{token}/usage", response_model=UserUsageStatsList)
async def get_sub_user_usage_custom_path(
    path: str,
    token: str,
    start: dt | None = None,
    end: dt | None = None,
    period: Period = Period.hour,
    db: AsyncSession = Depends(get_db),
):
    """Fetches the usage statistics for the user within a specified date range with custom path."""
    # Validate user and get user object
    user = await validate_custom_subscription_user(path, token, db)
    
    # Get user usage statistics
    return await get_user_usages(
        db, user_id=user.id, start=start, end=end, period=period
    )