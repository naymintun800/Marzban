import re
from distutils.version import LooseVersion

from fastapi import APIRouter, Depends, Header, Path, Request, Response, HTTPException
from fastapi.responses import HTMLResponse

from app.db import Session, crud, get_db
from app.db.models import User  # Import the SQLAlchemy User model
from app.dependencies import get_validated_sub, validate_dates, get_validated_custom_sub_user
from app.models.user import SubscriptionUserResponse, UserResponse
from app.subscription.share import encode_title, generate_subscription, setup_format_variables
from app.templates import render_template
from config import (
    SUB_PROFILE_TITLE,
    SUB_SUPPORT_URL,
    SUB_UPDATE_INTERVAL,
    SUBSCRIPTION_PAGE_TEMPLATE,
    USE_CUSTOM_JSON_DEFAULT,
    USE_CUSTOM_JSON_FOR_HAPP,
    USE_CUSTOM_JSON_FOR_STREISAND,
    USE_CUSTOM_JSON_FOR_V2RAYN,
    USE_CUSTOM_JSON_FOR_V2RAYNG,
    XRAY_SUBSCRIPTION_PATH,
)

# Reserved paths that should not be treated as subscription paths
RESERVED_PATHS = {'api', 'dashboard', 'statics', 'docs', 'redoc', 'openapi.json', XRAY_SUBSCRIPTION_PATH.lower()}

client_config = {
    "clash-meta": {"config_format": "clash-meta", "media_type": "text/yaml", "as_base64": False, "reverse": False},
    "sing-box": {"config_format": "sing-box", "media_type": "application/json", "as_base64": False, "reverse": False},
    "clash": {"config_format": "clash", "media_type": "text/yaml", "as_base64": False, "reverse": False},
    "v2ray": {"config_format": "v2ray", "media_type": "text/plain", "as_base64": True, "reverse": False},
    "outline": {"config_format": "outline", "media_type": "application/json", "as_base64": False, "reverse": False},
    "v2ray-json": {"config_format": "v2ray-json", "media_type": "application/json", "as_base64": False,
                   "reverse": False}
}

router = APIRouter(tags=['Subscription'])

# Create a separate router for custom subscription paths
custom_subscription_router = APIRouter(tags=['Subscription'])


def get_subscription_user_info(user: UserResponse) -> dict:
    """Retrieve user subscription information including upload, download, total data, and expiry."""
    return {
        "upload": 0,
        "download": user.used_traffic,
        "total": user.data_limit if user.data_limit is not None else 0,
        "expire": user.expire if user.expire is not None else 0,
    }


