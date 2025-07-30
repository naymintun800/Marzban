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
    if not build_dir.is_dir():
        build()

    # Ensure directories exist before mounting
    if build_dir.exists() and statics_dir.exists():
        try:
            # Mount static files first (more specific route)
            app.mount("/statics/", StaticFiles(directory=statics_dir, html=True), name="statics")
            print(f"✅ Mounted statics: /statics/ -> {statics_dir}")
            
            # Mount dashboard (catch-all for HTML)
            app.mount(DASHBOARD_PATH, StaticFiles(directory=build_dir, html=True), name="dashboard")
            print(f"✅ Mounted dashboard: {DASHBOARD_PATH} -> {build_dir}")
            
        except Exception as e:
            print(f"❌ Error mounting static files: {e}")
            # Force mount with different approach
            try:
                from fastapi import FastAPI
                from fastapi.staticfiles import StaticFiles
                
                # Remove existing mounts if they exist
                app.routes = [route for route in app.routes if not (
                    hasattr(route, 'name') and route.name in ['dashboard', 'statics']
                )]
                
                # Re-mount
                app.mount("/statics/", StaticFiles(directory=statics_dir, html=True), name="statics")
                app.mount(DASHBOARD_PATH, StaticFiles(directory=build_dir, html=True), name="dashboard")
                print(f"✅ Force-mounted static files successfully")
                
            except Exception as e2:
                print(f"❌ Failed to force-mount static files: {e2}")
    else:
        print(f"❌ Dashboard directories not found:")
        print(f"   build_dir exists: {build_dir.exists()} ({build_dir})")
        print(f"   statics_dir exists: {statics_dir.exists()} ({statics_dir})")


@on_startup
def run_dashboard():
    print(f"🚀 Starting dashboard - DEBUG: {DEBUG}")
    if DEBUG:
        print("📝 Running in development mode")
        run_dev()
    else:
        print("🏗️ Running in production mode")
        run_build()


# Failsafe: Mount static files immediately if not in DEBUG mode
# This ensures static files are available even if startup hooks fail
if not DEBUG and build_dir.exists() and statics_dir.exists():
    try:
        app.mount("/statics/", StaticFiles(directory=statics_dir, html=True), name="statics_immediate")
        app.mount(DASHBOARD_PATH, StaticFiles(directory=build_dir, html=True), name="dashboard_immediate")
        print(f"🔧 Immediate mount: statics and dashboard")
    except Exception as e:
        print(f"⚠️ Immediate mount failed: {e}")
        # Will be retried in run_dashboard()
