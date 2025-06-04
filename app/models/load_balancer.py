from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from app.models.node import NodeResponse # For embedding node details in response
from app.models.proxy import ProxyHostSecurity, ProxyHostALPN, ProxyHostFingerprint # For defaults and types

class LoadBalancerStrategy(str, Enum):
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    # Future options could include:
    # LEAST_CONNECTIONS = "least_connections"
    # WEIGHTED_ROUND_ROBIN = "weighted_round_robin"

class LoadBalancerHostBase(BaseModel):
    name: str = Field(..., examples=["EU Load Balancer"])
    remark_template: str = Field("LB-{USERNAME}-{PROTOCOL}", examples=["LB-{USERNAME}-{PROTOCOL}"])
    address: str = Field(..., examples=["lb.example.com"])
    port: Optional[int] = Field(None, examples=[443])
    path: Optional[str] = Field(None, examples=["/vless"])
    sni: Optional[str] = Field(None, examples=["lb.example.com"])
    host_header: Optional[str] = Field(None, examples=["lb.example.com"])
    security: ProxyHostSecurity = Field(default=ProxyHostSecurity.inbound_default)
    alpn: ProxyHostALPN = Field(default=ProxyHostALPN.none)
    fingerprint: ProxyHostFingerprint = Field(default=ProxyHostFingerprint.none)
    allowinsecure: Optional[bool] = Field(default=False)
    is_disabled: Optional[bool] = Field(default=False)
    mux_enable: Optional[bool] = Field(default=False)
    fragment_setting: Optional[str] = Field(None)
    noise_setting: Optional[str] = Field(None)
    random_user_agent: Optional[bool] = Field(default=False)
    use_sni_as_host: Optional[bool] = Field(default=False)
    inbound_tag: str = Field(..., examples=["vless-tcp-xtls-0"])
    load_balancing_strategy: LoadBalancerStrategy = LoadBalancerStrategy.ROUND_ROBIN
    model_config = ConfigDict(from_attributes=True, extra='ignore')

class LoadBalancerHostCreate(LoadBalancerHostBase):
    node_ids: List[int] = Field(..., examples=[[1, 2]])

class LoadBalancerHostUpdate(BaseModel):
    name: Optional[str] = None
    remark_template: Optional[str] = None
    address: Optional[str] = None
    port: Optional[int] = None
    path: Optional[str] = None
    sni: Optional[str] = None
    host_header: Optional[str] = None
    security: Optional[ProxyHostSecurity] = None
    alpn: Optional[ProxyHostALPN] = None
    fingerprint: Optional[ProxyHostFingerprint] = None
    allowinsecure: Optional[bool] = None
    is_disabled: Optional[bool] = None
    mux_enable: Optional[bool] = None
    fragment_setting: Optional[str] = None
    noise_setting: Optional[str] = None
    random_user_agent: Optional[bool] = None
    use_sni_as_host: Optional[bool] = None
    inbound_tag: Optional[str] = None
    load_balancing_strategy: Optional[LoadBalancerStrategy] = None
    node_ids: Optional[List[int]] = None

class LoadBalancerHostResponse(LoadBalancerHostBase):
    id: int
    nodes: List[NodeResponse] # Show full node details
    node_ids: List[int]     # This field will be populated from the ORM's 'LoadBalancerHost.node_ids' property
                            # because 'from_attributes=True' is active (inherited).

    # model_config is inherited 