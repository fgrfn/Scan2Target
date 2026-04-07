"""Scan2Target FastAPI application entrypoint."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from pathlib import Path
import asyncio
import logging

from core.logging_config import setup_logging
from api import scan, targets, auth, history, devices, maintenance, websocket, stats, homeassistant
from core.init_db import init_database
from core.scanning.health import get_health_monitor

# Logging must be configured before anything else touches a logger.
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
    from core.config.settings import get_settings
    settings = get_settings()

    logger.info("=" * 60)
    logger.info("Starting Scan2Target...")
    logger.info("=" * 60)

    init_database()
    logger.info("Database initialised")

    health_monitor = get_health_monitor(check_interval=settings.health_check_interval)
    await health_monitor.start()
    logger.info("Health monitor started (interval: %ds)", settings.health_check_interval)
    logger.info("Note: Using 15 s intervals for the first 5 minutes to detect scanners quickly")

    logger.info("Starting scanner discovery in background…")

    async def safe_scanner_init():
        try:
            logger.info("Background task: starting scanner initialisation…")
            await asyncio.to_thread(devices.init_scanner_cache)
            logger.info("Background task: scanner initialisation complete")
        except Exception as exc:
            logger.error("Background task: scanner initialisation failed: %s", exc, exc_info=True)

    scanner_task = asyncio.create_task(safe_scanner_init())

    logger.info("=" * 60)
    logger.info("Scan2Target is ready!")
    logger.info("=" * 60)

    yield

    logger.info("Shutting down Scan2Target…")
    if not scanner_task.done():
        scanner_task.cancel()
        try:
            await scanner_task
        except asyncio.CancelledError:
            logger.info("Scanner discovery task cancelled")

    await health_monitor.stop()
    logger.info("Scan2Target stopped")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    from core.config.settings import get_settings
    settings = get_settings()

    app = FastAPI(
        title="Scan2Target",
        version=get_version(),
        lifespan=lifespan,
        redirect_slashes=False,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(scan.router, prefix="/api/v1/scan", tags=["scan"])
    app.include_router(devices.router, prefix="/api/v1/devices", tags=["devices"])
    app.include_router(targets.router, prefix="/api/v1/targets", tags=["targets"])
    app.include_router(history.router, prefix="/api/v1/history", tags=["history"])
    app.include_router(maintenance.router, prefix="/api/v1/maintenance", tags=["maintenance"])
    app.include_router(websocket.router, prefix="/api/v1", tags=["websocket"])
    app.include_router(stats.router, prefix="/api/v1/stats", tags=["stats"])
    app.include_router(homeassistant.router, prefix="/api/v1/homeassistant", tags=["homeassistant"])

    thumbnail_dir = Path(settings.temp_dir)
    thumbnail_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/thumbnails", StaticFiles(directory=str(thumbnail_dir)), name="thumbnails")

    @app.get("/health", tags=["health"])
    async def health():
        return {"status": "ok", "version": get_version()}

    @app.get("/api/v1/version", tags=["info"])
    async def version():
        return {"version": get_version()}

    web_dist = Path(__file__).parent / "web" / "dist"
    web_dev = Path(__file__).parent / "web" / "index.html"

    if web_dist.exists():
        app.mount("/assets", StaticFiles(directory=str(web_dist / "assets")), name="assets")

        @app.get("/")
        async def serve_root():
            return FileResponse(str(web_dist / "index.html"))

        @app.get("/mobile")
        async def serve_mobile():
            mobile_html = web_dist / "mobile.html"
            return FileResponse(str(mobile_html if mobile_html.exists() else web_dist / "index.html"))

    elif web_dev.exists():
        app.mount("/src", StaticFiles(directory=str(web_dev.parent / "src")), name="src")

        @app.get("/")
        async def serve_root():
            return FileResponse(str(web_dev))

        @app.get("/mobile")
        async def serve_mobile():
            mobile_html = web_dev.parent / "mobile.html"
            return FileResponse(str(mobile_html if mobile_html.exists() else web_dev))

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
