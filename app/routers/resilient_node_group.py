from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.db import AsyncSession, get_db
from app.db.crud import (
    create_resilient_node_group,
    delete_resilient_node_group,
    get_all_resilient_node_groups,
    get_resilient_node_group,
    get_resilient_node_group_by_name,
    get_resilient_node_groups_count,
    update_resilient_node_group,
    validate_node_ids_exist,
)
from app.models.admin import AdminDetails
from app.models.resilient_node_group import (
    ResilientNodeGroupCreate,
    ResilientNodeGroupModify,
    ResilientNodeGroupResponse,
    ResilientNodeGroupsResponse,
)
from app.utils import responses

from .authentication import check_sudo_admin

router = APIRouter(
    tags=["Resilient Node Groups"], 
    prefix="/api/resilient-node-groups",
    responses={401: responses._401, 403: responses._403}
)


@router.post(
    "",
    response_model=ResilientNodeGroupResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: responses._400, 409: responses._409},
    summary="Create a new Resilient Node Group"
)
async def create_resilient_node_group_endpoint(
    group_in: ResilientNodeGroupCreate,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(check_sudo_admin)
):
    """
    Create a new Resilient Node Group.
    
    - **name**: Name of the group (must be unique).
    - **node_ids**: List of existing node IDs. Must not be empty.
    - **client_strategy_hint**: Strategy hint for clients.
    
    **Requires sudo admin permissions.**
    """
    if not group_in.node_ids:
        raise HTTPException(status_code=422, detail="node_ids cannot be empty.")
    
    # Check if group name already exists
    existing_group = await get_resilient_node_group_by_name(db, group_in.name)
    if existing_group:
        raise HTTPException(
            status_code=409, 
            detail=f"Group name '{group_in.name}' already exists."
        )
    
    # Validate that all node_ids exist
    invalid_node_ids = await validate_node_ids_exist(db, group_in.node_ids)
    if invalid_node_ids:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid or non-existent node_ids: {invalid_node_ids}"
        )
    
    try:
        created_group = await create_resilient_node_group(db=db, group_create=group_in)
        return created_group
    except Exception as e:
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to create resilient node group: {str(e)}"
        )


@router.get(
    "",
    response_model=ResilientNodeGroupsResponse,
    summary="Get a list of all Resilient Node Groups"
)
async def get_resilient_node_groups_list(
    skip: int = Query(0, ge=0, description="Number of items to skip for pagination"),
    limit: int = Query(100, ge=1, le=200, description="Maximum number of items to return"),
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(check_sudo_admin)
):
    """
    Retrieve a paginated list of all Resilient Node Groups.
    
    **Requires sudo admin permissions.**
    """
    groups = await get_all_resilient_node_groups(db, skip=skip, limit=limit)
    total = await get_resilient_node_groups_count(db)
    
    return ResilientNodeGroupsResponse(groups=groups, total=total)


@router.get(
    "/{group_id}",
    response_model=ResilientNodeGroupResponse,
    responses={404: responses._404},
    summary="Get a specific Resilient Node Group"
)
async def get_resilient_node_group_endpoint(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(check_sudo_admin)
):
    """
    Retrieve a specific Resilient Node Group by its ID.
    
    **Requires sudo admin permissions.**
    """
    group = await get_resilient_node_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Resilient Node Group not found")
    return group


@router.put(
    "/{group_id}",
    response_model=ResilientNodeGroupResponse,
    responses={400: responses._400, 404: responses._404, 409: responses._409},
    summary="Update a Resilient Node Group"
)
async def update_resilient_node_group_endpoint(
    group_id: int,
    group_update: ResilientNodeGroupModify,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(check_sudo_admin)
):
    """
    Update an existing Resilient Node Group.
    
    **Requires sudo admin permissions.**
    """
    # Check if group exists
    existing_group = await get_resilient_node_group(db, group_id)
    if not existing_group:
        raise HTTPException(status_code=404, detail="Resilient Node Group not found")
    
    # Check if new name conflicts with existing groups (if name is being updated)
    if group_update.name and group_update.name != existing_group.name:
        name_conflict = await get_resilient_node_group_by_name(db, group_update.name)
        if name_conflict:
            raise HTTPException(
                status_code=409, 
                detail=f"Group name '{group_update.name}' already exists."
            )
    
    # Validate node_ids if provided
    if group_update.node_ids is not None:
        if len(group_update.node_ids) == 0:
            raise HTTPException(status_code=422, detail="node_ids cannot be empty.")
        
        invalid_node_ids = await validate_node_ids_exist(db, group_update.node_ids)
        if invalid_node_ids:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid or non-existent node_ids: {invalid_node_ids}"
            )
    
    try:
        updated_group = await update_resilient_node_group(db, group_id, group_update)
        return updated_group
    except Exception as e:
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to update resilient node group: {str(e)}"
        )


@router.delete(
    "/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: responses._404},
    summary="Delete a Resilient Node Group"
)
async def delete_resilient_node_group_endpoint(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    admin: AdminDetails = Depends(check_sudo_admin)
):
    """
    Delete a Resilient Node Group.
    
    **Note**: Consider the implications for hosts currently assigned to this group.
    **Requires sudo admin permissions.**
    """
    deleted_group = await delete_resilient_node_group(db, group_id)
    if not deleted_group:
        raise HTTPException(status_code=404, detail="Resilient Node Group not found")
    
    # Return 204 No Content on successful deletion
    return