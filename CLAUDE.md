# CLAUDE.md - Sweedle Project Guide

## Project Overview

**Sweedle** is a local 3D asset generator UI for game development, powered by Hunyuan3D-2.1. It transforms 2D images into game-ready 3D models using AI, with features for asset management, LOD generation, and game engine export.

**GitHub**: https://github.com/gnoobs75/Sweedle.git

---

## Development Workflow

Follow this sequence for code changes:

1. **Write Code** - Implement the feature or fix
2. **Test Backend** - Restart backend if Python changes were made
3. **Verify Frontend** - Check UI updates (hot reload)
4. **Test Generation** - Run an actual 3D generation to verify

```powershell
# Start backend (debug mode with verbose logging)
cd C:\Claude\Sweedle
.\start-backend-debug.bat

# Start frontend (in separate terminal)
cd C:\Claude\Sweedle\frontend
npm run dev

# Or start both together
cd C:\Claude\Sweedle
.\start.bat
```

---

## Environment & Dependencies

### Required Software

| Software | Version | Path / Installation |
|----------|---------|---------------------|
| Python | 3.11.9 | `py -3.11` (via py launcher) |
| Node.js | 18+ | System PATH |
| CUDA | 12.1+ | NVIDIA drivers |
| Git | Latest | System PATH |

### Python Virtual Environment

```
C:\Claude\Sweedle\backend\venv\
├── Scripts\
│   ├── python.exe       # Python 3.11.9
│   ├── pip.exe
│   └── activate.bat
└── Lib\site-packages\   # Installed packages
```

### Key Python Packages

| Package | Version | Purpose |
|---------|---------|---------|
| torch | 2.5.1+cu121 | PyTorch with CUDA |
| hy3dgen | latest | Hunyuan3D-2.1 inference |
| fastapi | 0.128+ | Web framework |
| uvicorn | 0.40+ | ASGI server |
| sqlalchemy | 2.0+ | Database ORM |
| rembg | 2.0+ | Background removal |
| trimesh | 4.11+ | Mesh processing |

### Model Cache Locations

| Model | Cache Path | Size |
|-------|------------|------|
| Hunyuan3D-2.1 (Shape) | `~\.cache\huggingface\hub\models--tencent--Hunyuan3D-2.1\` | ~21GB |
| Hunyuan3D-2 (Texture) | `~\.cache\huggingface\hub\models--tencent--Hunyuan3D-2\` | ~18GB |
| rembg U2Net | `~\.u2net\` | ~170MB |

### GPU Performance Settings

The backend includes optimizations for modern NVIDIA GPUs (RTX 30/40 series). These are configured in `backend/.env`:

| Setting | Default | Description |
|---------|---------|-------------|
| `ENABLE_TF32` | `true` | TF32 tensor operations (8x faster matmul on Ampere+) |
| `ENABLE_CUDNN_BENCHMARK` | `true` | cuDNN autotuning for optimal algorithms |
| `INFERENCE_DTYPE` | `bf16` | BFloat16 inference (2x faster, 50% less VRAM) |
| `CUDA_MEMORY_FRACTION` | `0.95` | Max VRAM usage (prevents OOM) |
| `ENABLE_TEXTURE_PIPELINE` | `true` | Load texture generation (~18GB extra VRAM) |

**RTX 40 Series Optimizations Applied:**
- TF32 matrix operations (8x faster than FP32)
- BFloat16 inference (better precision than FP16)
- cuDNN benchmark autotuning
- `torch.inference_mode()` for all generation
- Flash Attention support

---

## Project Structure

```
C:\Claude\Sweedle\
├── backend\                    # Python FastAPI backend
│   ├── src\
│   │   ├── main.py            # Entry point, lifespan, routers
│   │   ├── config.py          # Pydantic settings
│   │   ├── database.py        # SQLite async setup
│   │   ├── core\              # Queue, worker, WebSocket
│   │   ├── inference\         # Hunyuan3D pipeline
│   │   ├── generation\        # Generation API
│   │   ├── assets\            # Asset library API
│   │   ├── export\            # LOD, engine export
│   │   ├── rigging\           # Auto-rigging system
│   │   │   ├── router.py      # Rigging API endpoints
│   │   │   ├── service.py     # RiggingService logic
│   │   │   ├── schemas.py     # Pydantic models
│   │   │   ├── processors\    # UniRig, Blender processors
│   │   │   └── skeleton\      # Skeleton templates
│   │   └── websocket\         # Real-time updates
│   ├── storage\               # File storage
│   ├── data\                  # SQLite database
│   ├── venv\                  # Python virtual environment
│   └── requirements.txt
│
├── frontend\                  # React TypeScript frontend
│   ├── src\
│   │   ├── App.tsx           # Main application
│   │   ├── components\       # UI components
│   │   │   ├── rigging\      # RiggingPanel, CharacterTypeSelector
│   │   │   └── viewer\       # GLBViewer, SkeletonVisualization
│   │   ├── stores\           # Zustand state (incl. riggingStore)
│   │   ├── hooks\            # Custom hooks
│   │   └── services\         # API clients (incl. rigging.ts)
│   ├── node_modules\
│   └── package.json
│
├── .claude\
│   └── skills\               # Claude Code skills
│       ├── rig-asset.md
│       ├── debug-rigging.md
│       └── export-rigged.md
│
├── start.bat                 # Start both services
├── start-backend-debug.bat   # Backend with logging
├── setup.bat                 # Initial setup
├── README.md                 # Project documentation
└── CLAUDE.md                 # This file
```

---

## Critical Files

### Backend Entry Point
`backend/src/main.py` - FastAPI app initialization, lifespan events, router registration

### Inference Pipeline
`backend/src/inference/pipeline.py` - Hunyuan3D wrapper, model loading, generation logic

**Key Notes:**
- The `hy3dgen` library's `.to()` method returns `None` instead of `self` (bug in their code)
- Model loading is done synchronously to avoid thread visibility issues
- Texture generation is disabled (requires custom_rasterizer CUDA compilation)

### Generation Flow
1. Image uploaded via `/api/generation/image-to-3d`
2. Job created in database and added to queue
3. Background worker dequeues and processes
4. Pipeline preprocesses image (rembg background removal)
5. Hunyuan3D generates 3D shape
6. Mesh saved as GLB
7. WebSocket broadcasts completion

### Configuration
`backend/src/config.py` - Pydantic settings, environment variables

### Database
`backend/data/sweedle.db` - SQLite database with assets, jobs, tags

---

## API Endpoints

### Generation
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/generation/image-to-3d` | Submit image |
| GET | `/api/generation/jobs/{id}` | Get job status |
| DELETE | `/api/generation/jobs/{id}` | Cancel job |
| GET | `/api/generation/queue/status` | Queue status |

