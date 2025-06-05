from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import crud
from app.db import get_db
from app.models.resilient_node_group import (
    ResilientNodeGroupCreate,
    ResilientNodeGroupResponse,
    ResilientNodeGroupUpdate,
)

router = APIRouter(tags=["Resilient Node Groups"])


@router.post(
    "/api/resilient-node-groups",
    response_model=ResilientNodeGroupResponse,
    status_code=201,
    summary="Create a new Resilient Node Group"
)
def create_resilient_node_group(
    group_in: ResilientNodeGroupCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new Resilient Node Group.
    
    - **name**: Name of the group (must be unique).
    - **node_ids**: List of existing Marzban node IDs. Must not be empty.
    - **client_strategy_hint**: Strategy hint for clients.
    """
    if not group_in.node_ids:
        raise HTTPException(status_code=422, detail="node_ids cannot be empty.")
    
    # Check if group name already exists
    existing_group = crud.get_resilient_node_group_by_name(db, group_in.name)
    if existing_group:
        raise HTTPException(
            status_code=409, 
            detail=f"Group name '{group_in.name}' already exists."
        )
    
    # Validate that all node_ids exist
    existing_nodes = crud.get_nodes(db)
    existing_node_ids = {node.id for node in existing_nodes}
    invalid_node_ids = set(group_in.node_ids) - existing_node_ids
    if invalid_node_ids:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid or non-existent node_ids: {list(invalid_node_ids)}"
        )
    
    try:
        created_group = crud.create_resilient_node_group(db=db, group_create=group_in)
        return created_group
    except Exception as e:
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to create resilient node group: {str(e)}"
        )


@router.get(
    "/api/resilient-node-groups",
    response_model=List[ResilientNodeGroupResponse],
    summary="Get a list of all Resilient Node Groups"
)
def get_resilient_node_groups_list(
    skip: int = Query(0, ge=0, description="Number of items to skip for pagination"),
    limit: int = Query(100, ge=1, le=200, description="Maximum number of items to return"),
    db: Session = Depends(get_db)
):
    """
    Retrieve a paginated list of all Resilient Node Groups.
    """
    groups = crud.get_all_resilient_node_groups(db, skip=skip, limit=limit)
    return groups


@router.get(
    "/api/resilient-node-groups/{group_id}",
    response_model=ResilientNodeGroupResponse,
    summary="Get a specific Resilient Node Group"
)
def get_resilient_node_group(
    group_id: int,
    db: Session = Depends(get_db)
):
    """
    Retrieve a specific Resilient Node Group by its ID.
    """
    group = crud.get_resilient_node_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Resilient Node Group not found")
    return group


@router.put(
    "/api/resilient-node-groups/{group_id}",
    response_model=ResilientNodeGroupResponse,
    summary="Update a Resilient Node Group"
)
def update_resilient_node_group(
    group_id: int,
    group_update: ResilientNodeGroupUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an existing Resilient Node Group.
    """
    # Check if group exists
    existing_group = crud.get_resilient_node_group(db, group_id)
    if not existing_group:
        raise HTTPException(status_code=404, detail="Resilient Node Group not found")
    
    # Check if new name conflicts with existing groups (if name is being updated)
    if group_update.name and group_update.name != existing_group.name:
        name_conflict = crud.get_resilient_node_group_by_name(db, group_update.name)
        if name_conflict:
            raise HTTPException(
                status_code=409, 
                detail=f"Group name '{group_update.name}' already exists."
            )
    
    # Validate node_ids if provided
    if group_update.node_ids is not None:
        if len(group_update.node_ids) == 0:
            raise HTTPException(status_code=422, detail="node_ids cannot be empty.")
        
        existing_nodes = crud.get_nodes(db)
        existing_node_ids = {node.id for node in existing_nodes}
        invalid_node_ids = set(group_update.node_ids) - existing_node_ids
        if invalid_node_ids:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid or non-existent node_ids: {list(invalid_node_ids)}"
            )
    
    try:
        updated_group = crud.update_resilient_node_group(db, group_id, group_update)
        return updated_group
    except Exception as e:
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to update resilient node group: {str(e)}"
        )


@router.delete(
    "/api/resilient-node-groups/{group_id}",
    status_code=204,
    summary="Delete a Resilient Node Group"
)
def delete_resilient_node_group(
    group_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a Resilient Node Group.
    
    Note: Consider the implications for users currently assigned to this group.
    """
    deleted_group = crud.delete_resilient_node_group(db, group_id)
    if not deleted_group:
        raise HTTPException(status_code=404, detail="Resilient Node Group not found")
    
    # Return 204 No Content on successful deletion
    return 