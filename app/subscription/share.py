import base64
import random
import secrets
from collections import defaultdict
from datetime import datetime as dt
from datetime import timedelta
from typing import TYPE_CHECKING, List, Literal, Union, Optional

from jdatetime import date as jd
from sqlalchemy.orm import Session

from app import xray
from app.utils.system import get_public_ip, get_public_ipv6, readable_size
from app.db import crud
from app.db.models import LoadBalancerHost, Node as NodeDbModel
from app.models.load_balancer import LoadBalancerStrategy
from app.models.node import NodeStatus

from . import *

if TYPE_CHECKING:
    from app.models.user import UserResponse

from config import (
    ACTIVE_STATUS_TEXT,
    DISABLED_STATUS_TEXT,
    EXPIRED_STATUS_TEXT,
    LIMITED_STATUS_TEXT,
    ONHOLD_STATUS_TEXT,
)

SERVER_IP = get_public_ip()
SERVER_IPV6 = get_public_ipv6()
ROUND_ROBIN_COUNTERS = defaultdict(int)

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


def _select_node_from_load_balancer(lb_config: LoadBalancerHost, user_id: int, db: Session) -> Optional[NodeDbModel]:
    """Selects a node from the load balancer based on its strategy."""
    if not lb_config.nodes:
        return None

    # Filter for active and non-disabled nodes
    # Assuming NodeDbModel has is_disabled, if not, adjust or rely on status only
    active_nodes = [
        node for node in lb_config.nodes 
        if node.status == NodeStatus.connected # and not getattr(node, 'is_disabled', False) # is_disabled is on ProxyHost not Node itself
    ]

    if not active_nodes:
        return None

    strategy = lb_config.load_balancing_strategy
    selected_node = None

    if strategy == LoadBalancerStrategy.ROUND_ROBIN:
        counter_key = lb_config.id
        current_index = ROUND_ROBIN_COUNTERS[counter_key]
        selected_node = active_nodes[current_index % len(active_nodes)]
        ROUND_ROBIN_COUNTERS[counter_key] = (current_index + 1)
    elif strategy == LoadBalancerStrategy.RANDOM:
        selected_node = random.choice(active_nodes)
    # Add other strategies here if needed (e.g., LEAST_CONNECTIONS)
    else: # Default to RANDOM if strategy is unknown or not implemented
        selected_node = random.choice(active_nodes)
        
    return selected_node


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
            
            # --- Load Balancer Logic ---
            db_load_balancers = crud.get_load_balancer_hosts_for_inbound(db, tag)
            processed_with_lb = False
            if db_load_balancers:
                for lb_config in db_load_balancers:
                    if lb_config.is_disabled:
                        continue
                    
                    selected_node = _select_node_from_load_balancer(lb_config, user.id, db)
                    if not selected_node:
                        continue # No active node for this LB config, try next LB or static host
                    
                    processed_with_lb = True
                    
                    # Use LoadBalancerHost's own settings, falling back to inbound defaults
                    lb_host_inbound_settings = inbound.copy() # Start with base inbound settings

                    # Override with LB-specific settings
                    # Note: LoadBalancerHost model has direct fields, not lists like ProxyHost's sni/host
                    # The address field of LoadBalancerHost is the "virtual" address, not the node's.
                    # The selected_node.address is what clients will connect to.
                    
                    current_sni = lb_config.sni if lb_config.sni is not None else inbound["sni"]
                    final_sni = ""
                    if isinstance(current_sni, list) and current_sni:
                        salt = secrets.token_hex(8)
                        final_sni = random.choice(current_sni).replace("*", salt)
                    elif isinstance(current_sni, str):
                        final_sni = current_sni

                    current_host_header = lb_config.host_header if lb_config.host_header is not None else inbound["host"]
                    final_host_header = ""
                    if isinstance(current_host_header, list) and current_host_header:
                        salt = secrets.token_hex(8)
                        final_host_header = random.choice(current_host_header).replace("*", salt)
                    elif isinstance(current_host_header, str):
                        final_host_header = current_host_header

                    lb_path = lb_config.path if lb_config.path is not None else inbound.get("path", "")
                    final_path = lb_path.format_map(format_variables)

                    if lb_config.use_sni_as_host and final_sni:
                        final_host_header = final_sni

                    lb_host_inbound_settings.update({
                        "port": lb_config.port if lb_config.port is not None else inbound["port"],
                        "sni": final_sni,
                        "host": final_host_header,
                        "tls": lb_config.security.value if lb_config.security != "inbound_default" else inbound["tls"], # Assuming ProxyHostSecurity enum
                        "alpn": lb_config.alpn.value if lb_config.alpn != "none" else (inbound.get("alpn") if inbound.get("alpn") else None), # Assuming ProxyHostALPN enum
                        "path": final_path,
                        "fp": lb_config.fingerprint.value if lb_config.fingerprint != "none" else inbound.get("fp", ""), # Assuming ProxyHostFingerprint enum
                        "ais": lb_config.allowinsecure if lb_config.allowinsecure is not None else inbound.get("allowinsecure", False),
                        "mux_enable": lb_config.mux_enable if lb_config.mux_enable is not None else inbound.get("mux_enable", False),
                        "fragment_setting": lb_config.fragment_setting if lb_config.fragment_setting is not None else inbound.get("fragment_setting"),
                        "noise_setting": lb_config.noise_setting if lb_config.noise_setting is not None else inbound.get("noise_setting"),
                        "random_user_agent": lb_config.random_user_agent if lb_config.random_user_agent is not None else inbound.get("random_user_agent", False),
                    })

                    conf.add(
                        remark=lb_config.remark_template.format_map(format_variables),
                        address=selected_node.address.format_map(format_variables), # Node's actual address
                        inbound=lb_host_inbound_settings,
                        settings=settings.model_dump()
                    )
                
                if processed_with_lb:
                    continue # Move to the next tag if LBs were processed for this one
            # --- End Load Balancer Logic ---

            # Original ProxyHost logic (if no LB or no active LBs for this tag)
            host_inbound = inbound.copy()
            for host in xray.hosts.get(tag, []):
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


def encode_title(text: str) -> str:
    return f"base64:{base64.b64encode(text.encode()).decode()}"
