"""Scan2Target FastAPI application entrypoint."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from pathlib import Path
import os
import logging

from core.logging_config import setup_logging
from api import scan, targets, auth, history, devices, maintenance, websocket, stats, homeassistant
from core.init_db import init_database
from core.scanning.health import get_health_monitor

# Initialize logging first
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("=" * 60)
    logger.info("Starting Scan2Target...")
    logger.info("=" * 60)
    
    init_database()
    logger.info("Database initialized")
    
    # Initialize scanner cache with retries to handle delayed scanner availability
    devices.init_scanner_cache()
    
    # Start health monitor for automatic scanner status checks
    health_check_interval = int(os.getenv('SCAN2TARGET_HEALTH_CHECK_INTERVAL', '60'))
    health_monitor = get_health_monitor(check_interval=health_check_interval)
    await health_monitor.start()
    logger.info(f"Health monitor started (interval: {health_check_interval}s)")
    logger.info("Note: Using 15s intervals for first 5 minutes to detect scanners quickly")
    
    logger.info("=" * 60)
    logger.info("Scan2Target is ready!")
    logger.info("=" * 60)
    
    yield
    
    # Shutdown
    logger.info("Shutting down Scan2Target...")
    await health_monitor.stop()
    logger.info("Scan2Target stopped")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Scan2Target",
        version="0.1.0",
        lifespan=lifespan,
        redirect_slashes=False  # Prevent 307 redirects on trailing slashes
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # tighten in production or configure via settings
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
    
    # Serve thumbnails from temp directory
    thumbnail_dir = Path("/tmp/scan2target/scans")
    thumbnail_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/thumbnails", StaticFiles(directory=str(thumbnail_dir)), name="thumbnails")

    @app.get("/health", tags=["health"])
    async def health():
        return {"status": "ok"}

    # Serve Web UI
    web_dist = Path(__file__).parent / "web" / "dist"
    web_dev = Path(__file__).parent / "web" / "index.html"
    
    if web_dist.exists():
        # Production: serve built assets
        app.mount("/assets", StaticFiles(directory=str(web_dist / "assets")), name="assets")
        
        @app.get("/")
        async def serve_root():
            return FileResponse(str(web_dist / "index.html"))
        
        @app.get("/mobile")
        async def serve_mobile():
            mobile_html = web_dist / "mobile.html"
            if mobile_html.exists():
                return FileResponse(str(mobile_html))
            else:
                return FileResponse(str(web_dist / "index.html"))
    elif web_dev.exists():
        # Development: serve from web directory
        app.mount("/src", StaticFiles(directory=str(web_dev.parent / "src")), name="src")
        
        @app.get("/")
        async def serve_root():
            return FileResponse(str(web_dev))
        
        @app.get("/mobile")
        async def serve_mobile():
            mobile_html = web_dev.parent / "mobile.html"
            if mobile_html.exists():
                return FileResponse(str(mobile_html))
            else:
                return FileResponse(str(web_dev))
    else:
        @app.get("/")
        async def serve_root():
            return {
                "message": "Scan2Target API",
                "docs": "/docs",
                "health": "/health",
                "note": "Web UI not found. Run 'cd app/web && npm run build' or 'npm run dev'"
            }

    return app


app = create_app()
