from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import ClientStrategyHint
from app.models.node import NodeResponse


class ResilientNodeGroupBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, examples=["EU GFW Resilient Group"])
    client_strategy_hint: ClientStrategyHint = Field(
        default=ClientStrategyHint.CLIENT_DEFAULT,
        examples=[ClientStrategyHint.URL_TEST]
    )
    model_config = ConfigDict(from_attributes=True, extra='ignore')


class ResilientNodeGroupCreate(ResilientNodeGroupBase):
    node_ids: List[int] = Field(..., min_items=1, examples=[[1, 2, 3]])


class ResilientNodeGroupModify(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    client_strategy_hint: Optional[ClientStrategyHint] = None
    node_ids: Optional[List[int]] = Field(None, min_items=1)
    model_config = ConfigDict(from_attributes=True, extra='ignore')


class ResilientNodeGroupResponse(ResilientNodeGroupBase):
    id: int
    nodes: List[NodeResponse] = Field(default_factory=list)
    node_ids: List[int] = Field(default_factory=list)
    total_nodes: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ResilientNodeGroupsResponse(BaseModel):
    groups: List[ResilientNodeGroupResponse]
    total: int
    
    model_config = ConfigDict(from_attributes=True)