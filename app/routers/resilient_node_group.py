from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.db import AsyncSession, get_db
from app.db.crud.resilient_node_group import (
    create_resilient_node_group,
    delete_resilient_node_group,
    get_resilient_node_group,
    get_resilient_node_group_by_name,
    get_resilient_node_groups,
    update_resilient_node_group,
)
from app.models.resilient_node_group import (
    ResilientNodeGroupCreate,
    ResilientNodeGroupModify,
    ResilientNodeGroupResponse,
    ResilientNodeGroupsResponse,
)
from app.routers.admin import admin_required

router = APIRouter(tags=["Resilient Node Group"])


@router.get("", response_model=ResilientNodeGroupsResponse)
async def get_resilient_node_groups_route(
    offset: int = 0,
    limit: int = 50,
    sort: str = None,
    db: AsyncSession = Depends(get_db),
    admin=Depends(admin_required),
):
    """Get all resilient node groups."""
    resilient_node_groups, total = await get_resilient_node_groups(
        db=db, offset=offset, limit=limit, sort=sort
    )
    return ResilientNodeGroupsResponse(groups=resilient_node_groups, total=total)


@router.post("", response_model=ResilientNodeGroupResponse)
async def create_resilient_node_group_route(
    resilient_node_group: ResilientNodeGroupCreate,
    db: AsyncSession = Depends(get_db),
    admin=Depends(admin_required),
):
    """Create a new resilient node group."""
    
    # Check if group with same name already exists
    existing_group = await get_resilient_node_group_by_name(db, resilient_node_group.name)
    if existing_group:
        raise HTTPException(status_code=409, detail="Resilient node group with this name already exists")
    
    try:
        db_resilient_node_group = await create_resilient_node_group(db, resilient_node_group)
        return ResilientNodeGroupResponse.model_validate(db_resilient_node_group)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{resilient_node_group_id}", response_model=ResilientNodeGroupResponse)
async def get_resilient_node_group_route(
    resilient_node_group_id: int,
    db: AsyncSession = Depends(get_db),
    admin=Depends(admin_required),
):
    """Get a resilient node group by ID."""
    db_resilient_node_group = await get_resilient_node_group(db, resilient_node_group_id)
    if not db_resilient_node_group:
        raise HTTPException(status_code=404, detail="Resilient node group not found")
    return ResilientNodeGroupResponse.model_validate(db_resilient_node_group)


@router.put("/{resilient_node_group_id}", response_model=ResilientNodeGroupResponse)
async def update_resilient_node_group_route(
    resilient_node_group_id: int,
    modify: ResilientNodeGroupModify,
    db: AsyncSession = Depends(get_db),
    admin=Depends(admin_required),
):
    """Update a resilient node group."""
    
    # Check if trying to rename to an existing name
    if modify.name:
        existing_group = await get_resilient_node_group_by_name(db, modify.name)
        if existing_group and existing_group.id != resilient_node_group_id:
            raise HTTPException(status_code=409, detail="Resilient node group with this name already exists")
    
    try:
        db_resilient_node_group = await update_resilient_node_group(db, resilient_node_group_id, modify)
        if not db_resilient_node_group:
            raise HTTPException(status_code=404, detail="Resilient node group not found")
        return ResilientNodeGroupResponse.model_validate(db_resilient_node_group)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{resilient_node_group_id}")
async def delete_resilient_node_group_route(
    resilient_node_group_id: int,
    db: AsyncSession = Depends(get_db),
    admin=Depends(admin_required),
):
    """Delete a resilient node group."""
    success = await delete_resilient_node_group(db, resilient_node_group_id)
    if not success:
        raise HTTPException(status_code=404, detail="Resilient node group not found")
    return {"message": "Resilient node group deleted successfully"}