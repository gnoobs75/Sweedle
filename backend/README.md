# Sweedle Backend

FastAPI-based backend service for Sweedle, providing REST APIs, WebSocket communication, and AI-powered 3D generation through Hunyuan3D-2.1.

---

## Overview

The backend handles:
- **3D Generation Pipeline**: Wraps Hunyuan3D-2.1 for image-to-3D conversion
- **Job Queue**: Async job processing with priority support
- **Asset Management**: CRUD operations on generated assets
- **Real-time Updates**: WebSocket broadcasting for progress tracking
- **File Storage**: Manages uploaded images and generated 3D models

---

## Directory Structure

```
backend/
├── src/
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py               # Pydantic settings (env vars)
│   ├── database.py             # SQLite + async SQLAlchemy setup
│   │
│   ├── core/                   # Core infrastructure
│   │   ├── queue.py            # AsyncIO priority queue
│   │   ├── worker.py           # Background GPU worker
│   │   └── websocket_manager.py # WebSocket connection manager
│   │
│   ├── inference/              # AI model integration
│   │   ├── pipeline.py         # Hunyuan3D wrapper (main inference)
│   │   ├── preprocessor.py     # Image preprocessing (rembg)
│   │   └── config.py           # Generation configuration dataclasses
│   │
│   ├── generation/             # Generation API module
│   │   ├── router.py           # REST endpoints (/api/generation/*)
│   │   ├── service.py          # Business logic
│   │   ├── models.py           # SQLAlchemy ORM models
│   │   └── schemas.py          # Pydantic request/response schemas
│   │
│   ├── assets/                 # Asset library module
│   │   ├── router.py           # CRUD endpoints (/api/assets/*)
│   │   └── schemas.py          # Asset Pydantic schemas
│   │
│   ├── export/                 # Export pipeline module
│   │   ├── router.py           # Export endpoints (/api/export/*)
│   │   ├── lod_generator.py    # Level of Detail generation
│   │   ├── mesh_optimizer.py   # Mesh optimization utilities
│   │   ├── draco_compressor.py # Draco compression
│   │   ├── engine_exporter.py  # Unity/Unreal/Godot export
│   │   ├── thumbnail_generator.py
│   │   └── validator.py        # Mesh validation
│   │
│   └── websocket/              # WebSocket module
│       ├── router.py           # /ws/progress endpoint
│       └── schemas.py          # Message schemas
│
├── storage/                    # File storage (auto-created)
│   ├── uploads/                # Uploaded source images
│   └── generated/              # Generated 3D models
│
├── data/                       # Database files (auto-created)
│   └── sweedle.db              # SQLite database
│
├── requirements.txt            # Python dependencies
├── requirements-minimal.txt    # Minimal deps for Python 3.14
└── convert_model.py            # Model format conversion utility
```

---

## Module Documentation

### Core Module (`src/core/`)

#### `queue.py` - Job Queue
Implements an async priority queue for managing generation jobs.

```python
from src.core.queue import get_queue, JobPriority

queue = get_queue()
await queue.enqueue(
    job_id="...",
    job_type="image_to_3d",
    payload={...},
    priority=JobPriority.HIGH
)
```

**Key Classes:**
- `JobQueue`: AsyncIO-based priority queue
- `Job`: Job data model with status, progress, timestamps
- `JobPriority`: Enum (LOW, NORMAL, HIGH)
- `JobStatus`: Enum (PENDING, PROCESSING, COMPLETED, FAILED, CANCELLED)

#### `worker.py` - Background Worker
Processes jobs from the queue using the inference pipeline.

```python
from src.core.worker import start_worker, stop_worker

worker = await start_worker()  # Starts processing loop
await stop_worker()            # Graceful shutdown
```

**Features:**
- Single-threaded GPU processing (max_workers=1)
- Automatic pipeline initialization
- Progress callbacks via WebSocket
- Error handling and job status updates

#### `websocket_manager.py` - WebSocket Manager
Manages WebSocket connections and broadcasts.

```python
from src.core.websocket_manager import get_websocket_manager

ws_manager = get_websocket_manager()
await ws_manager.send_progress(job_id, progress=0.5, stage="Generating...")
await ws_manager.send_asset_ready(asset_id, name="Model", ...)
```

