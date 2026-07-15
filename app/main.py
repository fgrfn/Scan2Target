"""Scan2Target FastAPI application entrypoint."""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from api import auth, devices, history, homeassistant, maintenance, profiles, scan, stats, targets, websocket
from core.config.settings import get_settings
from core.delivery.retry import get_delivery_retry_service
from core.init_db import init_database
from core.logging_config import setup_logging
from core.scanning.health import get_health_monitor
from core.websocket import register_main_loop

setup_logging()
logger = logging.getLogger(__name__)


class NoCacheStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response


def no_cache_file(path: Path, media_type: str | None = None) -> FileResponse:
    response = FileResponse(str(path), media_type=media_type)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


def get_version() -> str:
    version_file = Path(__file__).parent.parent / "VERSION"
    try:
        return version_file.read_text().strip()
    except OSError as exc:
        logger.warning("Could not read VERSION file (%s): %s", version_file, exc)
        return "0.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize persistent state and background services."""
    logger.info("Starting Scan2Target")
    register_main_loop(asyncio.get_running_loop())
    init_database()

    retry_service = get_delivery_retry_service()
    await retry_service.start()

    health_check_interval = int(os.getenv("SCAN2TARGET_HEALTH_CHECK_INTERVAL", "60"))
    health_monitor = get_health_monitor(check_interval=health_check_interval)
    await health_monitor.start()

    async def safe_scanner_init():
        try:
            await asyncio.to_thread(devices.init_scanner_cache)
        except Exception as exc:
            logger.error("Background scanner initialization failed: %s", exc, exc_info=True)

    scanner_task = asyncio.create_task(safe_scanner_init(), name="scanner-initialization")
    logger.info("Scan2Target is ready")
    try:
        yield
    finally:
        logger.info("Shutting down Scan2Target")
        if not scanner_task.done():
            scanner_task.cancel()
            try:
                await scanner_task
            except asyncio.CancelledError:
                pass
        await health_monitor.stop()
        await retry_service.stop()
        logger.info("Scan2Target stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Scan2Target",
        version=get_version(),
        lifespan=lifespan,
        redirect_slashes=False,
    )
    settings = get_settings()
    origins = settings.cors_origin_list
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=bool(origins),
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-API-Key"],
    )

    @app.middleware("http")
    async def enforce_request_size(request: Request, call_next):
        max_bytes = settings.max_request_size_mb * 1024 * 1024
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > max_bytes:
                    return JSONResponse(
                        status_code=413,
                        content={"detail": f"Request body exceeds {settings.max_request_size_mb} MB"},
                    )
            except ValueError:
                return JSONResponse(status_code=400, content={"detail": "Invalid Content-Length"})
        return await call_next(request)

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        return response

    if settings.require_auth:
        from core.auth.manager import get_auth_manager

        auth_exempt_prefixes = ("/api/v1/auth/", "/api/v1/homeassistant/")
        auth_exempt_paths = ("/health", "/api/v1/version")

        @app.middleware("http")
        async def enforce_auth(request: Request, call_next):
            path = request.url.path
            needs_auth = (
                path.startswith("/api/")
                and path not in auth_exempt_paths
                and not any(path.startswith(prefix) for prefix in auth_exempt_prefixes)
            )
            if needs_auth and request.method != "OPTIONS":
                header = request.headers.get("authorization", "")
                token = header[7:] if header.lower().startswith("bearer ") else None
                if not token or not get_auth_manager().verify_token(token):
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "Authentication required"},
                        headers={"WWW-Authenticate": "Bearer"},
                    )
            return await call_next(request)

    app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(scan.router, prefix="/api/v1/scan", tags=["scan"])
    app.include_router(profiles.router, prefix="/api/v1/profiles", tags=["profiles"])
    app.include_router(devices.router, prefix="/api/v1/devices", tags=["devices"])
    app.include_router(targets.router, prefix="/api/v1/targets", tags=["targets"])
    app.include_router(history.router, prefix="/api/v1/history", tags=["history"])
    app.include_router(maintenance.router, prefix="/api/v1/maintenance", tags=["maintenance"])
    app.include_router(websocket.router, prefix="/api/v1", tags=["websocket"])
    app.include_router(stats.router, prefix="/api/v1/stats", tags=["stats"])
    app.include_router(homeassistant.router, prefix="/api/v1/homeassistant", tags=["homeassistant"])

    thumbnail_dir = Path("/tmp/scan2target/scans")
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
        app.mount("/assets", NoCacheStaticFiles(directory=str(web_dist / "assets")), name="assets")

        @app.get("/service-worker.js", include_in_schema=False)
        async def serve_service_worker():
            path = web_dist / "service-worker.js"
            if not path.exists():
                raise HTTPException(status_code=404, detail="Service worker not found")
            return no_cache_file(path, "application/javascript")

        @app.get("/manifest.json", include_in_schema=False)
        async def serve_manifest():
            path = web_dist / "manifest.json"
            if not path.exists():
                raise HTTPException(status_code=404, detail="Manifest not found")
            return no_cache_file(path, "application/manifest+json")

        @app.get("/icon-192.png", include_in_schema=False)
        async def serve_icon_192():
            return no_cache_file(web_dist / "icon-192.png", "image/png")

        @app.get("/icon-96.png", include_in_schema=False)
        async def serve_icon_96():
            return no_cache_file(web_dist / "icon-96.png", "image/png")

        @app.get("/")
        @app.get("/mobile")
        async def serve_root():
            return no_cache_file(web_dist / "index.html")
    elif web_dev.exists():
        app.mount("/src", NoCacheStaticFiles(directory=str(web_dev.parent / "src")), name="src")

        @app.get("/")
        @app.get("/mobile")
        async def serve_root():
            return no_cache_file(web_dev)
    else:
        @app.get("/")
        async def serve_root():
            return {"message": "Scan2Target API", "docs": "/docs", "health": "/health"}

    return app


app = create_app()