### Assets
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/assets` | List assets |
| GET | `/api/assets/{id}` | Get asset |
| PATCH | `/api/assets/{id}` | Update asset |
| DELETE | `/api/assets/{id}` | Delete asset |
| GET | `/api/assets/tags` | List tags |

### Rigging
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/rigging/auto-rig` | Submit asset for rigging |
| GET | `/api/rigging/jobs/{id}` | Get rigging job status |
| DELETE | `/api/rigging/jobs/{id}` | Cancel rigging job |
| GET | `/api/rigging/skeleton/{asset_id}` | Get skeleton data |
| POST | `/api/rigging/detect-type` | Detect character type |
| GET | `/api/rigging/templates` | List skeleton templates |
| POST | `/api/rigging/export-fbx` | Export rigged model as FBX |

### WebSocket
| Endpoint | Purpose |
|----------|---------|
| `/ws/progress` | Real-time job progress |

### WebSocket Rigging Messages
| Message Type | Description |
|--------------|-------------|
| `rigging_progress` | Rigging job progress updates |
| `rigging_complete` | Rigging completed notification |
| `rigging_failed` | Rigging failure notification |

---

## Common Tasks

### Restart Backend After Code Changes

```powershell
# Close existing backend window (Ctrl+C)
# Then run:
cd C:\Claude\Sweedle
.\start-backend-debug.bat
```

### Clear Generated Assets

```powershell
# Delete all generated files (keeps database structure)
Remove-Item -Recurse -Force C:\Claude\Sweedle\backend\storage\generated\*
```

### Reset Database

```powershell
# Delete database (will be recreated on startup)
Remove-Item C:\Claude\Sweedle\backend\data\sweedle.db
```

### Install New Python Package

```powershell
cd C:\Claude\Sweedle\backend
venv\Scripts\pip.exe install package-name
# Add to requirements.txt if needed
```

### Install New NPM Package

```powershell
cd C:\Claude\Sweedle\frontend
npm install package-name
```

---

## Debugging

### Check Backend Logs
Run `start-backend-debug.bat` and watch console output.

