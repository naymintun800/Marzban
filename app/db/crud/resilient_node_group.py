from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.orm import selectinload

from app.db import AsyncSession
from app.db.models import Node, ResilientNodeGroup
from app.models.resilient_node_group import ResilientNodeGroupCreate, ResilientNodeGroupModify


async def create_resilient_node_group(
    db: AsyncSession,
    resilient_node_group: ResilientNodeGroupCreate,
) -> ResilientNodeGroup:
    """Create a new resilient node group."""
    
    # Fetch the nodes
    nodes = await db.execute(
        select(Node).where(Node.id.in_(resilient_node_group.node_ids))
    )
    node_list = nodes.scalars().all()
    
    if len(node_list) != len(resilient_node_group.node_ids):
        raise ValueError("Some node IDs were not found")
    
    # Create the resilient node group
    db_resilient_node_group = ResilientNodeGroup(
        name=resilient_node_group.name,
        client_strategy_hint=resilient_node_group.client_strategy_hint,
    )
    
    # Add nodes to the group
    db_resilient_node_group.nodes = node_list
    
    db.add(db_resilient_node_group)
    await db.commit()
    await db.refresh(db_resilient_node_group)
    
    return db_resilient_node_group


async def get_resilient_node_group(
    db: AsyncSession, 
    resilient_node_group_id: int
) -> Optional[ResilientNodeGroup]:
    """Get a resilient node group by ID."""
    result = await db.execute(
        select(ResilientNodeGroup)
        .options(selectinload(ResilientNodeGroup.nodes))
        .where(ResilientNodeGroup.id == resilient_node_group_id)
    )
    return result.scalar_one_or_none()


async def get_resilient_node_groups(
    db: AsyncSession,
    offset: int = 0,
    limit: int = 50,
    sort: Optional[str] = None,
) -> tuple[List[ResilientNodeGroup], int]:
    """Get all resilient node groups with pagination."""
    
    # Build the query
    query = select(ResilientNodeGroup).options(selectinload(ResilientNodeGroup.nodes))
    
    # Apply sorting
    if sort:
        if sort.startswith("-"):
            # Descending order
            sort_field = sort[1:]
            if hasattr(ResilientNodeGroup, sort_field):
                query = query.order_by(getattr(ResilientNodeGroup, sort_field).desc())
        else:
            # Ascending order
            if hasattr(ResilientNodeGroup, sort):
                query = query.order_by(getattr(ResilientNodeGroup, sort))
    else:
        # Default sorting by created_at descending
        query = query.order_by(ResilientNodeGroup.created_at.desc())
    
    # Get total count
    total_count_result = await db.execute(select(func.count(ResilientNodeGroup.id)))
    total_count = total_count_result.scalar()
    
    # Apply pagination
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    resilient_node_groups = result.scalars().all()
    
    return resilient_node_groups, total_count


async def update_resilient_node_group(
    db: AsyncSession,
    resilient_node_group_id: int,
    modify: ResilientNodeGroupModify,
) -> Optional[ResilientNodeGroup]:
    """Update a resilient node group."""
    
    # Get the existing group
    result = await db.execute(
        select(ResilientNodeGroup)
        .options(selectinload(ResilientNodeGroup.nodes))
        .where(ResilientNodeGroup.id == resilient_node_group_id)
    )
    db_resilient_node_group = result.scalar_one_or_none()
    
    if not db_resilient_node_group:
        return None
    
    # Update fields
    if modify.name is not None:
        db_resilient_node_group.name = modify.name
    
    if modify.client_strategy_hint is not None:
        db_resilient_node_group.client_strategy_hint = modify.client_strategy_hint
    
    if modify.node_ids is not None:
        # Fetch the new nodes
        nodes = await db.execute(
            select(Node).where(Node.id.in_(modify.node_ids))
        )
        node_list = nodes.scalars().all()
        
        if len(node_list) != len(modify.node_ids):
            raise ValueError("Some node IDs were not found")
        
        # Update the nodes
        db_resilient_node_group.nodes = node_list
    
    # Update the updated_at timestamp
    db_resilient_node_group.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(db_resilient_node_group)
    
    return db_resilient_node_group


async def delete_resilient_node_group(
    db: AsyncSession, 
    resilient_node_group_id: int
) -> bool:
    """Delete a resilient node group."""
    
    result = await db.execute(
        select(ResilientNodeGroup).where(ResilientNodeGroup.id == resilient_node_group_id)
    )
    db_resilient_node_group = result.scalar_one_or_none()
    
    if not db_resilient_node_group:
        return False
    
    await db.delete(db_resilient_node_group)
    await db.commit()
    
    return True


async def get_resilient_node_group_by_name(
    db: AsyncSession, 
    name: str
) -> Optional[ResilientNodeGroup]:
    """Get a resilient node group by name."""
    result = await db.execute(
        select(ResilientNodeGroup)
        .options(selectinload(ResilientNodeGroup.nodes))
        .where(ResilientNodeGroup.name == name)
    )
    return result.scalar_one_or_none()