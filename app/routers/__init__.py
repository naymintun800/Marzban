from fastapi import APIRouter

from . import admin, core, group, hiddify_import, home, host, node, resilient_node_group, settings, subscription, system, user, user_template

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
    resilient_node_group.router,
    user.router,
    subscription.router,
    user_template.router,
    hiddify_import.router,
]

for router in routers:
    api_router.include_router(router)

__all__ = ["api_router"]