### Check Frontend Logs
Open browser DevTools (F12) > Console tab.

### Verify CUDA
```powershell
nvidia-smi
python -c "import torch; print(torch.cuda.is_available())"
```

### Check Model Loading
Look for these log messages:
```
Model loaded on CUDA device
Loaded shape pipeline from tencent/Hunyuan3D-2.1
Hunyuan3D pipeline initialized - pipeline is None: False
```

If `pipeline is None: True`, there's a loading issue.

---

## Known Issues & Workarounds

### hy3dgen .to() Returns None
**Issue**: The Hunyuan3D library's `.to()` method doesn't return `self`.
**Workaround**: Don't reassign after `.to()` call. See `pipeline.py:121`.

### Python 3.14 Incompatibility
**Issue**: `onnxruntime` doesn't support Python 3.14.
**Workaround**: Use Python 3.11.x.

### Texture Generation
**Status**: Working (loads from tencent/Hunyuan3D-2, ~18GB)
**Note**: The texture pipeline loads successfully despite custom_rasterizer warnings.

### Thumbnail Generation
**Issue**: Requires `pyglet` which has display dependencies.
**Workaround**: Thumbnails may fail silently. Not critical.

---

## Future Roadmap

### Phase 1: Core Improvements
- [ ] Texture generation (compile custom_rasterizer)
- [ ] Better thumbnail generation
- [ ] Batch processing improvements

### Phase 2: Mesh Enhancement
- [ ] Mesh smoothing/subdivision
- [ ] Vertex optimization
- [ ] UV unwrapping improvements
- [ ] PBR material generation

### Phase 3: Auto-Rigging (COMPLETED)
- [x] Skeleton detection for humanoids and quadrupeds
- [x] Automatic bone placement (65-bone humanoid, 45-bone quadruped)
- [x] Weight painting (proximity-based weights)
- [x] Hybrid processors (UniRig ML + Blender headless)
- [x] Skeleton visualization in 3D viewer
- [x] Multi-format export (GLB + FBX)

### Phase 4: Animation
- [ ] Basic idle animations
- [ ] Walk/run cycles
- [ ] Animation retargeting
- [ ] Mixamo integration

### Phase 5: Multi-Model Pipeline
- [ ] Chain multiple AI models
- [ ] Text-to-image + image-to-3D
- [ ] Style transfer
- [ ] Custom model training

---

## Skills for Claude

Skills are slash commands that provide specialized functionality. They are defined in `.claude/skills/` and can be invoked during conversation.

### GPU & Memory Management

#### /gpu-status
Check GPU health, VRAM usage, temperature, and loaded models.
```
/gpu-status
```
Shows: VRAM allocation, GPU temp/utilization, loaded models, backend status.

#### /clear-vram
Force clear GPU memory when stuck or before heavy operations.
```
/clear-vram [--full]
```
- Default: Empty cache, garbage collect
- `--full`: Unload all models and restart backend

#### /gpu-benchmark
Run a quick benchmark to test generation speed.
```
/gpu-benchmark [--quality standard|high]
```
Generates test model and reports timing, VRAM usage, performance comparison.

---

### Model & Cache Management

#### /model-status
Check status of all AI models (loaded, cached, missing).
```
/model-status
```
Shows: Hunyuan3D-2.1, Hunyuan3D-2 (texture), U2Net cache status and sizes.

#### /clear-cache
Clear model caches to free disk space or force re-download.
```
/clear-cache [huggingface|hy3dgen|rembg|all]
```
Warning: Requires re-downloading models (~40GB) on next use.

---

### Debugging & Logs

#### /watch-logs
Stream backend logs in real-time for debugging.
```
/watch-logs [--filter generation|rigging|vram|error]
```
Reads from `backend/sweedle.log` with optional filtering.

#### /debug-generation
Diagnose why a generation failed.
```
/debug-generation [job_id]
```
Analyzes job status, error messages, VRAM state, suggests fixes.

#### /debug-pipeline
Debug Hunyuan3D pipeline issues - check model loading, CUDA, etc.
```
/debug-pipeline
```

#### /debug-rigging
Debug rigging pipeline issues - check processor availability, recent errors.
```
/debug-rigging
```

---

### Generation Presets

#### /generate-quick
Generate with fast/draft settings for quick iteration (~30-40s).
```
/generate-quick <image_path> [name]
```
Uses: 20 steps, 192 octree, no texture. Good for prototyping.

