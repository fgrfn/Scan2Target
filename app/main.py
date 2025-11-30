"""RaspScan FastAPI application entrypoint."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from pathlib import Path

from app.api import scan, targets, auth, history, devices, maintenance, websocket, stats
from app.core.init_db import init_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print("Starting RaspScan...")
    init_database()
    yield
    # Shutdown
    print("Shutting down RaspScan...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="RaspScan",
        version="0.1.0",
        lifespan=lifespan
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
    
    # Serve thumbnails from temp directory
    thumbnail_dir = Path("/tmp/raspscan/scans")
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
    elif web_dev.exists():
        # Development: serve from web directory
        app.mount("/src", StaticFiles(directory=str(web_dev.parent / "src")), name="src")
        
        @app.get("/")
        async def serve_root():
            return FileResponse(str(web_dev))
    else:
        @app.get("/")
        async def serve_root():
            return {
                "message": "RaspScan API",
                "docs": "/docs",
                "health": "/health",
                "note": "Web UI not found. Run 'cd app/web && npm run build' or 'npm run dev'"
            }

    return app


app = create_app()
