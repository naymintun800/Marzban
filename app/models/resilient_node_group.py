from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from app.models.node import NodeResponse


class ClientStrategyHint(str, Enum):
    URL_TEST = "url-test"
    FALLBACK = "fallback"
    LOAD_BALANCE = "load-balance"
    CLIENT_DEFAULT = "client-default"
    NONE = ""


class ResilientNodeGroupBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, examples=["EU GFW Resilient Group"])
    client_strategy_hint: ClientStrategyHint = Field(
        default=ClientStrategyHint.CLIENT_DEFAULT,
        examples=[ClientStrategyHint.URL_TEST]
    )
    model_config = ConfigDict(from_attributes=True, extra='ignore')


class ResilientNodeGroupCreate(ResilientNodeGroupBase):
    node_ids: List[int] = Field(..., examples=[[1, 2, 3]])


class ResilientNodeGroupUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    client_strategy_hint: Optional[ClientStrategyHint] = None
    node_ids: Optional[List[int]] = None


class ResilientNodeGroupResponse(ResilientNodeGroupBase):
    id: int
    nodes: List[NodeResponse]  # Show full node details
    node_ids: List[int]        # This will be populated from the ORM's property
    created_at: datetime
    updated_at: datetime 