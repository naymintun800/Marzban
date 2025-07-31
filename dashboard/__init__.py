import atexit
import os
import subprocess
from pathlib import Path

from fastapi.staticfiles import StaticFiles

from app import app, on_startup
from config import DASHBOARD_PATH, DEBUG, UVICORN_PORT, VITE_BASE_API

base_dir = Path(__file__).parent
build_dir = base_dir / "build"
statics_dir = build_dir / "statics"


def build_api_interface():
    subprocess.Popen(
        ["bun", "run", "wait-port-gen-api"],
        env={**os.environ, "UVICORN_PORT": str(UVICORN_PORT)},
        cwd=base_dir,
        stdout=subprocess.DEVNULL,
    )


def build():
    proc = subprocess.Popen(
        ["bun", "run", "build", "--outDir", build_dir, "--assetsDir", "statics"],
        env={**os.environ, "VITE_BASE_API": VITE_BASE_API},
        cwd=base_dir,
    )
    proc.wait()
    with open(build_dir / "index.html", "r") as file:
        html = file.read()
    with open(build_dir / "404.html", "w") as file:
        file.write(html)


def run_dev():
    build_api_interface()
    proc = subprocess.Popen(
        ["bun", "run", "dev", "--base", os.path.join(DASHBOARD_PATH, "")],
        env={**os.environ, "VITE_BASE_API": VITE_BASE_API, "DEBUG": "false"},
        cwd=base_dir,
    )

    atexit.register(proc.terminate)


def run_build():
    # Only build if build directory doesn't exist (for development)
    # In production, dashboard should be pre-built in Docker image
    if not build_dir.is_dir():
        print("📦 Build directory missing, attempting to build dashboard...")
        try:
            build()
        except FileNotFoundError as e:
            if 'bun' in str(e):
                print("❌ bun not found - dashboard should be pre-built in Docker image")
                print("   Please ensure your Docker build process includes dashboard build step")
                return
            else:
                raise
    else:
        print(f"📁 Using pre-built dashboard from {build_dir}")
    
    # Mount static files
    ensure_static_mount()


@on_startup
def run_dashboard():
    print(f"🚀 Starting dashboard - DEBUG: {DEBUG}")
    if DEBUG:
        print("📝 Running in development mode")
        run_dev()
    else:
        print("🏗️ Running in production mode")
        run_build()


# Check if we should mount immediately (avoid duplicate mounting)
_mounted = False

def ensure_static_mount():
    """Ensure static files are mounted exactly once."""
    global _mounted
    if _mounted:
        print("📁 Static files already mounted")
        return
        
    if not build_dir.exists():
        print(f"❌ Build directory not found: {build_dir}")
        return
        
    if not statics_dir.exists():
        print(f"❌ Statics directory not found: {statics_dir}")
        return
    
    try:
        # Remove any existing mounts to prevent conflicts
        original_routes_count = len(app.routes)
        app.routes[:] = [route for route in app.routes if not (
            hasattr(route, 'name') and route.name and 
            route.name.startswith(('dashboard', 'statics'))
        )]
        
        removed_routes = original_routes_count - len(app.routes)
        if removed_routes > 0:
            print(f"🔄 Removed {removed_routes} existing static route(s)")
        
        # Mount static files with proper order (most specific first)
        app.mount("/statics/", StaticFiles(directory=statics_dir, html=True), name="statics")
        app.mount(DASHBOARD_PATH, StaticFiles(directory=build_dir, html=True), name="dashboard")
        
        print(f"✅ Successfully mounted static files:")
        print(f"   /statics/ -> {statics_dir}")
        print(f"   {DASHBOARD_PATH} -> {build_dir}")
        _mounted = True
        
    except Exception as e:
        print(f"❌ Failed to mount static files: {e}")
        import traceback
        print(f"   Error details: {traceback.format_exc()}")
        _mounted = False

# Mount immediately if not in DEBUG mode
if not DEBUG:
    ensure_static_mount()
