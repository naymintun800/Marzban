import os
from datetime import datetime
from typing import List

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship
from sqlalchemy.sql.expression import select

from app import xray
from app.db.base import Base
from app.models.node import NodeStatus
from app.models.proxy import (
    ProxyHostALPN,
    ProxyHostFingerprint,
    ProxyHostSecurity,
    ProxyTypes,
)
from app.models.user import ReminderType, UserDataLimitResetStrategy, UserStatus
from app.models.resilient_node_group import ClientStrategyHint


# Define association tables first if they are used by models defined below
excluded_inbounds_association = Table(
    "exclude_inbounds_association",
    Base.metadata,
    Column("proxy_id", ForeignKey("proxies.id")),
    Column("inbound_tag", ForeignKey("inbounds.tag")),
)

template_inbounds_association = Table(
    "template_inbounds_association",
    Base.metadata,
    Column("user_template_id", ForeignKey("user_templates.id")),
    Column("inbound_tag", ForeignKey("inbounds.tag")),
)

# Define resilient_node_group_nodes_association for many-to-many relationship
resilient_node_group_nodes_association = Table(
    "resilient_node_group_nodes_association",
    Base.metadata,
    Column("resilient_node_group_id", ForeignKey("resilient_node_groups.id"), primary_key=True),
    Column("node_id", ForeignKey("nodes.id"), primary_key=True),
)

class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True)
    username = Column(String(34), unique=True, index=True)
    hashed_password = Column(String(128))
    users = relationship("User", back_populates="admin")
    created_at = Column(DateTime, default=datetime.utcnow)
    is_sudo = Column(Boolean, default=False)
    password_reset_at = Column(DateTime, nullable=True)
    telegram_id = Column(BigInteger, nullable=True, default=None)
    discord_webhook = Column(String(1024), nullable=True, default=None)
    users_usage = Column(BigInteger, nullable=False, default=0)
    usage_logs = relationship("AdminUsageLogs", back_populates="admin")


class AdminUsageLogs(Base):
    __tablename__ = "admin_usage_logs"

    id = Column(Integer, primary_key=True)
    admin_id = Column(Integer, ForeignKey("admins.id"))
    admin = relationship("Admin", back_populates="usage_logs")
    used_traffic_at_reset = Column(BigInteger, nullable=False)
    reset_at = Column(DateTime, default=datetime.utcnow)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(34, collation='NOCASE'), unique=True, index=True)
    proxies = relationship("Proxy", back_populates="user", cascade="all, delete-orphan")
    status = Column(Enum(UserStatus), nullable=False, default=UserStatus.active)
    used_traffic = Column(BigInteger, default=0)
    node_usages = relationship("NodeUserUsage", back_populates="user", cascade="all, delete-orphan")
    notification_reminders = relationship("NotificationReminder", back_populates="user", cascade="all, delete-orphan")
    data_limit = Column(BigInteger, nullable=True)
    data_limit_reset_strategy = Column(
        Enum(UserDataLimitResetStrategy),
        nullable=False,
        default=UserDataLimitResetStrategy.no_reset,
    )
    usage_logs = relationship("UserUsageResetLogs", back_populates="user", cascade="all, delete-orphan")  # maybe rename it to reset_usage_logs?
    expire = Column(Integer, nullable=True)
    admin_id = Column(Integer, ForeignKey("admins.id"))
    admin = relationship("Admin", back_populates="users")
    sub_revoked_at = Column(DateTime, nullable=True, default=None)
    sub_updated_at = Column(DateTime, nullable=True, default=None)
    sub_last_user_agent = Column(String(512), nullable=True, default=None)
    subscription_path = Column(String(256), unique=True, nullable=True, default=None)
    subscription_token = Column(String(256), unique=True, nullable=True, default=None)
    custom_subscription_path = Column(String(256), nullable=True, default=None)
    custom_uuid = Column(String(256), nullable=True, default=None)
    created_at = Column(DateTime, default=datetime.utcnow)
    note = Column(String(500), nullable=True, default=None)
    online_at = Column(DateTime, nullable=True, default=None)
    on_hold_expire_duration = Column(BigInteger, nullable=True, default=None)
    on_hold_timeout = Column(DateTime, nullable=True, default=None)

    # * Positive values: User will be deleted after the value of this field in days automatically.
    # * Negative values: User won't be deleted automatically at all.
    # * NULL: Uses global settings.
    auto_delete_in_days = Column(Integer, nullable=True, default=None)

    edit_at = Column(DateTime, nullable=True, default=None)
    last_status_change = Column(DateTime, default=datetime.utcnow, nullable=True)

    next_plan = relationship(
        "NextPlan",
        uselist=False,
        back_populates="user",
        cascade="all, delete-orphan"
    )

    @hybrid_property
    def reseted_usage(self) -> int:
        return int(sum([log.used_traffic_at_reset for log in self.usage_logs]))

    @reseted_usage.expression
    def reseted_usage(cls):
        return (
            select(func.sum(UserUsageResetLogs.used_traffic_at_reset)).
            where(UserUsageResetLogs.user_id == cls.id).
            label('reseted_usage')
        )

    @property
    def lifetime_used_traffic(self) -> int:
        return int(
            sum([log.used_traffic_at_reset for log in self.usage_logs])
            + self.used_traffic
        )

    @property
    def last_traffic_reset_time(self):
        return self.usage_logs[-1].reset_at if self.usage_logs else self.created_at

    @property
    def excluded_inbounds(self):
        _ = {}
        for proxy in self.proxies:
            _[proxy.type] = [i.tag for i in proxy.excluded_inbounds]
        return _

    @property
    def inbounds(self):
        _ = {}
        for proxy in self.proxies:
            _[proxy.type] = []
            excluded_tags = [i.tag for i in proxy.excluded_inbounds]
            for inbound in xray.config.inbounds_by_protocol.get(proxy.type, []):
                if inbound["tag"] not in excluded_tags:
                    _[proxy.type].append(inbound["tag"])

        return _