@custom_subscription_router.get("/{path}/{token}/")
@custom_subscription_router.get("/{path}/{token}", include_in_schema=False)
def user_subscription_custom_path(
    request: Request,
    path: str,
    token: str,
    db: Session = Depends(get_db),
    user_agent: str = Header(default="")
):
    """Provides a subscription link based on the user agent (Clash, V2Ray, etc.) with custom path."""
    # Skip if this is a reserved path
    if path.lower() in RESERVED_PATHS:
        raise HTTPException(status_code=404, detail="Not found")

    # Find ORM user by custom path and token
    orm_user = db.query(User).filter(
        User.custom_subscription_path == path,
        User.custom_uuid == token
    ).first()

    if not orm_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update subscription access time on the ORM user
    updated_orm_user = crud.update_user_sub(db, orm_user, user_agent)

    # Convert the updated ORM user to Pydantic UserResponse model
    # This ensures all validators, including for 'proxies', are run.
    user = UserResponse.model_validate(updated_orm_user)

    # Generate subscription content
    accept_header = request.headers.get("Accept", "")
    if "text/html" in accept_header:
        return HTMLResponse(
            render_template(
                SUBSCRIPTION_PAGE_TEMPLATE,
                {"user": user}
            )
        )

    response_headers = {
        "content-disposition": f'attachment; filename="{user.username}"',
        "profile-web-page-url": str(request.url),
        "support-url": SUB_SUPPORT_URL,
        "profile-title": encode_title(SUB_PROFILE_TITLE, setup_format_variables(user.__dict__)),
        "profile-update-interval": SUB_UPDATE_INTERVAL,
        "subscription-userinfo": "; ".join(
            f"{key}={val}"
            for key, val in get_subscription_user_info(user).items()
        )
    }

    if re.match(r'^([Cc]lash-verge|[Cc]lash[-\.]?[Mm]eta|[Ff][Ll][Cc]lash|[Mm]ihomo)', user_agent):
        conf = generate_subscription(user=user, config_format="clash-meta", as_base64=False, reverse=False, db=db)
        return Response(content=conf, media_type="text/yaml", headers=response_headers)
    elif re.match(r'^([Cc]lash|[Ss]tash)', user_agent):
        conf = generate_subscription(user=user, config_format="clash", as_base64=False, reverse=False, db=db)
        return Response(content=conf, media_type="text/yaml", headers=response_headers)
    elif re.match(r'^(SFA|SFI|SFM|SFT|[Kk]aring|[Hh]iddify[Nn]ext)', user_agent):
        conf = generate_subscription(user=user, config_format="sing-box", as_base64=False, reverse=False, db=db)
        return Response(content=conf, media_type="application/json", headers=response_headers)
    elif re.match(r'^(SS|SSR|SSD|SSS|Outline|Shadowsocks|SSconf)', user_agent):
        conf = generate_subscription(user=user, config_format="outline", as_base64=False, reverse=False, db=db)
        return Response(content=conf, media_type="application/json", headers=response_headers)
    elif (USE_CUSTOM_JSON_DEFAULT or USE_CUSTOM_JSON_FOR_V2RAYN) and re.match(r'^v2rayN/(\d+\.\d+)', user_agent):
        version_str = re.match(r'^v2rayN/(\d+\.\d+)', user_agent).group(1)
        if LooseVersion(version_str) >= LooseVersion("6.40"):
            conf = generate_subscription(user=user, config_format="v2ray-json", as_base64=False, reverse=False, db=db)
            return Response(content=conf, media_type="application/json", headers=response_headers)
        else:
            conf = generate_subscription(user=user, config_format="v2ray", as_base64=True, reverse=False, db=db)
            return Response(content=conf, media_type="text/plain", headers=response_headers)
    elif (USE_CUSTOM_JSON_DEFAULT or USE_CUSTOM_JSON_FOR_V2RAYNG) and re.match(r'^v2rayNG/(\d+\.\d+\.\d+)', user_agent):
        version_str = re.match(r'^v2rayNG/(\d+\.\d+\.\d+)', user_agent).group(1)
        if LooseVersion(version_str) >= LooseVersion("1.8.29"):
            conf = generate_subscription(user=user, config_format="v2ray-json", as_base64=False, reverse=False, db=db)
            return Response(content=conf, media_type="application/json", headers=response_headers)
        elif LooseVersion(version_str) >= LooseVersion("1.8.18"):
            conf = generate_subscription(user=user, config_format="v2ray-json", as_base64=False, reverse=True, db=db)
            return Response(content=conf, media_type="application/json", headers=response_headers)
        else:
            conf = generate_subscription(user=user, config_format="v2ray", as_base64=True, reverse=False, db=db)
            return Response(content=conf, media_type="text/plain", headers=response_headers)
    elif re.match(r'^[Ss]treisand', user_agent):
        if USE_CUSTOM_JSON_DEFAULT or USE_CUSTOM_JSON_FOR_STREISAND:
            conf = generate_subscription(user=user, config_format="v2ray-json", as_base64=False, reverse=False, db=db)
            return Response(content=conf, media_type="application/json", headers=response_headers)
        else:
            conf = generate_subscription(user=user, config_format="v2ray", as_base64=True, reverse=False, db=db)
            return Response(content=conf, media_type="text/plain", headers=response_headers)
    elif (USE_CUSTOM_JSON_DEFAULT or USE_CUSTOM_JSON_FOR_HAPP) and re.match(r'^Happ/(\d+\.\d+\.\d+)', user_agent):
        version_str = re.match(r'^Happ/(\d+\.\d+\.\d+)', user_agent).group(1)
        if LooseVersion(version_str) >= LooseVersion("1.63.1"):
            conf = generate_subscription(user=user, config_format="v2ray-json", as_base64=False, reverse=False, db=db)
            return Response(content=conf, media_type="application/json", headers=response_headers)
        else:
            conf = generate_subscription(user=user, config_format="v2ray", as_base64=True, reverse=False, db=db)
            return Response(content=conf, media_type="text/plain", headers=response_headers)
    else:
        conf = generate_subscription(user=user, config_format="v2ray", as_base64=True, reverse=False, db=db)
        return Response(content=conf, media_type="text/plain", headers=response_headers)