**Message Types:**
- `progress`: Job progress updates
- `job_created`: New job notification
- `asset_ready`: Generation complete notification
- `queue_status`: Queue state updates

---

### Inference Module (`src/inference/`)

#### `pipeline.py` - Hunyuan3D Pipeline
Wraps the Hunyuan3D-2.1 model for 3D generation.

```python
from src.inference.pipeline import get_pipeline, initialize_pipeline

pipeline = get_pipeline()  # Singleton
await pipeline.initialize()
result = await pipeline.generate(
    image=image_path,
    config=config,
    output_dir=output_dir,
    asset_id=asset_id,
    progress_callback=callback
)
```

**Key Methods:**
- `initialize()`: Loads model into GPU memory
- `generate()`: Main generation entry point
- `cleanup()`: Releases GPU memory

**Generation Flow:**
1. Preprocess image (resize, remove background)
2. Generate 3D shape via DiT model
3. (Optional) Generate texture
4. Post-process and save mesh

#### `preprocessor.py` - Image Preprocessor
Handles image preparation before generation.

```python
from src.inference.preprocessor import ImagePreprocessor

preprocessor = ImagePreprocessor()
image = await preprocessor.prepare_image(
    image_path,
    target_size=512,
    remove_bg=True,
    center_crop=True
)
```

**Features:**
- Background removal using rembg (U2Net model)
- Center cropping to square
- Resize to target dimensions
- Alpha channel handling

#### `config.py` - Generation Config
Dataclasses for generation parameters.

```python
from src.inference.config import GenerationConfig, TextureConfig

config = GenerationConfig(
    inference_steps=30,
    guidance_scale=5.5,
    octree_resolution=256,
    seed=42,
    texture=TextureConfig(enabled=True),
    output_format=OutputFormat.GLB
)
```

---

### Generation Module (`src/generation/`)

#### `router.py` - Generation Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/generation/image-to-3d` | POST | Submit image for generation |
| `/api/generation/text-to-3d` | POST | Submit text prompt (planned) |
| `/api/generation/jobs/{id}` | GET | Get job status |
| `/api/generation/jobs/{id}` | DELETE | Cancel job |
| `/api/generation/queue/status` | GET | Get queue status |
| `/api/generation/queue/jobs` | GET | List queue jobs |

#### `models.py` - ORM Models

**Asset Model:**
```python
class Asset(Base):
    id: str                    # UUID
    name: str
    source_type: GenerationType
    source_image_path: str
    file_path: str            # Path to .glb file
    thumbnail_path: str
    vertex_count: int
    face_count: int
    status: AssetStatus
    generation_time_seconds: float
    # ... tags, metadata, timestamps
```

**GenerationJob Model:**
```python
class GenerationJob(Base):
    id: str
    asset_id: str
    job_type: str
    status: JobStatus
    payload: dict             # JSON
    progress: float
    stage: str
    error_message: str
    # ... timestamps
```

---

### Assets Module (`src/assets/`)

#### `router.py` - Asset Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/assets` | GET | List assets (paginated) |
| `/api/assets/{id}` | GET | Get asset details |
| `/api/assets/{id}` | PATCH | Update asset metadata |
| `/api/assets/{id}` | DELETE | Delete asset |
| `/api/assets/tags` | GET | List all tags |
| `/api/assets/tags` | POST | Create tag |

**Query Parameters (GET /api/assets):**
- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 20)
- `search`: Text search in name
- `source_type`: Filter by generation type
- `status`: Filter by status
- `tags`: Filter by tag names
- `sort_by`: created, name, vertex_count
- `sort_order`: asc, desc

---

### Export Module (`src/export/`)

#### `lod_generator.py` - LOD Generation
Creates Level of Detail variants.

```python
from src.export.lod_generator import LODGenerator

generator = LODGenerator()
lod_paths = await generator.generate_lods(
    mesh_path="model.glb",
    output_dir="output/",
    levels=[1.0, 0.5, 0.25, 0.1]
)
```

#### `engine_exporter.py` - Game Engine Export
Exports assets to game engine project folders.

```python
from src.export.engine_exporter import EngineExporter

exporter = EngineExporter()
await exporter.export_to_unity(asset_path, project_path, asset_name)
await exporter.export_to_unreal(asset_path, project_path, asset_name)
await exporter.export_to_godot(asset_path, project_path, asset_name)
```

