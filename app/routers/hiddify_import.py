from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse

from app.db import AsyncSession, get_db
from app.db.crud.user import create_user, get_user
from app.db.crud.group import get_group_by_id
from app.db.crud.user_template import get_user_template
from app.db.models import User
from sqlalchemy import select, delete
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

router = APIRouter(tags=["Hiddify Import"], prefix="/api/hiddify")

@router.post("/import", response_model=HiddifyImportResponse)
async def import_hiddify_users(
    config: HiddifyImportConfig,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
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
                    False  # Don't force unlimited
                )
                
                # Convert data limit
                data_limit = convert_hiddify_data_limit(user_data.usage_limit_GB)
                
                # Map reset strategy
                reset_strategy = map_hiddify_reset_strategy(user_data.mode)
                
                # Get groups to assign
                groups = []
                if config.group_ids:
                    for group_id in config.group_ids:
                        group = await get_group_by_id(db, group_id)
                        if group:
                            groups.append(group)
                        else:
                            errors.append(f"Group ID {group_id} not found for user '{username}'")
                
                # If no groups specified or found, use default group
                if not groups:
                    default_group = await get_group_by_id(db, 1)
                    if default_group:
                        groups = [default_group]
                
                if not groups:
                    errors.append(f"No valid groups found for user '{username}'")
                    failed_imports += 1
                    continue
                
                # Create user with template or basic settings
                if config.user_template_id:
                    template = await get_user_template(db, config.user_template_id)
                    if template:
                        # Use template-based creation
                        user_create = UserCreate(
                            username=username,
                            note=f"{note or ''}\n[Hiddify Import - Batch: {batch_id}]".strip(),
                            custom_subscription_path=username.lower(),
                            custom_uuid=generate_custom_uuid(),
                            user_template_id=config.user_template_id
                        )
                    else:
                        errors.append(f"Template ID {config.user_template_id} not found for user '{username}'")
                        failed_imports += 1
                        continue
                else:
                    # Create user with Hiddify data
                    user_create = UserCreate(
                        username=username,
                        status='active' if user_data.enable else 'disabled',
                        group_ids=[g.id for g in groups],
                        data_limit=data_limit or 0,
                        expire=expire,
                        note=f"{note or ''}\n[Hiddify Import - Batch: {batch_id}]".strip(),
                        data_limit_reset_strategy=reset_strategy,
                        custom_subscription_path=username.lower(),
                        custom_uuid=generate_custom_uuid(),
                    )
                
                # Create user in database - using None for admin temporarily for testing
                await create_user(db, user_create, groups, None)
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


@router.delete("/delete-imported")
async def delete_imported_users(
    db: AsyncSession = Depends(get_db),
):
    """Delete all users that were imported from Hiddify (identified by batch ID in note)."""
    
    try:
        # Find all users with Hiddify Import batch ID in their notes
        result = await db.execute(
            select(User).where(User.note.contains("[Hiddify Import - Batch:"))
        )
        users_to_delete = result.scalars().all()
        
        deleted_count = 0
        for user in users_to_delete:
            await db.delete(user)
            deleted_count += 1
        
        await db.commit()
        
        return {"deleted_count": deleted_count, "message": f"Successfully deleted {deleted_count} imported users"}
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")