#### /generate-production
Generate with maximum quality settings (~90-120s).
```
/generate-production <image_path> [name] [--texture] [--high-poly]
```
Uses: 50 steps, 384 octree, optional texture. For final assets.

---

### Batch Operations

#### /batch-generate
Generate multiple 3D models from a folder of images.
```
/batch-generate <folder_path> [--quality standard|high|draft] [--skip-existing] [--texture]
```
Examples:
- `/batch-generate ./sprites --quality standard`
- `/batch-generate ./characters --skip-existing`

#### /batch-export
Export multiple assets to game engine format.
```
/batch-export [--format glb|fbx|obj] [--engine unity|unreal|godot] [--filter <query>]
```
Examples:
- `/batch-export --format fbx --engine unity`
- `/batch-export --filter tag:character`

---

### Rigging

#### /rig-asset
Auto-rig an existing asset with skeleton and weights.
```
/rig-asset [asset_id] [--type humanoid|quadruped|auto] [--processor unirig|blender|auto]
```
Examples:
- `/rig-asset` - Rig current viewer asset
- `/rig-asset abc123 --type humanoid`

#### /export-rigged
Export a rigged model to game engine format.
```
/export-rigged [asset_id] [--format glb|fbx] [--engine unity|unreal|godot]
```
Examples:
- `/export-rigged abc123 --format fbx --engine unity`

---

### Database & Cleanup

#### /cleanup-assets
Remove orphaned files and failed generations.
```
/cleanup-assets [--dry-run] [--include-failed] [--include-orphaned]
```
Options:
- `--dry-run`: Preview without deleting
- `--include-failed`: Remove failed generation attempts
- `--include-orphaned`: Remove files not in database

#### /db-maintenance
Run database maintenance tasks.
```
/db-maintenance [vacuum|check|stats|backup|repair]
```
- `vacuum`: Reclaim disk space
- `check`: Verify integrity
- `stats`: Show counts and sizes
- `backup`: Create backup
- `repair`: Attempt repair

---

### Development

#### /generate-component
Generate a new React component with TypeScript and TailwindCSS.
```
/generate-component ComponentName
```

#### /add-endpoint
Add a new FastAPI endpoint with Pydantic schemas.
```
/add-endpoint /api/feature/action POST
```

#### /add-mesh-processor
Add a new mesh processing feature (smoothing, decimation, etc.)
```
/add-mesh-processor smooth
```

#### /export-format
Add support for a new export format (FBX, OBJ, etc.)
```
/export-format fbx
```

---

## Code Patterns

### Adding a New Backend Endpoint

1. Create/update router in `backend/src/{module}/router.py`
2. Add Pydantic schemas in `schemas.py`
3. Implement business logic in `service.py`
4. Register router in `main.py` if new module

### Adding a New Frontend Component

1. Create component in `frontend/src/components/{category}/`
2. Export from `index.ts` if applicable
3. Add to relevant parent component
4. Create store if state needed

### Adding a New Generation Parameter

1. Add to `GenerationConfig` in `backend/src/inference/config.py`
2. Add to `GenerationParameters` schema in `generation/schemas.py`
3. Handle in `pipeline.py` generation methods
4. Add UI control in frontend `ParameterControls.tsx`
5. Update store in `generationStore.ts`

---

## Testing

### Manual Testing Checklist

- [ ] Backend starts without errors
- [ ] Frontend loads at localhost:5173
- [ ] Backend status shows "Connected"
- [ ] Can upload image
- [ ] Generation starts (progress shows)
- [ ] 3D model appears in viewer
- [ ] Asset appears in library
- [ ] Can delete asset
- [ ] Can search/filter assets

### Rigging Testing Checklist

- [ ] RiggingPanel opens when selecting asset
- [ ] Character type auto-detection works
- [ ] Can start auto-rigging job
- [ ] Progress updates via WebSocket
- [ ] Skeleton appears in viewer after completion
- [ ] Skeleton toggle button works in toolbar
- [ ] Can click bones to select them
- [ ] Export as FBX works (requires Blender)

### Verify Generation Works

1. Start backend and frontend
2. Upload a simple image (solid object, clear background)
3. Click Generate
4. Watch progress bar
5. Confirm 3D model loads in viewer
6. Check logs for "Shape complete"

---

## Contact & Resources

- **GitHub**: https://github.com/gnoobs75/Sweedle
- **Hunyuan3D**: https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **React Three Fiber**: https://docs.pmnd.rs/react-three-fiber
