import base64
import logging
import random
import secrets
from collections import defaultdict
from datetime import datetime as dt
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, List, Literal, Union, Optional

from jdatetime import date as jd
from sqlalchemy.orm import Session

from app import xray
from app.utils.system import get_public_ip, get_public_ipv6, readable_size
from app.models.node import NodeStatus

logger = logging.getLogger(__name__)

from . import *

if TYPE_CHECKING:
    from app.models.user import UserResponse
    from app.db.models import Node as NodeDbModel
    from app.db import crud as db_crud

from config import (
    ACTIVE_STATUS_TEXT,
    DISABLED_STATUS_TEXT,
    EXPIRED_STATUS_TEXT,
    LIMITED_STATUS_TEXT,
    ONHOLD_STATUS_TEXT,
)

SERVER_IP = get_public_ip()
SERVER_IPV6 = get_public_ipv6()
# DEPRECATED: ROUND_ROBIN_COUNTERS removed - functionality replaced with Resilient Node Groups

STATUS_EMOJIS = {
    "active": "✅",
    "expired": "⌛️",
    "limited": "🪫",
    "disabled": "❌",
    "on_hold": "🔌",
}

STATUS_TEXTS = {
    "active": ACTIVE_STATUS_TEXT,
    "expired": EXPIRED_STATUS_TEXT,
    "limited": LIMITED_STATUS_TEXT,
    "disabled": DISABLED_STATUS_TEXT,
    "on_hold": ONHOLD_STATUS_TEXT,
}


def _select_node_by_strategy(active_nodes: list, strategy_hint: str, user_id: int, db: Session):
    """
    Select a node from active nodes based on the client strategy hint with enhanced server-side logic.

    Args:
        active_nodes: List of active nodes
        strategy_hint: Client strategy hint from resilient node group
        user_id: User ID for consistent selection
        db: Database session for performance queries

    Returns:
        Selected node
    """
    from app.models.resilient_node_group import ClientStrategyHint

    if not active_nodes:
        return None

    if len(active_nodes) == 1:
        return active_nodes[0]

    # Convert string to enum if needed
    if isinstance(strategy_hint, str):
        try:
            strategy = ClientStrategyHint(strategy_hint)
        except ValueError:
            strategy = ClientStrategyHint.CLIENT_DEFAULT
    else:
        strategy = strategy_hint

    if strategy == ClientStrategyHint.URL_TEST:
        # URL_TEST: Server-side performance-based selection
        # Select from top-performing nodes based on response time and success rate
        return _select_fastest_node(active_nodes, user_id)

    elif strategy == ClientStrategyHint.FALLBACK:
        # FALLBACK: Primary node with health-aware fallback
        # Use first node if healthy, otherwise select best backup
        return _select_fallback_node(active_nodes)

    elif strategy == ClientStrategyHint.LOAD_BALANCE:
        # LOAD_BALANCE: Real-time load balancing based on active connections
        # Select node with lowest current load
        return _select_least_loaded_node(active_nodes, user_id)

    elif strategy == ClientStrategyHint.CLIENT_DEFAULT:
        # CLIENT_DEFAULT: Smart consistent selection with performance awareness
        # Consistent per user but avoid poorly performing nodes
        return _select_consistent_node(active_nodes, user_id)

    else:  # NONE or unknown
        # No strategy hint - random selection each time
        return random.choice(active_nodes)


