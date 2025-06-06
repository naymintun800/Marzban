from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from datetime import datetime, timedelta

from app.db import crud
from app.db import get_db
from app.models.admin import Admin
from app.models.resilient_node_group import (
    ResilientNodeGroupCreate,
    ResilientNodeGroupResponse,
    ResilientNodeGroupUpdate,
)
from app.models.node import NodeStatus
from app.utils import responses

router = APIRouter(tags=["Resilient Node Groups"], responses={401: responses._401, 403: responses._403})


@router.post(
    "/api/resilient-node-groups",
    response_model=ResilientNodeGroupResponse,
    status_code=201,
    summary="Create a new Resilient Node Group"
)
def create_resilient_node_group(
    group_in: ResilientNodeGroupCreate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.check_sudo_admin)
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
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.check_sudo_admin)
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
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.check_sudo_admin)
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
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.check_sudo_admin)
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
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.check_sudo_admin)
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


# --- Metrics and Monitoring Endpoints ---

@router.get(
    "/api/resilient-node-groups/metrics/overview",
    summary="Get Resilient Node Groups Overview Metrics"
)
def get_resilient_node_groups_overview(
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.check_sudo_admin)
) -> Dict[str, Any]:
    """
    Get overview metrics for all resilient node groups and their nodes.
    """
    # Get all groups
    groups = crud.get_all_resilient_node_groups(db)

    # Get all nodes
    all_nodes = crud.get_nodes(db)
    connected_nodes = [n for n in all_nodes if n.status == NodeStatus.connected]

    # Calculate metrics (using default values until performance tracking is enabled)
    total_groups = len(groups)
    total_nodes_in_groups = sum(len(group.nodes) for group in groups)
    healthy_nodes = len(connected_nodes)  # Assume all connected nodes are healthy for now
    total_active_connections = 0  # Default until tracking is enabled

    return {
        "total_groups": total_groups,
        "total_nodes": len(all_nodes),
        "connected_nodes": len(connected_nodes),
        "nodes_in_groups": total_nodes_in_groups,
        "healthy_nodes": healthy_nodes,
        "total_active_connections": total_active_connections,
        "avg_response_time": None,  # Will be available after performance tracking is enabled
        "avg_success_rate": None,   # Will be available after performance tracking is enabled
    }


@router.get(
    "/api/resilient-node-groups/metrics/performance",
    summary="Get Node Performance Metrics"
)
def get_node_performance_metrics(
    hours: int = 24,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.check_sudo_admin)
) -> Dict[str, Any]:
    """
    Get performance metrics for all nodes in resilient groups.
    """
    # Get all groups with their nodes
    groups = crud.get_all_resilient_node_groups(db)

    performance_data = []

    for group in groups:
        group_data = {
            "group_id": group.id,
            "group_name": group.name,
            "strategy": group.client_strategy_hint.value,
            "nodes": []
        }

        for node in group.nodes:
            if node.status == NodeStatus.connected:
                node_data = {
                    "node_id": node.id,
                    "node_name": node.name,
                    "status": node.status.value,
                    "avg_response_time": None,  # Will be available after performance tracking
                    "success_rate": None,      # Will be available after performance tracking
                    "active_connections": 0,   # Will be available after performance tracking
                    "total_connections": 0,    # Will be available after performance tracking
                    "last_check": None,        # Will be available after performance tracking
                    "recent_checks": 0,        # Will be available after performance tracking
                }
                group_data["nodes"].append(node_data)

        performance_data.append(group_data)

    return {
        "groups": performance_data,
        "timestamp": datetime.utcnow().isoformat(),
        "period_hours": hours
    }


@router.get(
    "/api/resilient-node-groups/{group_id}/metrics",
    summary="Get Specific Group Metrics"
)
def get_group_metrics(
    group_id: int,
    hours: int = 24,
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.check_sudo_admin)
) -> Dict[str, Any]:
    """
    Get detailed metrics for a specific resilient node group.
    """
    group = crud.get_resilient_node_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Resilient Node Group not found")

    # Calculate group statistics
    connected_nodes = [n for n in group.nodes if n.status == NodeStatus.connected]

    # Node details (simplified until performance tracking is enabled)
    nodes_data = []
    for node in group.nodes:
        node_data = {
            "node_id": node.id,
            "node_name": node.name,
            "status": node.status.value,
            "avg_response_time": None,        # Will be available after performance tracking
            "success_rate": None,             # Will be available after performance tracking
            "active_connections": 0,          # Will be available after performance tracking
            "total_connections": 0,           # Will be available after performance tracking
            "performance_trend": "insufficient_data",
            "recent_metrics_count": 0,
            "last_check": None,
        }
        nodes_data.append(node_data)

    return {
        "group_id": group.id,
        "group_name": group.name,
        "strategy": group.client_strategy_hint.value,
        "total_nodes": len(group.nodes),
        "connected_nodes": len(connected_nodes),
        "total_active_connections": 0,  # Will be available after performance tracking
        "nodes": nodes_data,
        "timestamp": datetime.utcnow().isoformat(),
    }