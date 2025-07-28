from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Node, ResilientNodeGroup
from app.models.resilient_node_group import ResilientNodeGroupCreate, ResilientNodeGroupModify


async def create_resilient_node_group(
    db: AsyncSession, group_create: ResilientNodeGroupCreate
) -> ResilientNodeGroup:
    """Create a new resilient node group with associated nodes."""
    # Create the group
    db_group = ResilientNodeGroup(
        name=group_create.name,
        client_strategy_hint=group_create.client_strategy_hint,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    # Add nodes to the group
    if group_create.node_ids:
        nodes = await db.execute(
            select(Node).where(Node.id.in_(group_create.node_ids))
        )
        db_group.nodes.extend(nodes.scalars().all())
    
    db.add(db_group)
    await db.commit()
    await db.refresh(db_group, ["nodes"])
    return db_group


async def get_resilient_node_group(
    db: AsyncSession, group_id: int
) -> Optional[ResilientNodeGroup]:
    """Get a resilient node group by ID."""
    result = await db.execute(
        select(ResilientNodeGroup)
        .options(selectinload(ResilientNodeGroup.nodes))
        .where(ResilientNodeGroup.id == group_id)
    )
    return result.scalar_one_or_none()


async def get_resilient_node_group_by_name(
    db: AsyncSession, name: str
) -> Optional[ResilientNodeGroup]:
    """Get a resilient node group by name."""
    result = await db.execute(
        select(ResilientNodeGroup)
        .options(selectinload(ResilientNodeGroup.nodes))
        .where(ResilientNodeGroup.name == name)
    )
    return result.scalar_one_or_none()


async def get_all_resilient_node_groups(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> List[ResilientNodeGroup]:
    """Get all resilient node groups with pagination."""
    result = await db.execute(
        select(ResilientNodeGroup)
        .options(selectinload(ResilientNodeGroup.nodes))
        .offset(skip)
        .limit(limit)
        .order_by(ResilientNodeGroup.created_at.desc())
    )
    return result.scalars().all()


async def get_resilient_node_groups_count(db: AsyncSession) -> int:
    """Get total count of resilient node groups."""
    result = await db.execute(
        select(ResilientNodeGroup.id).select_from(ResilientNodeGroup)
    )
    return len(result.scalars().all())


async def update_resilient_node_group(
    db: AsyncSession, group_id: int, group_update: ResilientNodeGroupModify
) -> Optional[ResilientNodeGroup]:
    """Update a resilient node group."""
    db_group = await get_resilient_node_group(db, group_id)
    if not db_group:
        return None
    
    # Update basic fields
    if group_update.name is not None:
        db_group.name = group_update.name
    if group_update.client_strategy_hint is not None:
        db_group.client_strategy_hint = group_update.client_strategy_hint
    
    # Update nodes if provided
    if group_update.node_ids is not None:
        # Clear existing nodes
        db_group.nodes.clear()
        # Add new nodes
        if group_update.node_ids:
            nodes = await db.execute(
                select(Node).where(Node.id.in_(group_update.node_ids))
            )
            db_group.nodes.extend(nodes.scalars().all())
    
    db_group.updated_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(db_group, ["nodes"])
    return db_group


async def delete_resilient_node_group(
    db: AsyncSession, group_id: int
) -> Optional[ResilientNodeGroup]:
    """Delete a resilient node group."""
    db_group = await get_resilient_node_group(db, group_id)
    if not db_group:
        return None
    
    await db.delete(db_group)
    await db.commit()
    return db_group


async def get_nodes_by_ids(db: AsyncSession, node_ids: List[int]) -> List[Node]:
    """Get nodes by their IDs."""
    result = await db.execute(
        select(Node).where(Node.id.in_(node_ids))
    )
    return result.scalars().all()


async def validate_node_ids_exist(db: AsyncSession, node_ids: List[int]) -> List[int]:
    """Validate that all node IDs exist and return any missing ones."""
    existing_nodes = await get_nodes_by_ids(db, node_ids)
    existing_ids = {node.id for node in existing_nodes}
    return [node_id for node_id in node_ids if node_id not in existing_ids]