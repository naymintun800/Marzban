import logging

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from config import ALLOWED_ORIGINS, DOCS, XRAY_SUBSCRIPTION_PATH

__version__ = "0.8.4"

app = FastAPI(
    title="MarzbanAPI",
    description="Unified GUI Censorship Resistant Solution Powered by Xray",
    version=__version__,
    docs_url="/docs" if DOCS else None,
    redoc_url="/redoc" if DOCS else None,
)

scheduler = BackgroundScheduler(
    {"apscheduler.job_defaults.max_instances": 20}, timezone="UTC"
)
logger = logging.getLogger("uvicorn.error")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
from app import dashboard, jobs, routers, telegram  # noqa
from app.routers import api_router  # noqa
from app.routers.subscription import router as subscription_router, custom_subscription_router  # noqa

# Debug flag - set to False to disable custom subscription router
ENABLE_CUSTOM_SUBSCRIPTION = True

# Debug: Print routes being registered
print("=== REGISTERING API ROUTER ===")
for route in api_router.routes:
    if hasattr(route, 'path'):
        print(f"API Route: {route.path} - Methods: {getattr(route, 'methods', 'N/A')}")

app.include_router(api_router)

print("=== REGISTERING SUBSCRIPTION ROUTER ===")
for route in subscription_router.routes:
    if hasattr(route, 'path'):
        print(f"Subscription Route: {route.path} - Methods: {getattr(route, 'methods', 'N/A')}")

# Default subscription router first for specific path matching (e.g., /sub/token)
app.include_router(subscription_router)

if ENABLE_CUSTOM_SUBSCRIPTION:
    print("=== REGISTERING CUSTOM SUBSCRIPTION ROUTER ===")
    for route in custom_subscription_router.routes:
        if hasattr(route, 'path'):
            print(f"Custom Route: {route.path} - Methods: {getattr(route, 'methods', 'N/A')}")
    # Custom/generic router after specific ones
    app.include_router(custom_subscription_router)
else:
    print("=== CUSTOM SUBSCRIPTION ROUTER DISABLED ===") # Added an else for clarity

def use_route_names_as_operation_ids(app: FastAPI) -> None:
    for route in app.routes:
        if isinstance(route, APIRoute):
            route.operation_id = route.name


use_route_names_as_operation_ids(app)


@app.on_event("startup")
def on_startup():
    # Debug: Print all final routes
    print("=== ALL FINAL ROUTES ===")
    for route in app.routes:
        if hasattr(route, 'path'):
            print(f"Final Route: {route.path} - Methods: {getattr(route, 'methods', 'N/A')}")
    
    # Debug: Print database info
    from app.db import get_db
    from app.db.crud import get_admins
    from config import SQLALCHEMY_DATABASE_URL
    print(f"=== DATABASE INFO ===")
    print(f"Database URL: {SQLALCHEMY_DATABASE_URL}")
    
    try:
        with next(get_db()) as db:
            admins = get_admins(db)
            print(f"Admin count on startup: {len(admins)}")
            for admin in admins:
                print(f"  - Admin: {admin.username} (sudo: {admin.is_sudo})")
    except Exception as e:
        print(f"Error checking admins: {e}")
    
    paths = [f"{r.path}/" for r in app.routes]
    paths.append("/api/")
    if f"/{XRAY_SUBSCRIPTION_PATH}/" in paths:
        raise ValueError(
            f"you can't use /{XRAY_SUBSCRIPTION_PATH}/ as subscription path it reserved for {app.title}"
        )
    scheduler.start()


@app.on_event("shutdown")
def on_shutdown():
    scheduler.shutdown()


@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exc: RequestValidationError):
    details = {}
    for error in exc.errors():
        details[error["loc"][-1]] = error.get("msg")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({"detail": details}),
    )
