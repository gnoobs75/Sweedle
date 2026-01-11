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

from src.config import settings, apply_gpu_optimizations
from src.database import init_db

# Frontend build directory
FRONTEND_DIR = Path(__file__).parent.parent.parent / "frontend" / "dist"

# Configure logging with file output for monitoring
LOG_FILE = Path(__file__).parent.parent / "sweedle.log"
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler(LOG_FILE, mode='w', encoding='utf-8'),  # File output (overwrite each run)
    ],
)
logger = logging.getLogger(__name__)
logger.info(f"Logging to file: {LOG_FILE}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown events."""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    # Apply GPU optimizations BEFORE loading any models
    logger.info("Applying GPU optimizations...")
    gpu_opts = apply_gpu_optimizations()
    if gpu_opts.get("gpu"):
        logger.info(f"GPU optimizations applied: TF32={gpu_opts.get('tf32')}, "
                   f"dtype={gpu_opts.get('dtype')}, cuDNN={gpu_opts.get('cudnn_benchmark')}")
    app.state.gpu_optimizations = gpu_opts

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
    from src.core.device import get_device_info

    queue_status = app.state.job_queue.get_status() if app.state.job_queue else {}
    device_info = get_device_info()

    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "worker_running": app.state.worker.is_running if app.state.worker else False,
        "queue_size": queue_status.get("queue_size", 0),
        "websocket_connections": app.state.ws_manager.connection_count if app.state.ws_manager else 0,
        "device": device_info,
    }


# Readiness endpoint - tells frontend when backend is fully ready
@app.get("/api/ready")
async def readiness_check():
    """Check if backend is fully initialized and ready for requests.

    Frontend should poll this until ready=true before showing the main UI.
    """
    from src.core.device import get_device_info
    from src.inference.pipeline import get_pipeline

    # Check core components
    worker_ready = app.state.worker is not None and app.state.worker.is_running
    queue_ready = app.state.job_queue is not None
    ws_ready = app.state.ws_manager is not None

    # Check pipeline is initialized (not necessarily loaded to GPU yet)
    pipeline = get_pipeline()
    pipeline_initialized = pipeline is not None

    # Check GPU availability
    device_info = get_device_info()
    gpu_available = device_info.get("cuda_available", False)

    # All systems go?
    ready = all([worker_ready, queue_ready, ws_ready, pipeline_initialized])

    # Get loading status message
    if not queue_ready:
        status_message = "Initializing job queue..."
    elif not ws_ready:
        status_message = "Initializing WebSocket..."
    elif not pipeline_initialized:
        status_message = "Loading AI models..."
    elif not worker_ready:
        status_message = "Starting background worker..."
    else:
        status_message = "Ready"

    return {
        "ready": ready,
        "status_message": status_message,
        "components": {
            "worker": worker_ready,
            "queue": queue_ready,
            "websocket": ws_ready,
            "pipeline": pipeline_initialized,
            "gpu": gpu_available,
        },
        "gpu": {
            "available": gpu_available,
            "name": device_info.get("gpu_name", "Unknown"),
            "vram_gb": device_info.get("gpu_memory_gb", 0),
        } if gpu_available else None,
    }


# Device info endpoint
@app.get("/api/device/info")
async def device_info():
    """Get detailed device information."""
    from src.core.device import get_device_info, DeviceManager

    info = get_device_info()
    manager = DeviceManager()

    return {
        **info,
        "configured_device": settings.DEVICE,
        "effective_device": settings.compute_device,
        "preprocessing_overlap_enabled": settings.ENABLE_PREPROCESSING_OVERLAP,
        "model_warmup_enabled": settings.ENABLE_MODEL_WARMUP,
    }


# Live GPU stats endpoint (for polling)
@app.get("/api/device/stats")
async def device_stats():
    """Get live GPU/system stats for monitoring."""
    import psutil
    import time

    stats = {
        "timestamp": time.time(),
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "ram_used_gb": round(psutil.virtual_memory().used / 1e9, 2),
        "ram_total_gb": round(psutil.virtual_memory().total / 1e9, 2),
        "ram_percent": psutil.virtual_memory().percent,
    }

    # GPU stats
    try:
        import torch
        if torch.cuda.is_available():
            stats["gpu"] = {
                "name": torch.cuda.get_device_name(0),
                "vram_used_gb": round(torch.cuda.memory_allocated(0) / 1e9, 2),
                "vram_reserved_gb": round(torch.cuda.memory_reserved(0) / 1e9, 2),
                "vram_total_gb": round(torch.cuda.get_device_properties(0).total_memory / 1e9, 2),
                "vram_percent": round(torch.cuda.memory_allocated(0) / torch.cuda.get_device_properties(0).total_memory * 100, 1),
            }
            # Try to get GPU utilization via nvidia-smi
            try:
                import subprocess
                result = subprocess.run(
                    ['nvidia-smi', '--query-gpu=utilization.gpu,temperature.gpu', '--format=csv,noheader,nounits'],
                    capture_output=True, text=True, timeout=1
                )
                if result.returncode == 0:
                    parts = result.stdout.strip().split(', ')
                    stats["gpu"]["utilization_percent"] = int(parts[0])
                    stats["gpu"]["temperature_c"] = int(parts[1])
            except Exception:
                pass
        else:
            stats["gpu"] = None
    except ImportError:
        stats["gpu"] = None

    # Worker status
    if app.state.worker:
        stats["worker"] = {
            "running": app.state.worker.is_running,
            "current_job": app.state.worker.current_job_id,
        }

    # Queue status
    if app.state.job_queue:
        queue_status = app.state.job_queue.get_status()
        stats["queue"] = {
            "size": queue_status.get("queue_size", 0),
            "processing": queue_status.get("current_job") is not None,
        }

    return stats


# VRAM diagnostic endpoint
@app.get("/api/device/vram-diagnostic")
async def vram_diagnostic():
    """Run full VRAM diagnostic to identify memory usage and leaks."""
    from src.utils.vram_diagnostic import full_diagnostic
    return full_diagnostic()


# Clear VRAM endpoint
@app.post("/api/device/clear-vram")
async def clear_vram():
    """Attempt to clear VRAM by forcing garbage collection and cache clearing."""
    from src.utils.vram_diagnostic import clear_all_vram, get_vram_info

    before = get_vram_info()
    result = clear_all_vram()
    after = get_vram_info()

    return {
        "success": result.get("success", False),
        "before_gb": before.get("allocated_gb", 0),
        "after_gb": after.get("allocated_gb", 0),
        "freed_gb": result.get("freed_gb", 0),
        "message": f"Freed {result.get('freed_gb', 0):.2f} GB" if result.get("success") else result.get("error", "Unknown error"),
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
from src.pipeline.router import router as pipeline_router
from src.workflow.router import router as workflow_router

app.include_router(generation_router, prefix="/api/generation", tags=["Generation"])
app.include_router(websocket_router, prefix="/ws", tags=["WebSocket"])
app.include_router(assets_router, prefix="/api/assets", tags=["Assets"])
app.include_router(export_router, prefix="/api/export", tags=["Export"])
app.include_router(rigging_router, prefix="/api", tags=["Rigging"])
app.include_router(pipeline_router, tags=["Pipeline"])
app.include_router(workflow_router, tags=["Workflow"])


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