class NextPlan(Base):
    __tablename__ = 'next_plans'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    data_limit = Column(BigInteger, nullable=False)
    expire = Column(Integer, nullable=True)
    add_remaining_traffic = Column(Boolean, nullable=False, default=False, server_default='0')
    fire_on_either = Column(Boolean, nullable=False, default=True, server_default='0')

    user = relationship("User", back_populates="next_plan")


class UserTemplate(Base):
    __tablename__ = "user_templates"

    id = Column(Integer, primary_key=True)
    name = Column(String(64), nullable=False, unique=True)
    data_limit = Column(BigInteger, default=0)
    expire_duration = Column(BigInteger, default=0)  # in seconds
    username_prefix = Column(String(20), nullable=True)
    username_suffix = Column(String(20), nullable=True)

    inbounds = relationship(
        "ProxyInbound", secondary=template_inbounds_association
    )


class UserUsageResetLogs(Base):
    __tablename__ = "user_usage_logs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="usage_logs")
    used_traffic_at_reset = Column(BigInteger, nullable=False)
    reset_at = Column(DateTime, default=datetime.utcnow)


class Proxy(Base):
    __tablename__ = "proxies"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="proxies")
    type = Column(Enum(ProxyTypes), nullable=False)
    settings = Column(JSON, nullable=False)
    excluded_inbounds = relationship(
        "ProxyInbound", secondary=excluded_inbounds_association
    )


class ProxyInbound(Base):
    __tablename__ = "inbounds"

    id = Column(Integer, primary_key=True)
    tag = Column(String(256), unique=True, nullable=False, index=True)
    hosts = relationship(
        "ProxyHost", back_populates="inbound", cascade="all, delete-orphan"
    )