def _select_fastest_node(active_nodes: list, user_id: int):
    """
    Select node based on performance metrics (response time and success rate).
    Distributes users across top-performing nodes to avoid overloading the fastest one.
    """
    # Sort nodes by performance score (combination of response time and success rate)
    def performance_score(node):
        # Default values for nodes without performance data
        response_time = node.avg_response_time or 1000.0  # Default to 1000ms
        success_rate = node.success_rate or 50.0  # Default to 50%

        # Lower response time is better, higher success rate is better
        # Normalize and combine (success rate weight is higher)
        time_score = max(0, 100 - (response_time / 10))  # 100ms = 90 points, 1000ms = 0 points
        combined_score = (success_rate * 0.7) + (time_score * 0.3)
        return combined_score

    # Sort by performance score (highest first)
    sorted_nodes = sorted(active_nodes, key=performance_score, reverse=True)

    # Select from top 50% of nodes to distribute load
    top_nodes_count = max(1, len(sorted_nodes) // 2)
    top_nodes = sorted_nodes[:top_nodes_count]

    # Distribute users across top nodes
    return top_nodes[user_id % len(top_nodes)]


def _select_fallback_node(active_nodes: list):
    """
    Select primary node if healthy, otherwise select best backup.
    """
    primary_node = active_nodes[0]

    # Check if primary node is healthy (good success rate)
    if primary_node.success_rate is None or primary_node.success_rate >= 80.0:
        return primary_node

    # Primary is unhealthy, select best backup from remaining nodes
    if len(active_nodes) > 1:
        backup_nodes = active_nodes[1:]
        # Select backup with highest success rate
        best_backup = max(backup_nodes, key=lambda n: n.success_rate or 0.0)
        return best_backup

    # No backup available, return primary anyway
    return primary_node


def _select_least_loaded_node(active_nodes: list, user_id: int):
    """
    Select node with lowest current active connections.
    Uses user_id for tie-breaking to maintain some consistency.
    """
    # Calculate load score considering both connections and performance
    def load_score(node):
        # Base load from active connections
        connection_load = node.active_connections

        # Penalty for poor performance (higher response time = higher load)
        performance_penalty = 0
        if node.avg_response_time:
            # Add penalty: 1 point per 100ms above 100ms
            performance_penalty = max(0, (node.avg_response_time - 100) / 100)

        # Penalty for poor success rate
        if node.success_rate is not None and node.success_rate < 90:
            performance_penalty += (90 - node.success_rate) / 10

        return connection_load + performance_penalty

    # Sort by load score (lowest first)
    sorted_nodes = sorted(active_nodes, key=load_score)

    # Find nodes with minimum load score
    min_score = load_score(sorted_nodes[0])
    least_loaded_nodes = [n for n in sorted_nodes if abs(load_score(n) - min_score) < 1.0]

    # If multiple nodes have similar load, use user_id for consistent selection
    return least_loaded_nodes[user_id % len(least_loaded_nodes)]


def _select_consistent_node(active_nodes: list, user_id: int):
    """
    Consistent selection per user but avoid poorly performing nodes.
    Filters out nodes with very poor performance before applying consistent selection.
    Also considers estimated device count for better distribution.
    """
    # Filter out nodes with very poor performance (success rate < 30%)
    healthy_nodes = [n for n in active_nodes if n.success_rate is None or n.success_rate >= 30.0]

    # If all nodes are unhealthy, use all nodes anyway
    if not healthy_nodes:
        healthy_nodes = active_nodes

    # Try to estimate device count for this user to improve distribution
    try:
        from app.services.connection_tracker import get_estimated_device_count
        device_count = get_estimated_device_count(user_id)

        # If multiple devices detected, use a different distribution strategy
        if device_count > 1:
            # Distribute devices across different nodes
            # Use a hash of user_id + device_index for better distribution
            base_selection = user_id % len(healthy_nodes)
            # Add some variation based on time to help distribute multiple devices
            time_variation = (int(datetime.utcnow().timestamp()) // 3600) % len(healthy_nodes)  # Changes hourly
            selected_index = (base_selection + time_variation) % len(healthy_nodes)
            return healthy_nodes[selected_index]
    except Exception:
        # Fall back to simple consistent selection if device counting fails
        pass

    # Apply consistent selection to healthy nodes
    return healthy_nodes[user_id % len(healthy_nodes)]


def _get_subscription_hash(user_id: int, subscription_token: str = None) -> int:
    """
    Generate a hash for subscription-based distribution.
    This helps distribute different devices using the same subscription.
    """
    import hashlib

    # Create a hash based on user_id and subscription_token
    hash_input = f"{user_id}_{subscription_token or ''}"
    hash_value = int(hashlib.md5(hash_input.encode()).hexdigest()[:8], 16)
    return hash_value


def generate_v2ray_links(proxies: dict, inbounds: dict, extra_data: dict, reverse: bool, db: Session, user: "UserResponse") -> list:
    format_variables = setup_format_variables(extra_data)
    conf = V2rayShareLink()
    return process_inbounds_and_tags(inbounds, proxies, format_variables, conf=conf, reverse=reverse, db=db, user=user)


def generate_clash_subscription(
        proxies: dict, inbounds: dict, extra_data: dict, reverse: bool, db: Session, user: "UserResponse", is_meta: bool = False
) -> str:
    if is_meta is True:
        conf = ClashMetaConfiguration()
    else:
        conf = ClashConfiguration()

    format_variables = setup_format_variables(extra_data)
    return process_inbounds_and_tags(
        inbounds, proxies, format_variables, conf=conf, reverse=reverse, db=db, user=user
    )


def generate_singbox_subscription(
        proxies: dict, inbounds: dict, extra_data: dict, reverse: bool, db: Session, user: "UserResponse"
) -> str:
    conf = SingBoxConfiguration()

    format_variables = setup_format_variables(extra_data)
    return process_inbounds_and_tags(
        inbounds, proxies, format_variables, conf=conf, reverse=reverse, db=db, user=user
    )


def generate_outline_subscription(
        proxies: dict, inbounds: dict, extra_data: dict, reverse: bool, db: Session, user: "UserResponse"
) -> str:
    conf = OutlineConfiguration()

    format_variables = setup_format_variables(extra_data)
    return process_inbounds_and_tags(
        inbounds, proxies, format_variables, conf=conf, reverse=reverse, db=db, user=user
    )


def generate_v2ray_json_subscription(
        proxies: dict, inbounds: dict, extra_data: dict, reverse: bool, db: Session, user: "UserResponse"
) -> str:
    conf = V2rayJsonConfig()

    format_variables = setup_format_variables(extra_data)
    return process_inbounds_and_tags(
        inbounds, proxies, format_variables, conf=conf, reverse=reverse, db=db, user=user
    )


def generate_subscription(
        user: "UserResponse",
        config_format: Literal["v2ray", "clash-meta", "clash", "sing-box", "outline", "v2ray-json"],
        as_base64: bool,
        reverse: bool,
        db: Session,
) -> str:
    kwargs = {
        "proxies": user.proxies,
        "inbounds": user.inbounds,
        "extra_data": user.__dict__,
        "reverse": reverse,
        "db": db,
        "user": user
    }

    if config_format == "v2ray":
        config = "\n".join(generate_v2ray_links(**kwargs))
    elif config_format == "clash-meta":
        config = generate_clash_subscription(**kwargs, is_meta=True)
    elif config_format == "clash":
        config = generate_clash_subscription(**kwargs)
    elif config_format == "sing-box":
        config = generate_singbox_subscription(**kwargs)
    elif config_format == "outline":
        config = generate_outline_subscription(**kwargs)
    elif config_format == "v2ray-json":
        config = generate_v2ray_json_subscription(**kwargs)
    else:
        raise ValueError(f'Unsupported format "{config_format}"')

    if as_base64:
        config = base64.b64encode(config.encode()).decode()

    return config


def format_time_left(seconds_left: int) -> str:
    if not seconds_left or seconds_left <= 0:
        return "∞"

    minutes, seconds = divmod(seconds_left, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    months, days = divmod(days, 30)

    result = []
    if months:
        result.append(f"{months}m")
    if days:
        result.append(f"{days}d")
    if hours and (days < 7):
        result.append(f"{hours}h")
    if minutes and not (months or days):
        result.append(f"{minutes}m")
    if seconds and not (months or days):
        result.append(f"{seconds}s")
    return " ".join(result)


def setup_format_variables(extra_data: dict) -> dict:
    from app.models.user import UserStatus

    user_status = extra_data.get("status")
    expire_timestamp = extra_data.get("expire")
    on_hold_expire_duration = extra_data.get("on_hold_expire_duration")
    now = dt.utcnow()
    now_ts = now.timestamp()

    if user_status != UserStatus.on_hold:
        if expire_timestamp is not None and expire_timestamp >= 0:
            seconds_left = expire_timestamp - int(dt.utcnow().timestamp())
            expire_datetime = dt.fromtimestamp(expire_timestamp)
            expire_date = expire_datetime.date()
            jalali_expire_date = jd.fromgregorian(
                year=expire_date.year, month=expire_date.month, day=expire_date.day
            ).strftime("%Y-%m-%d")
            if now_ts < expire_timestamp:
                days_left = (expire_datetime - dt.utcnow()).days + 1
                time_left = format_time_left(seconds_left)
            else:
                days_left = "0"
                time_left = "0"

        else:
            days_left = "∞"
            time_left = "∞"
            expire_date = "∞"
            jalali_expire_date = "∞"
    else:
        if on_hold_expire_duration is not None and on_hold_expire_duration >= 0:
            days_left = timedelta(seconds=on_hold_expire_duration).days
            time_left = format_time_left(on_hold_expire_duration)
            expire_date = "-"
            jalali_expire_date = "-"
        else:
            days_left = "∞"
            time_left = "∞"
            expire_date = "∞"
            jalali_expire_date = "∞"

    if extra_data.get("data_limit"):
        data_limit = readable_size(extra_data["data_limit"])
        data_left = extra_data["data_limit"] - extra_data["used_traffic"]
        if data_left < 0:
            data_left = 0
        data_left = readable_size(data_left)
    else:
        data_limit = "∞"
        data_left = "∞"

    status_emoji = STATUS_EMOJIS.get(extra_data.get("status")) or ""
    status_text = STATUS_TEXTS.get(extra_data.get("status")) or ""

    format_variables = defaultdict(
        lambda: "<missing>",
        {
            "SERVER_IP": SERVER_IP,
            "SERVER_IPV6": SERVER_IPV6,
            "USERNAME": extra_data.get("username", "{USERNAME}"),
            "USER_NOTE": extra_data.get("note", ""),
            "DATA_USAGE": readable_size(extra_data.get("used_traffic")),
            "DATA_LIMIT": data_limit,
            "DATA_LEFT": data_left,
            "DAYS_LEFT": days_left,
            "EXPIRE_DATE": expire_date,
            "JALALI_EXPIRE_DATE": jalali_expire_date,
            "TIME_LEFT": time_left,
            "STATUS_EMOJI": status_emoji,
            "STATUS_TEXT": status_text,
        },
    )

    return format_variables


def process_inbounds_and_tags(
        inbounds: dict,
        proxies: dict,
        format_variables: dict,
        conf: Union[
            V2rayShareLink,
            V2rayJsonConfig,
            SingBoxConfiguration,
            ClashConfiguration,
            ClashMetaConfiguration,
            OutlineConfiguration
        ],
        reverse: bool,
        db: Session,
        user: "UserResponse"
) -> Union[List, str]:
    from app.db import crud
    # DEPRECATED: LoadBalancerHost import removed - functionality replaced with Resilient Node Groups

    _inbounds = []
    for protocol, tags in inbounds.items():
        for tag in tags:
            _inbounds.append((protocol, [tag]))
    index_dict = {proxy: index for index, proxy in enumerate(
        xray.config.inbounds_by_tag.keys())}
    inbounds = sorted(
        _inbounds, key=lambda x: index_dict.get(x[1][0], float('inf')))

    for protocol, tags in inbounds:
        settings = proxies.get(protocol)
        if not settings:
            continue

        format_variables.update({"PROTOCOL": protocol.name})
        for tag in tags:
            inbound = xray.config.inbounds_by_tag.get(tag)
            if not inbound:
                continue

            format_variables.update({"TRANSPORT": inbound["network"]})
            
            # Resilient Node Groups Logic
            host_inbound = inbound.copy()
            for host in xray.hosts.get(tag, []):
                # Check if this host has a resilient node group assigned
                resilient_node_group_id = host.get("resilient_node_group_id")
                if resilient_node_group_id:
                    # Get the resilient node group and select a node
                    resilient_group = crud.get_resilient_node_group(db, resilient_node_group_id)
                    if resilient_group and resilient_group.nodes:
                        # Filter active nodes
                        active_nodes = [node for node in resilient_group.nodes if node.status == NodeStatus.connected]
                        if active_nodes:
                            # Select node based on strategy hint
                            selected_node = _select_node_by_strategy(
                                active_nodes,
                                resilient_group.client_strategy_hint,
                                user.id,
                                db
                            )
                            # Use the selected node's address instead of host address
                            node_address = selected_node.address

                            # Track this node selection for connection monitoring
                            # Note: We can't track the actual connection here since this is just
                            # subscription generation, but we can log the node assignment
                            try:
                                from app.services.connection_tracker import connection_tracker
                                # This helps us understand which nodes are being assigned to users
                                logger.debug(f"Assigned user {user.id} to node {selected_node.id} ({selected_node.name}) via strategy {resilient_group.client_strategy_hint}")
                            except Exception:
                                pass  # Don't fail subscription generation if tracking fails
                        else:
                            # No active nodes, fall back to host address
                            node_address = None
                    else:
                        # Group not found or empty, fall back to host address
                        node_address = None
                else:
                    # No resilient node group, use traditional logic
                    node_address = None
                sni = ""
                sni_list = host["sni"] or inbound["sni"]
                if sni_list:
                    salt = secrets.token_hex(8)
                    sni = random.choice(sni_list).replace("*", salt)

                if sids := inbound.get("sids"):
                    inbound["sid"] = random.choice(sids)

                req_host = ""
                req_host_list = host["host"] or inbound["host"]
                if req_host_list:
                    salt = secrets.token_hex(8)
                    req_host = random.choice(req_host_list).replace("*", salt)

                # Use node address from resilient group if available, otherwise use host address
                if node_address:
                    # Use the selected node's address
                    address = node_address.format_map(format_variables)
                else:
                    # Traditional host address logic
                    address = ""
                    address_list = host['address']
                    if host['address']:
                        salt = secrets.token_hex(8)
                        address = random.choice(address_list).replace('*', salt)

                if host["path"] is not None:
                    path = host["path"].format_map(format_variables)
                else:
                    path = inbound.get("path", "").format_map(format_variables)

                if host.get("use_sni_as_host", False) and sni:
                    req_host = sni

                host_inbound.update(
                    {
                        "port": host["port"] or inbound["port"],
                        "sni": sni,
                        "host": req_host,
                        "tls": inbound["tls"] if host["tls"] is None else host["tls"],
                        "alpn": host["alpn"] if host["alpn"] else None,
                        "path": path,
                        "fp": host["fingerprint"] or inbound.get("fp", ""),
                        "ais": host["allowinsecure"]
                        or inbound.get("allowinsecure", ""),
                        "mux_enable": host["mux_enable"],
                        "fragment_setting": host["fragment_setting"],
                        "noise_setting": host["noise_setting"],
                        "random_user_agent": host["random_user_agent"],
                    }
                )

                conf.add(
                    remark=host["remark"].format_map(format_variables),
                    address=address.format_map(format_variables),
                    inbound=host_inbound,
                    settings=settings.model_dump()
                )

    return conf.render(reverse=reverse)


def encode_title(text: str, format_variables: dict = None) -> str:
    if format_variables:
        text = text.format_map(format_variables)
    return f"base64:{base64.b64encode(text.encode()).decode()}"
