from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse

from app.db import AsyncSession, get_db
from app.db.crud.user import create_user, get_user
from app.db.crud.group import get_group_by_id
from app.models.hiddify_import import (
    HiddifyImportConfig, 
    HiddifyImportResponse, 
    HiddifyUserData,
    generate_unique_batch_id,
    parse_hiddify_expire_time,
    convert_hiddify_data_limit,
    map_hiddify_reset_strategy,
    generate_custom_uuid,
    should_skip_user,
    parse_smart_username
)
from app.models.user import UserCreate
from app.routers.authentication import get_current
from app.models.admin import AdminDetails
import json

router = APIRouter(tags=["Hiddify Import"])

@router.post("/import", response_model=HiddifyImportResponse)
async def import_hiddify_users(
    config: HiddifyImportConfig,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(get_current),
):
    """Import users from Hiddify JSON export."""
    
    # Validate file type
    if not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="File must be a JSON file")
    
    try:
        # Read and parse JSON file
        content = await file.read()
        hiddify_data = json.loads(content.decode('utf-8'))
        
        # Validate that it's a list of user objects
        if not isinstance(hiddify_data, list):
            raise HTTPException(status_code=400, detail="JSON file must contain an array of users")
        
        # Generate batch ID for tracking
        batch_id = generate_unique_batch_id()
        
        # Process users
        successful_imports = 0
        failed_imports = 0
        errors = []
        
        for user_data_dict in hiddify_data:
            try:
                # Validate user data structure
                user_data = HiddifyUserData(**user_data_dict)
                
                # Skip disabled or invalid users
                if should_skip_user(user_data):
                    continue
                
                # Parse username and note
                username, note = parse_smart_username(
                    user_data.name, 
                    user_data.uuid, 
                    config.enable_smart_username_parsing
                )
                
                # Check if user already exists
                existing_user = await get_user(db, username)
                if existing_user:
                    errors.append(f"User '{username}' already exists")
                    failed_imports += 1
                    continue
                
                # Parse expiration
                expire = parse_hiddify_expire_time(
                    user_data.expire_time,
                    user_data.package_days,
                    config.set_unlimited_expire
                )
                
                # Convert data limit
                data_limit = convert_hiddify_data_limit(user_data.usage_limit_GB)
                
                # Map reset strategy
                reset_strategy = map_hiddify_reset_strategy(user_data.mode)
                
                # Get default group (assuming group with ID 1 exists)
                default_group = await get_group_by_id(db, 1)
                if not default_group:
                    errors.append(f"Default group not found for user '{username}'")
                    failed_imports += 1
                    continue
                
                # Create user
                user_create = UserCreate(
                    username=username,
                    status='active' if user_data.enable else 'disabled',
                    group_ids=[1],  # Default group - you might want to make this configurable
                    data_limit=data_limit or 0,
                    expire=expire,
                    note=f"{note or ''}\n[Hiddify Import - Batch: {batch_id}]".strip(),
                    data_limit_reset_strategy=reset_strategy,
                    custom_subscription_path=username.lower(),
                    custom_uuid=generate_custom_uuid(),
                    proxy_settings={
                        "vmess": {"id": None} if "vmess" in config.selected_protocols else {},
                        "vless": {"id": None, "flow": ""} if "vless" in config.selected_protocols else {},
                        "trojan": {"password": None} if "trojan" in config.selected_protocols else {},
                        "shadowsocks": {"password": None, "method": "aes-256-gcm"} if "shadowsocks" in config.selected_protocols else {}
                    }
                )
                
                # Create user in database
                await create_user(db, user_create, [default_group], admin)
                successful_imports += 1
                
            except Exception as e:
                errors.append(f"Failed to import user '{user_data_dict.get('name', 'unknown')}': {str(e)}")
                failed_imports += 1
                continue
        
        return HiddifyImportResponse(
            successful_imports=successful_imports,
            failed_imports=failed_imports,
            errors=errors,
            batch_id=batch_id
        )
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")