class ProxyHost(Base):
    __tablename__ = "hosts"
    # __table_args__ = (
    #     UniqueConstraint('inbound_tag', 'remark'),
    # )

    id = Column(Integer, primary_key=True)
    remark = Column(String(256), unique=False, nullable=False)
    address = Column(String(256), unique=False, nullable=False)
    port = Column(Integer, nullable=True)
    path = Column(String(256), unique=False, nullable=True)
    sni = Column(String(1000), unique=False, nullable=True)
    host = Column(String(1000), unique=False, nullable=True)
    security = Column(
        Enum(ProxyHostSecurity),
        unique=False,
        nullable=False,
        default=ProxyHostSecurity.inbound_default,
    )
    alpn = Column(
        Enum(ProxyHostALPN),
        unique=False,
        nullable=False,
        default=ProxyHostSecurity.none,
        server_default=ProxyHostSecurity.none.name
    )
    fingerprint = Column(
        Enum(ProxyHostFingerprint),
        unique=False,
        nullable=False,
        default=ProxyHostSecurity.none,
        server_default=ProxyHostSecurity.none.name
    )

    inbound_tag = Column(String(256), ForeignKey("inbounds.tag"), nullable=False)
    inbound = relationship("ProxyInbound", back_populates="hosts")
    allowinsecure = Column(Boolean, nullable=True)
    is_disabled = Column(Boolean, nullable=True, default=False)
    mux_enable = Column(Boolean, nullable=False, default=False, server_default='0')
    fragment_setting = Column(String(100), nullable=True)
    noise_setting = Column(String(2000), nullable=True)
    random_user_agent = Column(Boolean, nullable=False, default=False, server_default='0')
    use_sni_as_host = Column(Boolean, nullable=False, default=False, server_default="0")

    # Resilient Node Group relationship (optional)
    resilient_node_group_id = Column(Integer, ForeignKey("resilient_node_groups.id", ondelete="SET NULL"), nullable=True, index=True)
    resilient_node_group = relationship("ResilientNodeGroup", backref="hosts")


class System(Base):
    __tablename__ = "system"

    id = Column(Integer, primary_key=True)
    uplink = Column(BigInteger, default=0)
    downlink = Column(BigInteger, default=0)


class JWT(Base):
    __tablename__ = "jwt"

    id = Column(Integer, primary_key=True)
    secret_key = Column(
        String(64), nullable=False, default=lambda: os.urandom(32).hex()
    )


class TLS(Base):
    __tablename__ = "tls"

    id = Column(Integer, primary_key=True)
    key = Column(String(4096), nullable=False)
    certificate = Column(String(2048), nullable=False)


class Node(Base):
    __tablename__ = "nodes"

    id = Column(Integer, primary_key=True)
    name = Column(String(256, collation='NOCASE'), unique=True)
    address = Column(String(256), unique=False, nullable=False)  # Address for both API and client connections
    port = Column(Integer, unique=False, nullable=False)
    api_port = Column(Integer, unique=False, nullable=False)
    xray_version = Column(String(32), nullable=True)
    status = Column(Enum(NodeStatus), nullable=False, default=NodeStatus.connecting)
    last_status_change = Column(DateTime, default=datetime.utcnow)
    message = Column(String(1024), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    uplink = Column(BigInteger, default=0)
    downlink = Column(BigInteger, default=0)
    user_usages = relationship("NodeUserUsage", back_populates="node", cascade="all, delete-orphan")
    usages = relationship("NodeUsage", back_populates="node", cascade="all, delete-orphan")
    usage_coefficient = Column(Float, nullable=False, server_default=text("1.0"), default=1)
    resilient_node_groups = relationship(
        "ResilientNodeGroup",
        secondary="resilient_node_group_nodes_association",
        back_populates="nodes"
    )

    # Performance tracking fields (added later, may not exist in older databases)
    # These will be added via manual SQL script or migration
    # avg_response_time = Column(Float, nullable=True, default=None)
    # success_rate = Column(Float, nullable=True, default=None)
    # last_performance_check = Column(DateTime, nullable=True, default=None)
    # active_connections = Column(Integer, nullable=False, default=0)
    # total_connections = Column(BigInteger, nullable=False, default=0)

    # Performance history relationships (commented out until tables exist)
    # performance_metrics = relationship("NodePerformanceMetric", back_populates="node", cascade="all, delete-orphan")
    # connection_logs = relationship("NodeConnectionLog", back_populates="node", cascade="all, delete-orphan")

    @property
    def avg_response_time(self):
        """Backward compatible property for avg_response_time"""
        return getattr(self, '_avg_response_time', None)

    @avg_response_time.setter
    def avg_response_time(self, value):
        self._avg_response_time = value

    @property
    def success_rate(self):
        """Backward compatible property for success_rate"""
        return getattr(self, '_success_rate', None)

    @success_rate.setter
    def success_rate(self, value):
        self._success_rate = value

    @property
    def last_performance_check(self):
        """Backward compatible property for last_performance_check"""
        return getattr(self, '_last_performance_check', None)

    @last_performance_check.setter
    def last_performance_check(self, value):
        self._last_performance_check = value

    @property
    def active_connections(self):
        """Backward compatible property for active_connections"""
        return getattr(self, '_active_connections', 0)

    @active_connections.setter
    def active_connections(self, value):
        self._active_connections = value

    @property
    def total_connections(self):
        """Backward compatible property for total_connections"""
        return getattr(self, '_total_connections', 0)

    @total_connections.setter
    def total_connections(self, value):
        self._total_connections = value


class NodeUserUsage(Base):
    __tablename__ = "node_user_usages"
    __table_args__ = (
        UniqueConstraint('created_at', 'user_id', 'node_id'),
    )

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, unique=False, nullable=False)  # one hour per record
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="node_usages")
    node_id = Column(Integer, ForeignKey("nodes.id"))
    node = relationship("Node", back_populates="user_usages")
    used_traffic = Column(BigInteger, default=0)