@router.get(f"/{XRAY_SUBSCRIPTION_PATH}/{{token}}/")
@router.get(f"/{XRAY_SUBSCRIPTION_PATH}/{{token}}", include_in_schema=False)
def user_subscription(
    request: Request,
    db: Session = Depends(get_db),
    dbuser: UserResponse = Depends(get_validated_sub),
    user_agent: str = Header(default="")
):
    """Provides a subscription link based on the user agent (Clash, V2Ray, etc.)."""
    user: UserResponse = UserResponse.model_validate(dbuser)

    accept_header = request.headers.get("Accept", "")
    if "text/html" in accept_header:
        return HTMLResponse(
            render_template(
                SUBSCRIPTION_PAGE_TEMPLATE,
                {"user": user}
            )
        )

    crud.update_user_sub(db, dbuser, user_agent)
    response_headers = {
        "content-disposition": f'attachment; filename="{user.username}"',
        "profile-web-page-url": str(request.url),
        "support-url": SUB_SUPPORT_URL,
        "profile-title": encode_title(SUB_PROFILE_TITLE, setup_format_variables(user.__dict__)),
        "profile-update-interval": SUB_UPDATE_INTERVAL,
        "subscription-userinfo": "; ".join(
            f"{key}={val}"
            for key, val in get_subscription_user_info(user).items()
        )
    }

    if re.match(r'^([Cc]lash-verge|[Cc]lash[-\.]?[Mm]eta|[Ff][Ll][Cc]lash|[Mm]ihomo)', user_agent):
        conf = generate_subscription(user=user, config_format="clash-meta", as_base64=False, reverse=False, db=db)
        return Response(content=conf, media_type="text/yaml", headers=response_headers)

    elif re.match(r'^([Cc]lash|[Ss]tash)', user_agent):
        conf = generate_subscription(user=user, config_format="clash", as_base64=False, reverse=False, db=db)
        return Response(content=conf, media_type="text/yaml", headers=response_headers)

    elif re.match(r'^(SFA|SFI|SFM|SFT|[Kk]aring|[Hh]iddify[Nn]ext)', user_agent):
        conf = generate_subscription(user=user, config_format="sing-box", as_base64=False, reverse=False, db=db)
        return Response(content=conf, media_type="application/json", headers=response_headers)

    elif re.match(r'^(SS|SSR|SSD|SSS|Outline|Shadowsocks|SSconf)', user_agent):
        conf = generate_subscription(user=user, config_format="outline", as_base64=False, reverse=False, db=db)
        return Response(content=conf, media_type="application/json", headers=response_headers)

    elif (USE_CUSTOM_JSON_DEFAULT or USE_CUSTOM_JSON_FOR_V2RAYN) and re.match(r'^v2rayN/(\d+\.\d+)', user_agent):
        version_str = re.match(r'^v2rayN/(\d+\.\d+)', user_agent).group(1)
        if LooseVersion(version_str) >= LooseVersion("6.40"):
            conf = generate_subscription(user=user, config_format="v2ray-json", as_base64=False, reverse=False, db=db)
            return Response(content=conf, media_type="application/json", headers=response_headers)
        else:
            conf = generate_subscription(user=user, config_format="v2ray", as_base64=True, reverse=False, db=db)
            return Response(content=conf, media_type="text/plain", headers=response_headers)

    elif (USE_CUSTOM_JSON_DEFAULT or USE_CUSTOM_JSON_FOR_V2RAYNG) and re.match(r'^v2rayNG/(\d+\.\d+\.\d+)', user_agent):
        version_str = re.match(r'^v2rayNG/(\d+\.\d+\.\d+)', user_agent).group(1)
        if LooseVersion(version_str) >= LooseVersion("1.8.29"):
            conf = generate_subscription(user=user, config_format="v2ray-json", as_base64=False, reverse=False, db=db)
            return Response(content=conf, media_type="application/json", headers=response_headers)
        elif LooseVersion(version_str) >= LooseVersion("1.8.18"):
            conf = generate_subscription(user=user, config_format="v2ray-json", as_base64=False, reverse=True, db=db)
            return Response(content=conf, media_type="application/json", headers=response_headers)
        else:
            conf = generate_subscription(user=user, config_format="v2ray", as_base64=True, reverse=False, db=db)
            return Response(content=conf, media_type="text/plain", headers=response_headers)

    elif re.match(r'^[Ss]treisand', user_agent):
        if USE_CUSTOM_JSON_DEFAULT or USE_CUSTOM_JSON_FOR_STREISAND:
            conf = generate_subscription(user=user, config_format="v2ray-json", as_base64=False, reverse=False, db=db)
            return Response(content=conf, media_type="application/json", headers=response_headers)
        else:
            conf = generate_subscription(user=user, config_format="v2ray", as_base64=True, reverse=False, db=db)
            return Response(content=conf, media_type="text/plain", headers=response_headers)

    elif (USE_CUSTOM_JSON_DEFAULT or USE_CUSTOM_JSON_FOR_HAPP) and re.match(r'^Happ/(\d+\.\d+\.\d+)', user_agent):
        version_str = re.match(r'^Happ/(\d+\.\d+\.\d+)', user_agent).group(1)
        if LooseVersion(version_str) >= LooseVersion("1.63.1"):
            conf = generate_subscription(user=user, config_format="v2ray-json", as_base64=False, reverse=False, db=db)
            return Response(content=conf, media_type="application/json", headers=response_headers)
        else:
            conf = generate_subscription(user=user, config_format="v2ray", as_base64=True, reverse=False, db=db)
            return Response(content=conf, media_type="text/plain", headers=response_headers)

    else:
        conf = generate_subscription(user=user, config_format="v2ray", as_base64=True, reverse=False, db=db)
        return Response(content=conf, media_type="text/plain", headers=response_headers)


