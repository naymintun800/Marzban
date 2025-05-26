from fastapi import APIRouter
from . import (
    admin, 
    core, 
    node, 
    subscription, 
    system, 
    user_template, 
    user,
    home,
)

api_router = APIRouter()

# Only include routers that have /api prefix or are meant to be in API
routers = [
    admin.router,
    core.router,
    node.router,
    # subscription.router,  # Removed - has root level routes that conflict
    system.router,
    user_template.router,
    user.router,
    home.router,
]

for router in routers:
    api_router.include_router(router)

__all__ = ["api_router"]