---

## Third-Party Dependencies

### AI/ML Libraries

| Package | Version | Purpose |
|---------|---------|---------|
| `torch` | 2.5.1+cu121 | PyTorch with CUDA 12.1 |
| `torchvision` | 0.20.1+cu121 | Image transforms |
| `hy3dgen` | latest | Hunyuan3D-2.1 inference |
| `diffusers` | 0.36+ | Diffusion model utilities |
| `transformers` | 4.57+ | Hugging Face models |
| `accelerate` | 1.12+ | Training acceleration |
| `safetensors` | 0.7+ | Model serialization |

### Image Processing

| Package | Version | Purpose |
|---------|---------|---------|
| `pillow` | 12.1+ | Image manipulation |
| `rembg` | 2.0+ | Background removal |
| `onnxruntime` | 1.23+ | ONNX inference (for rembg) |

### Mesh Processing

| Package | Version | Purpose |
|---------|---------|---------|
| `trimesh` | 4.11+ | Mesh loading/manipulation |
| `pygltflib` | 1.16+ | GLB/GLTF handling |
| `numpy` | 2.2+ | Numerical operations |

### Web Framework

| Package | Version | Purpose |
|---------|---------|---------|
| `fastapi` | 0.128+ | Web framework |
| `uvicorn` | 0.40+ | ASGI server |
| `websockets` | 15.0+ | WebSocket support |
| `python-multipart` | 0.0.21+ | File uploads |

### Database

| Package | Version | Purpose |
|---------|---------|---------|
| `sqlalchemy` | 2.0+ | ORM |
| `aiosqlite` | 0.22+ | Async SQLite |
| `alembic` | 1.17+ | Migrations |

### Configuration

| Package | Version | Purpose |
|---------|---------|---------|
| `pydantic` | 2.12+ | Data validation |
| `pydantic-settings` | 2.12+ | Settings management |
| `python-dotenv` | 1.2+ | .env file loading |

---

## Running the Backend

### Development Mode

```bash
# Activate virtual environment
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Run with auto-reload
uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
```

### Production Mode

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 1
```

> Note: Only use 1 worker as the GPU cannot be shared between processes.

### Debug Mode (Windows)

```bash
..\start-backend-debug.bat
```

This shows all console output for debugging.

---

## API Documentation

Once running, access:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

---

## Database Schema

The SQLite database is auto-created at `data/sweedle.db`.

### Tables

- `assets`: Generated 3D assets
- `generation_jobs`: Job history
- `tags`: Asset tags
- `asset_tags`: Many-to-many relationship

### Migrations

Currently using auto-create. For manual migrations:
```bash
alembic init alembic
alembic revision --autogenerate -m "Initial"
alembic upgrade head
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | Sweedle | Application name |
| `APP_VERSION` | 1.0.0 | Version string |
| `DEBUG` | false | Enable debug logging |
| `HOST` | 0.0.0.0 | Server host |
| `PORT` | 8000 | Server port |
| `DATABASE_URL` | sqlite+aiosqlite:///./data/sweedle.db | Database URL |
| `HUNYUAN_MODEL_PATH` | tencent/Hunyuan3D-2.1 | Model identifier |
| `HUNYUAN_SUBFOLDER` | hunyuan3d-dit-v2-1 | Model subfolder |
| `DEVICE` | cuda | Compute device |
| `LOW_VRAM_MODE` | false | Enable memory optimizations |
| `DEFAULT_INFERENCE_STEPS` | 30 | Default inference steps |
| `DEFAULT_GUIDANCE_SCALE` | 5.5 | Default guidance scale |
| `DEFAULT_OCTREE_RESOLUTION` | 256 | Default octree resolution |

---

## Troubleshooting

### CUDA Issues

```bash
# Verify CUDA is available
python -c "import torch; print(torch.cuda.is_available())"

# Check CUDA version
nvidia-smi
```

### Model Loading Issues

```bash
# Clear Hugging Face cache and re-download
rm -rf ~/.cache/huggingface/hub/models--tencent--Hunyuan3D-2.1
```

### Memory Issues

Enable low VRAM mode in `.env`:
```
LOW_VRAM_MODE=true
```

Or reduce resolution:
```
DEFAULT_OCTREE_RESOLUTION=128
```
