"""Scan2Target FastAPI application."""
from __future__ import annotations

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import auth, devices, scan, targets, history, stats, app_settings, maintenance, homeassistant, websocket
from app.config import get_settings


def get_version() -> str:
    try:
        return (Path(__file__).parent.parent / "VERSION").read_text().strip()
    except Exception:
        return "2.0.0"


def _get_setting(key, default):
    """Read a setting from DB, falling back to default if table doesn't exist yet."""
    try:
        from app.app_settings.service import get_setting
        return get_setting(key, default)
    except Exception:
        return default


def _setup_logging() -> None:
    level_name = _get_setting("log_level", get_settings().log_level)
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )
    # File handler
    log_dir = Path(get_settings().log_dir)
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        from logging.handlers import RotatingFileHandler
        fh = RotatingFileHandler(log_dir / "app.log", maxBytes=10_000_000, backupCount=5)
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s %(name)s — %(message)s"))
        logging.getLogger().addHandler(fh)
    except OSError:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────
    logger = logging.getLogger(__name__)
    settings = get_settings()

    # Run DB migrations
    from app.database import run_migrations
    await asyncio.to_thread(run_migrations, settings.database_path)
    logger.info("Database migrations applied")

    # Seed default admin
    from app.auth.service import init_admin
    await asyncio.to_thread(init_admin)

    # Start job worker
    from app.jobs.worker import get_worker
    await get_worker().start()
    logger.info("Job worker started")

    # Start health monitor
    from app.scanning.health import get_health_monitor
    from app.app_settings.service import get_setting as _gs
    interval = _gs("health_check_interval", settings.health_check_interval)
    monitor = get_health_monitor(check_interval=interval)
    await monitor.start()
    logger.info("Health monitor started (interval=%ds)", interval)

    # Background scanner discovery
    from app.scanning.discovery import discover_all
    async def _discover():
        try:
            devices = await asyncio.to_thread(discover_all)
            logger.info("Initial discovery: %d scanner(s) found", len(devices))
        except Exception as exc:
            logger.warning("Initial discovery failed: %s", exc)
    asyncio.create_task(_discover())

    logger.info("=" * 50)
    logger.info("Scan2Target v%s ready", get_version())
    logger.info("=" * 50)

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────
    await get_worker().stop()
    await monitor.stop()
    logger.info("Scan2Target stopped")


def create_app() -> FastAPI:
    _setup_logging()
    settings = get_settings()

    cors = _get_setting("cors_origins", settings.cors_origins)

    app = FastAPI(title="Scan2Target", version=get_version(),
                  lifespan=lifespan)

    app.add_middleware(CORSMiddleware, allow_origins=cors,
                       allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

    PREFIX = "/api/v1"
    app.include_router(auth.router,         prefix=f"{PREFIX}/auth",          tags=["auth"])
    app.include_router(devices.router,      prefix=f"{PREFIX}/devices",       tags=["devices"])
    app.include_router(scan.router,         prefix=f"{PREFIX}/scan",          tags=["scan"])
    app.include_router(targets.router,      prefix=f"{PREFIX}/targets",       tags=["targets"])
    app.include_router(history.router,      prefix=f"{PREFIX}/history",       tags=["history"])
    app.include_router(stats.router,        prefix=f"{PREFIX}/stats",         tags=["stats"])
    app.include_router(app_settings.router, prefix=f"{PREFIX}/settings",      tags=["settings"])
    app.include_router(maintenance.router,  prefix=f"{PREFIX}/maintenance",   tags=["maintenance"])
    app.include_router(homeassistant.router,prefix=f"{PREFIX}/homeassistant", tags=["homeassistant"])
    app.include_router(websocket.router,    prefix=f"{PREFIX}",               tags=["ws"])

    @app.get("/health")
    def health():
        return {"status": "ok", "version": get_version()}

    @app.get("/api/v1/version")
    def version():
        return {"version": get_version()}

    # Serve SvelteKit static output
    # Native install: <repo>/backend/app/main.py → 3 levels up → <repo>/frontend/build
    # Docker:         /app/app/main.py → 2 levels up → /app/frontend/build
    static_dir = Path(__file__).parent.parent.parent / "frontend" / "build"
    if not static_dir.exists():
        static_dir = Path(__file__).parent.parent / "frontend" / "build"
    if static_dir.exists():
        # SPA fallback: serve index.html for all non-API routes
        index_html = static_dir / "index.html"

        @app.get("/{path:path}", include_in_schema=False)
        def spa_fallback(path: str):
            if index_html.exists():
                return FileResponse(str(index_html))
            raise HTTPException(status_code=404)

        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="frontend")

    return app


app = create_app()
