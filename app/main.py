"""Scan2Target FastAPI application entrypoint."""

from contextlib import asynccontextmanager
from pathlib import Path
import asyncio
import logging
import os
import sys

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Ensure local app modules are importable regardless of how uvicorn is started
# e.g. from repository root via `uvicorn app.main:app` under systemd.
APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core.logging_config import setup_logging
from api import scan, targets, auth, history, devices, maintenance, websocket, stats, homeassistant
from core.init_db import init_database
from core.scanning.health import get_health_monitor


# Initialize logging first
setup_logging()
logger = logging.getLogger(__name__)


def get_version() -> str:
    """Read version from VERSION file."""
    version_file = Path(__file__).parent.parent / "VERSION"
    try:
        return version_file.read_text().strip()
    except Exception:
        return "0.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("=" * 60)
    logger.info("Starting Scan2Target...")
    logger.info("=" * 60)

    init_database()
    logger.info("Database initialized")

    # Start health monitor FIRST for automatic scanner status checks
    health_check_interval = int(os.getenv("SCAN2TARGET_HEALTH_CHECK_INTERVAL", "60"))
    health_monitor = get_health_monitor(check_interval=health_check_interval)
    await health_monitor.start()
    logger.info(f"Health monitor started (interval: {health_check_interval}s)")
    logger.info("Note: Using 15s intervals for first 5 minutes to detect scanners quickly")

    # Initialize scanner cache in background (non-blocking)
    logger.info("Starting scanner discovery in background...")

    async def safe_scanner_init():
        """Wrapper für Scanner-Discovery mit Error-Handling."""
        try:
            logger.info("Background task: Starting scanner initialization...")
            await asyncio.to_thread(devices.init_scanner_cache)
            logger.info("Background task: Scanner initialization completed successfully")
        except Exception as e:
            logger.error(f"Background task: Scanner initialization failed: {e}", exc_info=True)

    scanner_task = asyncio.create_task(safe_scanner_init())

    logger.info("=" * 60)
    logger.info("Scan2Target is ready!")
    logger.info("=" * 60)

    yield

    logger.info("Shutting down Scan2Target...")

    if not scanner_task.done():
        logger.info("Cancelling scanner discovery task...")
        scanner_task.cancel()
        try:
            await scanner_task
        except asyncio.CancelledError:
            logger.info("Scanner discovery task cancelled")

    await health_monitor.stop()
    logger.info("Scan2Target stopped")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Scan2Target",
        version=get_version(),
        lifespan=lifespan,
        redirect_slashes=False,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # tighten in production or configure via settings
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routes
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(scan.router, prefix="/api/v1/scan", tags=["scan"])
    app.include_router(devices.router, prefix="/api/v1/devices", tags=["devices"])
    app.include_router(targets.router, prefix="/api/v1/targets", tags=["targets"])
    app.include_router(history.router, prefix="/api/v1/history", tags=["history"])
    app.include_router(maintenance.router, prefix="/api/v1/maintenance", tags=["maintenance"])
    app.include_router(websocket.router, prefix="/api/v1", tags=["websocket"])
    app.include_router(stats.router, prefix="/api/v1/stats", tags=["stats"])
    app.include_router(homeassistant.router, prefix="/api/v1/homeassistant", tags=["homeassistant"])

    # Serve thumbnails from temp directory
    thumbnail_dir = Path("/tmp/scan2target/scans")
    thumbnail_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/thumbnails", StaticFiles(directory=str(thumbnail_dir)), name="thumbnails")

    @app.get("/health", tags=["health"])
    async def health():
        return {"status": "ok", "version": get_version()}

    @app.get("/api/v1/version", tags=["info"])
    async def version():
        """Get application version."""
        return {"version": get_version()}

    # Serve Web UI
    web_dist = Path(__file__).parent / "web" / "dist"
    web_dev = Path(__file__).parent / "web" / "index.html"

    if web_dist.exists():
        # Production: serve built assets
        app.mount("/assets", StaticFiles(directory=str(web_dist / "assets")), name="assets")

        @app.get("/service-worker.js", include_in_schema=False)
        async def serve_service_worker():
            sw_file = web_dist / "service-worker.js"
            if not sw_file.exists():
                raise HTTPException(status_code=404, detail="Service worker not found")

            response = FileResponse(str(sw_file), media_type="application/javascript")
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            return response

        @app.get("/manifest.json", include_in_schema=False)
        async def serve_manifest():
            manifest_file = web_dist / "manifest.json"
            if not manifest_file.exists():
                raise HTTPException(status_code=404, detail="Manifest not found")

            response = FileResponse(str(manifest_file), media_type="application/manifest+json")
            response.headers["Cache-Control"] = "no-cache"
            return response

        @app.get("/icon-192.png", include_in_schema=False)
        async def serve_icon_192():
            icon_file = web_dist / "icon-192.png"
            if not icon_file.exists():
                raise HTTPException(status_code=404, detail="Icon not found")

            return FileResponse(str(icon_file), media_type="image/png")

        @app.get("/icon-96.png", include_in_schema=False)
        async def serve_icon_96():
            icon_file = web_dist / "icon-96.png"
            if not icon_file.exists():
                raise HTTPException(status_code=404, detail="Icon not found")

            return FileResponse(str(icon_file), media_type="image/png")

        @app.get("/")
        async def serve_root():
            index_file = web_dist / "index.html"
            response = FileResponse(str(index_file))
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            return response

        @app.get("/mobile")
        async def serve_mobile():
            # Legacy mobile UI removed; always use the current unified WebUI.
            index_file = web_dist / "index.html"
            response = FileResponse(str(index_file))
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            return response

    elif web_dev.exists():
        # Development: serve from web directory
        app.mount("/src", StaticFiles(directory=str(web_dev.parent / "src")), name="src")

        @app.get("/")
        async def serve_root():
            response = FileResponse(str(web_dev))
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            return response

        @app.get("/mobile")
        async def serve_mobile():
            # Legacy mobile UI removed; always use the current unified WebUI.
            response = FileResponse(str(web_dev))
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            return response

    else:
        @app.get("/")
        async def serve_root():
            return {
                "message": "Scan2Target API",
                "docs": "/docs",
                "health": "/health",
                "note": "Web UI not found. Run 'cd app/web && npm run build' or 'npm run dev'",
            }

    return app


app = create_app()