class NodeUsage(Base):
    __tablename__ = "node_usages"
    __table_args__ = (
        UniqueConstraint('created_at', 'node_id'),
    )

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, unique=False, nullable=False)  # one hour per record
    node_id = Column(Integer, ForeignKey("nodes.id"))
    node = relationship("Node", back_populates="usages")
    uplink = Column(BigInteger, default=0)
    downlink = Column(BigInteger, default=0)


class NotificationReminder(Base):
    __tablename__ = "notification_reminders"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="notification_reminders")
    type = Column(Enum(ReminderType), nullable=False)
    threshold = Column(Integer, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# Temporarily commented out until database tables are created
# class NodePerformanceMetric(Base):
#     __tablename__ = "node_performance_metrics"
#     __table_args__ = (
#         UniqueConstraint('created_at', 'node_id'),
#     )

#     id = Column(Integer, primary_key=True)
#     node_id = Column(Integer, ForeignKey("nodes.id"), nullable=False)
#     node = relationship("Node", back_populates="performance_metrics")
#     created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
#     response_time = Column(Float, nullable=False)  # Response time in milliseconds
#     success = Column(Boolean, nullable=False)  # Whether the check was successful
#     error_message = Column(String(512), nullable=True)  # Error message if failed


# class NodeConnectionLog(Base):
#     __tablename__ = "node_connection_logs"

#     id = Column(Integer, primary_key=True)
#     node_id = Column(Integer, ForeignKey("nodes.id"), nullable=False)
#     node = relationship("Node", back_populates="connection_logs")
#     user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
#     user = relationship("User")
#     subscription_token = Column(String(256), nullable=True)  # To track same subscription usage
#     connected_at = Column(DateTime, default=datetime.utcnow, nullable=False)
#     disconnected_at = Column(DateTime, nullable=True)
#     user_agent = Column(String(512), nullable=True)  # To help identify different devices
#     client_ip = Column(String(45), nullable=True)  # IPv4 or IPv6


class ResilientNodeGroup(Base):
    __tablename__ = "resilient_node_groups"

    id = Column(Integer, primary_key=True)
    name = Column(String(100, collation='NOCASE'), unique=True, nullable=False, index=True)
    client_strategy_hint = Column(
        Enum(ClientStrategyHint),
        nullable=False,
        default=ClientStrategyHint.CLIENT_DEFAULT
    )

    # Many-to-many relationship with nodes
    nodes = relationship(
        "Node",
        secondary="resilient_node_group_nodes_association",
        back_populates="resilient_node_groups"
    )

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def node_ids(self) -> List[int]:
        return [node.id for node in self.nodes] if self.nodes else []
