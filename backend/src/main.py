"""Sweedle Backend - FastAPI Application Entry Point."""

import os
import sys

# Add CUDA DLL directory for Windows (required for custom_rasterizer)
# Must be done before importing torch or any CUDA-dependent modules
if sys.platform == "win32":
    cuda_paths = [
        r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.4\bin",
        r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.1\bin",
    ]
    for cuda_path in cuda_paths:
        if os.path.exists(cuda_path):
            os.add_dll_directory(cuda_path)
            break

import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse

from src.config import settings
from src.database import init_db

# Frontend build directory
FRONTEND_DIR = Path(__file__).parent.parent.parent / "frontend" / "dist"

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown events."""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    # Ensure directories exist
    settings.ensure_directories()
    logger.info("Storage directories initialized")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Initialize core components
    from src.core.queue import get_queue
    from src.core.websocket_manager import get_websocket_manager
    from src.core.worker import get_worker

    app.state.job_queue = get_queue()
    app.state.ws_manager = get_websocket_manager()
    app.state.worker = get_worker()

    # Start background worker
    logger.info("Starting background worker...")
    await app.state.worker.start()
    logger.info("Background worker started")

    yield

    # Shutdown
    logger.info("Shutting down...")

    # Stop background worker
    if app.state.worker:
        await app.state.worker.stop()
        logger.info("Background worker stopped")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="Local 3D Asset Generator for Game Development powered by Hunyuan3D-2.1",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local use
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for serving generated assets
app.mount(
    "/storage",
    StaticFiles(directory=str(settings.STORAGE_ROOT)),
    name="storage",
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    queue_status = app.state.job_queue.get_status() if app.state.job_queue else {}

    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "worker_running": app.state.worker.is_running if app.state.worker else False,
        "queue_size": queue_status.get("queue_size", 0),
        "websocket_connections": app.state.ws_manager.connection_count if app.state.ws_manager else 0,
    }


# API info endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": "Local 3D Asset Generator for Game Development",
        "docs": "/docs",
        "health": "/health",
        "websocket": "/ws/progress",
    }


# Import and include routers
from src.generation.router import router as generation_router
from src.websocket.router import router as websocket_router
from src.assets.router import router as assets_router
from src.export.router import router as export_router
from src.rigging.router import router as rigging_router

app.include_router(generation_router, prefix="/api/generation", tags=["Generation"])
app.include_router(websocket_router, prefix="/ws", tags=["WebSocket"])
app.include_router(assets_router, prefix="/api/assets", tags=["Assets"])
app.include_router(export_router, prefix="/api/export", tags=["Export"])
app.include_router(rigging_router, prefix="/api", tags=["Rigging"])


# Serve frontend static files
if FRONTEND_DIR.exists():
    # Serve static assets (js, css, images)
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="frontend-assets")

    # Serve index.html for all non-API routes (SPA routing)
    @app.get("/{full_path:path}", response_class=HTMLResponse, include_in_schema=False)
    async def serve_frontend(request: Request, full_path: str):
        """Serve the frontend SPA for all non-API routes."""
        # Don't serve frontend for API/WebSocket routes
        if full_path.startswith(("api/", "ws/", "storage/", "docs", "redoc", "openapi")):
            return None

        index_file = FRONTEND_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)

        return HTMLResponse(content="<h1>Frontend not built</h1><p>Run: cd frontend && npm run build</p>", status_code=404)
else:
    logger.warning(f"Frontend build not found at {FRONTEND_DIR}. Run 'npm run build' in frontend/")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
