from fastapi import APIRouter
from . import admin, core, node, subscription, system, user_template, user, home, host, group, dev, settings, resilient_node_group, custom_subscription

api_router = APIRouter()

routers = [
    home.router,
    admin.router,
    system.router,
    settings.router,
    group.router,
    core.router,
    host.router,
    node.router,
    user.router,
    subscription.router,
    user_template.router,
    resilient_node_group.router,
    custom_subscription.router,
    dev.router,
]

for router in routers:
    api_router.include_router(router)

__all__ = ["api_router"]