@router.get(f"/{XRAY_SUBSCRIPTION_PATH}/{{token}}/info", response_model=SubscriptionUserResponse)
def user_subscription_info(
    dbuser: UserResponse = Depends(get_validated_sub),
):
    """Retrieves detailed information about the user's subscription."""
    return dbuser


@router.get(f"/{XRAY_SUBSCRIPTION_PATH}/{{token}}/usage")
def user_get_usage(
    dbuser: UserResponse = Depends(get_validated_sub),
    start: str = "",
    end: str = "",
    db: Session = Depends(get_db)
):
    """Fetches the usage statistics for the user within a specified date range."""
    start, end = validate_dates(start, end)

    usages = crud.get_user_usages(db, dbuser, start, end)

    return {"usages": usages, "username": dbuser.username}


@router.get(f"/{XRAY_SUBSCRIPTION_PATH}/{{token}}/{{client_type}}")
def user_subscription_with_client_type(
    request: Request,
    dbuser: UserResponse = Depends(get_validated_sub),
    client_type: str = Path(..., regex="sing-box|clash-meta|clash|outline|v2ray|v2ray-json"),
    db: Session = Depends(get_db),
    user_agent: str = Header(default="")
):
    """Provides a subscription link based on the specified client type (e.g., Clash, V2Ray)."""
    user: UserResponse = UserResponse.model_validate(dbuser)

    response_headers = {
        "content-disposition": f'attachment; filename="{user.username}"',
        "profile-web-page-url": str(request.url),
        "support-url": SUB_SUPPORT_URL,
        "profile-title": encode_title(SUB_PROFILE_TITLE, setup_format_variables(user.__dict__)),
        "profile-update-interval": SUB_UPDATE_INTERVAL,
        "subscription-userinfo": "; ".join(
            f"{key}={val}"
            for key, val in get_subscription_user_info(user).items()
        )
    }

    config = client_config.get(client_type)
    conf = generate_subscription(user=user,
                                 config_format=config["config_format"],
                                 as_base64=config["as_base64"],
                                 reverse=config["reverse"],
                                 db=db)

    return Response(content=conf, media_type=config["media_type"], headers=response_headers)


@custom_subscription_router.get("/{path}/{token}/info", response_model=SubscriptionUserResponse)
def user_custom_subscription_info(
    dbuser: UserResponse = Depends(get_validated_custom_sub_user),
):
    """Retrieves detailed information about the user's custom subscription."""
    return dbuser


@custom_subscription_router.get("/{path}/{token}/usage")
def user_custom_get_usage(
    path: str, # Explicitly take path and token for the dependency
    token: str,
    dbuser: UserResponse = Depends(get_validated_custom_sub_user),
    start: str = "",
    end: str = "",
    db: Session = Depends(get_db)
):
    """Fetches the usage statistics for the user with a custom subscription within a specified date range."""
    start_date, end_date = validate_dates(start, end)
    # crud.get_user_usages expects the ORM user model, not Pydantic UserResponse
    # We need to fetch the ORM user again, or pass username/id to crud function if possible
    # For now, let's re-fetch for simplicity, though it's not the most efficient.
    orm_user = crud.get_user_by_custom_path_and_token(db, path=path, token=token)
    if not orm_user:
        raise HTTPException(status_code=404, detail="User not found for usage query")

    usages = crud.get_user_usages(db, orm_user, start_date, end_date)
    return {"usages": usages, "username": dbuser.username}


@custom_subscription_router.get("/{path}/{token}/{client_type}")
def user_custom_subscription_with_client_type(
    request: Request,
    dbuser: UserResponse = Depends(get_validated_custom_sub_user),
    client_type: str = Path(..., regex="sing-box|clash-meta|clash|outline|v2ray|v2ray-json"),
    db: Session = Depends(get_db)
):
    """Provides a custom subscription link based on the specified client type."""
    user: UserResponse = UserResponse.model_validate(dbuser)

    response_headers = {
        "content-disposition": f'attachment; filename="{user.username}"',
        "profile-web-page-url": str(request.url),
        "support-url": SUB_SUPPORT_URL,
        "profile-title": encode_title(SUB_PROFILE_TITLE, setup_format_variables(user.__dict__)),
        "profile-update-interval": SUB_UPDATE_INTERVAL,
        "subscription-userinfo": "; ".join(
            f"{key}={val}"
            for key, val in get_subscription_user_info(user).items()
        )
    }

    config_params = client_config.get(client_type)
    if not config_params:
        raise HTTPException(status_code=400, detail=f"Invalid client type: {client_type}")

    conf = generate_subscription(user=user,
                                 config_format=config_params["config_format"],
                                 as_base64=config_params["as_base64"],
                                 reverse=config_params["reverse"],
                                 db=db)

    return Response(content=conf, media_type=config_params["media_type"], headers=response_headers)


# Export both routers
__all__ = ["router", "custom_subscription_router"]
