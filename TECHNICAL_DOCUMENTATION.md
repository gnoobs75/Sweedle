# Sweedle - Technical Documentation

## Full Stack Architecture Reference

**Version**: 1.1.0
**Last Updated**: January 9, 2026
**GitHub**: https://github.com/gnoobs75/Sweedle.git

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Backend Architecture](#2-backend-architecture)
3. [Frontend Architecture](#3-frontend-architecture)
4. [Data Flow & Integration](#4-data-flow--integration)
5. [API Reference](#5-api-reference)
6. [WebSocket Protocol](#6-websocket-protocol)
7. [Database Schema](#7-database-schema)
8. [Configuration](#8-configuration)
9. [Rigging System](#9-rigging-system)
10. [Key Files Reference](#10-key-files-reference)

---

## 1. System Overview

### 1.1 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (React + TypeScript)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Generation   │  │   Viewer     │  │   Library    │  │   Rigging    │     │
│  │   Panel      │  │   Panel      │  │    Panel     │  │    Panel     │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                 │                 │                 │             │
│  ┌──────┴─────────────────┴─────────────────┴─────────────────┴───────┐     │
│  │                    Zustand State Management                         │     │
│  │  generationStore │ viewerStore │ libraryStore │ riggingStore       │     │
│  └──────┬─────────────────────────────────────────────────────────────┘     │
│         │                                                                    │
│  ┌──────┴─────────────────────────────────────────────────────────────┐     │
│  │                      API Client / WebSocket Client                   │     │
│  └──────┬───────────────────────────────────┬─────────────────────────┘     │
└─────────┼───────────────────────────────────┼───────────────────────────────┘
          │ HTTP (REST API)                   │ WebSocket
          ▼                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BACKEND (FastAPI + Python)                           │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                          FastAPI Application                          │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────────┐  │   │
│  │  │ Generation │  │   Assets   │  │  Rigging   │  │   WebSocket    │  │   │
│  │  │   Router   │  │   Router   │  │   Router   │  │    Router      │  │   │
│  │  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └───────┬────────┘  │   │
│  └────────┼───────────────┼───────────────┼─────────────────┼───────────┘   │
│           │               │               │                 │               │
│  ┌────────┴───────────────┴───────────────┴─────────────────┴───────────┐   │
│  │                        Service Layer                                  │   │
│  │  GenerationService │ AssetService │ RiggingService │ WebSocketManager│   │
│  └────────┬─────────────────────────────────────────────────────────────┘   │
│           │                                                                  │
│  ┌────────┼─────────────────────────────────────────────────────────────┐   │
│  │ ┌──────┴──────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │   │
│  │ │  JobQueue   │──│   Worker     │──│   Pipeline   │  │  Rigging   │  │   │
│  │ │ (asyncio)   │  │ (Background) │  │ (Hunyuan3D)  │  │ Processors │  │   │
│  │ └─────────────┘  └──────────────┘  └──────────────┘  └────────────┘  │   │
│  │                                           │               │           │   │
│  │                                    ┌──────┴──────┐  ┌─────┴──────┐    │   │
│  │                                    │    CUDA     │  │  Blender   │    │   │
│  │                                    │    GPU      │  │ (headless) │    │   │
│  │                                    └─────────────┘  └────────────┘    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│           │                                                                  │
│  ┌────────┴─────────────────────────────────────────────────────────────┐   │
│  │                        Data Layer                                     │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                │   │
│  │  │   SQLite     │  │  File System │  │ Model Cache  │                │   │
│  │  │  (Assets,    │  │  (Uploads,   │  │ (HuggingFace │                │   │
│  │  │  Jobs, Rigs) │  │  Generated)  │  │  Models)     │                │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘                │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Technology Stack

| Layer | Technology | Version |
|-------|------------|---------|
| Frontend | React + TypeScript | 18.x |
| State Management | Zustand | 4.x |
| 3D Rendering | Three.js / React Three Fiber | Latest |
| Styling | TailwindCSS | 3.x |
| Build Tool | Vite | 5.x |
| Desktop Wrapper | Tauri | 2.x |
| Backend | FastAPI | 0.128+ |
| ASGI Server | Uvicorn | 0.40+ |
| Database ORM | SQLAlchemy (async) | 2.0+ |
| Database | SQLite + aiosqlite | - |
| AI Model | Hunyuan3D-2.1 | Latest |
| ML Framework | PyTorch + CUDA | 2.5.1+cu121 |
| Image Processing | rembg, Pillow | - |
| Mesh Processing | trimesh | 4.11+ |

---

## 2. Backend Architecture

### 2.1 Application Entry Point

**File**: `backend/src/main.py`

The FastAPI application uses an async lifespan context manager for startup/shutdown:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()           # Initialize SQLite database
    queue = get_queue()       # Create job queue
    worker = get_worker()     # Get background worker
    await worker.start()      # Start processing loop

    yield  # Application running

    # Shutdown
    await worker.stop()       # Graceful shutdown
```

**Router Registration**:
- `/api/generation` - 3D generation endpoints
- `/api/assets` - Asset library management
- `/api/export` - Export and processing
- `/ws` - WebSocket endpoints

**Static File Serving**:
- `/storage` - Generated assets directory
- `/assets` - Frontend static assets
- Catch-all SPA routing for frontend

### 2.2 Configuration System

**File**: `backend/src/config.py`

Pydantic Settings with environment variable support:

```python
class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Sweedle"
    APP_VERSION: str = "1.0.0"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/sweedle.db"

    # Storage Paths
    STORAGE_ROOT: Path = Path("./storage")
    UPLOAD_DIR: Path = Path("./storage/uploads")
    GENERATED_DIR: Path = Path("./storage/generated")
    EXPORT_DIR: Path = Path("./storage/exports")

    # Hunyuan3D Settings
    HUNYUAN_MODEL_PATH: str = "tencent/Hunyuan3D-2.1"
    HUNYUAN_SUBFOLDER: str = "hunyuan3d-dit-v2-1"
    DEVICE: str = "cuda"
    LOW_VRAM_MODE: bool = False

    # Generation Defaults
    DEFAULT_INFERENCE_STEPS: int = 30
    DEFAULT_GUIDANCE_SCALE: float = 5.5
    DEFAULT_OCTREE_RESOLUTION: int = 256

    # Queue
    MAX_QUEUE_SIZE: int = 100
    JOB_TIMEOUT_SECONDS: int = 600

    # LOD
    LOD_LEVELS: list = [1.0, 0.5, 0.25, 0.1]

    # Engine Paths (optional)
    UNITY_PROJECT_PATH: Optional[str] = None
    UNREAL_PROJECT_PATH: Optional[str] = None
    GODOT_PROJECT_PATH: Optional[str] = None
```

### 2.3 Job Queue System

**File**: `backend/src/core/queue.py`

Priority-based async job queue:

```python
@dataclass
class Job:
    id: str
    job_type: str           # "image_to_3d", "text_to_3d"
    payload: dict
    priority: JobPriority   # HIGH(0), NORMAL(1), LOW(2)
    status: JobStatus       # PENDING, PROCESSING, COMPLETED, FAILED, CANCELLED
    progress: float         # 0.0-1.0
    stage: str              # Current processing stage
    error: Optional[str]
    result: Optional[Any]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

class JobQueue:
    def __init__(self, max_size: int = 100):
        self._queue = asyncio.PriorityQueue(maxsize=max_size)
        self._jobs: Dict[str, Job] = {}
        self._lock = asyncio.Lock()

    async def enqueue(self, job_id, job_type, payload, priority) -> Job
    async def dequeue() -> Job
    async def complete(job_id, result, error) -> None
    async def update_progress(job_id, progress, stage) -> None
    async def cancel(job_id) -> bool
    async def get_status() -> dict
```

**Key Features**:
- Priority queue using `asyncio.PriorityQueue`
- Thread-safe operations with `asyncio.Lock`
- Statistics tracking (completed, failed counts)
- Recent job history

### 2.4 Background Worker

**File**: `backend/src/core/worker.py`

Single-threaded job processor:

```python
class BackgroundWorker:
    def __init__(self):
        self._running = False
        self._current_job_id: Optional[str] = None
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Initialize pipeline and start processing loop"""
        pipeline = get_pipeline()
        await asyncio.to_thread(pipeline.initialize)
        self._task = asyncio.create_task(self._process_loop())

    async def _process_loop(self):
        """Main loop: dequeue → process → repeat"""
        while self._running:
            job = await queue.dequeue()
            await self._process_job(job)

    async def _process_image_to_3d(self, job: Job):
        """Process image-to-3D generation with progress callbacks"""
        # Calls pipeline.generate() in ThreadPoolExecutor
        # Broadcasts progress via WebSocket
```

**Processing Flow**:
1. Dequeue job from priority queue
2. Mark as PROCESSING
3. Send initial WebSocket progress
4. Execute pipeline in thread pool
5. Broadcast completion/failure

### 2.5 Hunyuan3D Inference Pipeline

**File**: `backend/src/inference/pipeline.py`

**GenerationConfig**:
```python
@dataclass
class GenerationConfig:
    # Shape generation
    inference_steps: int = 30        # 5-100
    guidance_scale: float = 5.5      # 1.0-15.0
    octree_resolution: int = 256     # 128, 256, 384, 512
    seed: Optional[int] = None

    # Texture generation
    texture: TextureConfig = field(default_factory=TextureConfig)

    # Post-processing
    face_count: Optional[int] = None
    remove_floaters: bool = True

    # Output
    output_format: str = "glb"       # glb, obj, ply, stl
    mode: str = "standard"           # fast, standard, quality
```

**Hunyuan3DPipeline Class**:

```python
class Hunyuan3DPipeline:
    def initialize(self):
        """Load models to GPU (synchronous)"""
        self.shape_pipeline = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(
            "tencent/Hunyuan3D-2.1",
            subfolder="hunyuan3d-dit-v2-1"
        )
        self.shape_pipeline.to("cuda")  # Note: returns None (library bug)

    def generate(self, image, config, output_dir, asset_id, progress_callback):
        """Full generation pipeline"""
        # Step 1: Preprocess image (5-15%)
        processed = self.preprocessor.prepare_image(image)

        # Step 2: Generate shape (15-70%)
        mesh = self.shape_pipeline(
            image=processed,
            num_inference_steps=config.inference_steps,
            guidance_scale=config.guidance_scale,
            octree_resolution=config.octree_resolution
        )

        # Step 3: Generate texture (70-90%) - if enabled
        if config.texture.enabled:
            mesh = self.paint_pipeline(mesh, processed)

        # Step 4: Post-process & save (90-100%)
        mesh.export(output_path)
        return GenerationResult(...)
```

**GenerationResult**:
```python
@dataclass
class GenerationResult:
    success: bool
    mesh_path: Optional[Path]
    thumbnail_path: Optional[Path]
    vertex_count: int
    face_count: int
    generation_time: float
    parameters: Optional[dict]
    error: Optional[str]
```

### 2.6 Image Preprocessor

**File**: `backend/src/inference/preprocessor.py`

```python
class ImagePreprocessor:
    async def remove_background(self, image_path, **kwargs) -> PIL.Image:
        """Remove background using rembg (u2net model)"""
        return await asyncio.to_thread(rembg.remove, image)

    async def prepare_image(self, image_path, target_size=512) -> PIL.Image:
        """Full preprocessing pipeline"""
        image = await self.remove_background(image_path)
        image = self._center_crop(image)
        image = image.resize((target_size, target_size))
        return image.convert("RGBA")
```

### 2.7 WebSocket Manager

**File**: `backend/src/core/websocket_manager.py`

```python
class WebSocketManager:
    def __init__(self):
        self._connections: Set[WebSocket] = set()
        self._subscriptions: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket)
    async def disconnect(self, websocket: WebSocket)
    async def subscribe(self, websocket: WebSocket, job_id: str)
    async def unsubscribe(self, websocket: WebSocket, job_id: str)

    async def broadcast(self, message: dict)
    async def send_to_job(self, job_id: str, message: dict)

    # Specialized message methods
    async def send_progress(self, job_id, progress, stage, status, result, error)
    async def send_queue_status(self, status)
    async def send_job_created(self, job_id, asset_id, job_type, position)
    async def send_asset_ready(self, asset_id, name, thumbnail_url, download_url)
    async def send_error(self, code, message, job_id, details)
```

---

## 3. Frontend Architecture

### 3.1 Application Structure

**File**: `frontend/src/App.tsx`

```typescript
function App() {
  const { isConnected } = useWebSocket()  // Initialize WebSocket

  return (
    <AppShell>
      <GenerationPanel />    {/* Left: Image upload, parameters */}
      <ViewerPanel />        {/* Center: 3D model viewer */}
      <LibraryPanel />       {/* Right: Asset gallery */}
      <ToastContainer />     {/* Notifications */}
      <DebugPanel />         {/* Development logs */}
    </AppShell>
  )
}
```

### 3.2 State Management (Zustand)

**Location**: `frontend/src/stores/`

#### generationStore.ts
```typescript
interface GenerationState {
  sourceImage: File | null
  sourceImagePreview: string | null
  prompt: string
  assetName: string

  parameters: {
    inferenceSteps: number      // 5-100
    guidanceScale: number       // 1.0-15.0
    octreeResolution: number    // 128, 256, 384, 512
    seed?: number
    generateTexture: boolean
    faceCount?: number
    outputFormat: 'glb' | 'obj' | 'ply' | 'stl'
    mode: 'fast' | 'standard' | 'quality'
  }

  isGenerating: boolean
  currentJobId: string | null

  // Actions
  setSourceImage: (file: File | null) => void
  setParameter: <K>(key: K, value: any) => void
  applyPreset: (preset: 'fast' | 'balanced' | 'quality') => void
  reset: () => void
}

// Presets
const PRESETS = {
  fast: { inferenceSteps: 15, guidanceScale: 4.0, octreeResolution: 128 },
  balanced: { inferenceSteps: 30, guidanceScale: 5.5, octreeResolution: 256 },
  quality: { inferenceSteps: 50, guidanceScale: 7.0, octreeResolution: 512 }
}
```

#### libraryStore.ts
```typescript
interface LibraryState {
  assets: Asset[]
  selectedAssetIds: Set<string>
  currentAssetId: string | null
  tags: Tag[]

  filters: {
    search: string
    tags: number[]
    sourceType: 'all' | 'image_to_3d' | 'text_to_3d'
    hasLod: boolean | null
    isFavorite: boolean | null
    sortBy: 'created' | 'name' | 'size' | 'rating'
    sortOrder: 'asc' | 'desc'
  }

  page: number
  pageSize: number
  totalAssets: number
  viewMode: 'grid' | 'list'
  isLoading: boolean
}
```

#### queueStore.ts
```typescript
interface QueueState {
  jobs: GenerationJob[]
  status: {
    queueSize: number
    currentJobId?: string
    pendingCount: number
    processingCount: number
    completedCount: number
    failedCount: number
  }

  addJob: (job: GenerationJob) => void
  updateJobProgress: (jobId: string, progress: number, stage: string) => void
  updateJobStatus: (jobId: string, status: JobStatus) => void
}
```

#### viewerStore.ts
```typescript
interface ViewerState {
  selectedAssetId: string | null
  modelUrl: string | null
  isLoading: boolean

  settings: {
    showWireframe: boolean
    showGrid: boolean
    showAxes: boolean
    autoRotate: boolean
    backgroundColor: string
    environmentMap: string
    exposure: number
  }
}
```

### 3.3 API Client

**File**: `frontend/src/services/api/client.ts`

```typescript
const apiClient = {
  async get<T>(endpoint: string, options?: RequestOptions): Promise<T>,
  async post<T>(endpoint: string, data?: unknown, options?: RequestOptions): Promise<T>,
  async patch<T>(endpoint: string, data: unknown, options?: RequestOptions): Promise<T>,
  async delete<T>(endpoint: string, options?: RequestOptions): Promise<T>
}

// Base URL detection
const getBaseUrl = () => {
  if (window.__TAURI__) return 'http://localhost:8000/api'
  return import.meta.env.VITE_API_BASE_URL || '/api'
}
```

### 3.4 WebSocket Client

**File**: `frontend/src/services/websocket/WebSocketClient.ts`

```typescript
class WebSocketClient {
  private ws: WebSocket | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 10
  private reconnectInterval = 3000
  private pingInterval = 30000

  connect(): void
  disconnect(): void
  send(data: object): boolean

  subscribeToJob(jobId: string): void
  unsubscribeFromJob(jobId: string): void
  requestQueueStatus(): void

  // Event registration
  onMessage(handler: (data: WSMessage) => void): () => void
  onConnect(handler: () => void): () => void
  onDisconnect(handler: () => void): () => void
  onError(handler: (error: Event) => void): () => void
}
```

### 3.5 WebSocket Hook

**File**: `frontend/src/hooks/useWebSocket.ts`

```typescript
function useWebSocket() {
  useEffect(() => {
    const client = getWebSocketClient()

    // Handle incoming messages
    const unsubMessage = client.onMessage((data) => {
      switch (data.type) {
        case 'progress':
          queueStore.updateJobProgress(data.job_id, data.progress, data.stage)
          break
        case 'queue_status':
          queueStore.setQueueStatus(data)
          break
        case 'job_created':
          queueStore.addJob(data)
          generationStore.setCurrentJobId(data.job_id)
          break
        case 'asset_ready':
          uiStore.addNotification({ type: 'success', message: 'Asset ready!' })
          libraryStore.refreshAssets()
          break
        case 'error':
          uiStore.addNotification({ type: 'error', message: data.message })
          break
      }
    })

    return () => unsubMessage()
  }, [])

  return {
    isConnected: uiStore.isConnected,
    subscribeToJob: (id) => client.subscribeToJob(id),
    unsubscribeFromJob: (id) => client.unsubscribeFromJob(id),
    requestQueueStatus: () => client.requestQueueStatus()
  }
}
```

### 3.6 Component Hierarchy

```
App
├── AppShell
│   ├── Header
│   │   └── BackendStatus
│   │
│   ├── GenerationPanel
│   │   ├── ImageUploader
│   │   ├── ParameterControls
│   │   │   ├── PresetSelector
│   │   │   ├── Slider (inferenceSteps)
│   │   │   ├── Slider (guidanceScale)
│   │   │   └── Select (outputFormat)
│   │   └── GenerationProgress
│   │
│   ├── ViewerPanel
│   │   ├── GLBViewer (Three.js)
│   │   ├── ViewerToolbar
│   │   └── ModelInfo
│   │
│   └── LibraryPanel
│       ├── SearchBar
│       ├── TagManager
│       ├── AssetGrid / AssetList
│       │   └── AssetCard
│       ├── AssetDetails
│       └── BulkActions
│
├── QueuePanel (collapsible)
│   ├── QueueControls
│   └── JobCard[]
│
├── ExportModal
│   ├── EnginePresets
│   └── LODSettings
│
└── ToastContainer
```

---

## 4. Data Flow & Integration

### 4.1 Image-to-3D Generation Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           USER INTERACTION                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. User selects image and configures parameters in GenerationPanel          │
│    - generationStore.setSourceImage(file)                                    │
│    - generationStore.setParameter('inferenceSteps', 30)                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. User clicks "Generate" button                                             │
│    - generationStore.setIsGenerating(true)                                   │
│    - generationApi.generateFromImage(file, params)                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ HTTP POST /api/generation/image-to-3d
┌─────────────────────────────────────────────────────────────────────────────┐
│ 3. Backend receives request (generation/router.py)                           │
│    a. Validate image type (PNG, JPG, WEBP)                                   │
│    b. Save file: UPLOAD_DIR/YYYY/MM/DD/{uuid}.{ext}                          │
│    c. Create Asset record (status=PENDING)                                   │
│    d. Create GenerationJob record (status=PENDING)                           │
│    e. Enqueue job to JobQueue with priority                                  │
│    f. Broadcast WebSocket: { type: "job_created", job_id, queue_position }  │
│    g. Return: { jobId, assetId, status, queuePosition }                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ WebSocket "job_created"
┌─────────────────────────────────────────────────────────────────────────────┐
│ 4. Frontend receives job_created notification                                │
│    - queueStore.addJob(job)                                                  │
│    - generationStore.setCurrentJobId(jobId)                                  │
│    - wsClient.subscribeToJob(jobId)                                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 5. Background worker dequeues job (core/worker.py)                           │
│    - Mark job PROCESSING                                                     │
│    - Broadcast: { type: "progress", progress: 0.0, stage: "Starting..." }   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 6. Pipeline.generate() executes (inference/pipeline.py)                      │
│                                                                              │
│    ┌────────────────────────────────────────────────────────────────────┐   │
│    │ Step 1: Preprocess (5-15%)                                          │   │
│    │ - Load image from disk                                              │   │
│    │ - rembg background removal                                          │   │
│    │ - Resize to 512x512 RGBA                                            │   │
│    └────────────────────────────────────────────────────────────────────┘   │
│                              │ progress callback                             │
│                              ▼                                               │
│    ┌────────────────────────────────────────────────────────────────────┐   │
│    │ Step 2: Generate Shape (15-70%)                                     │   │
│    │ - Hunyuan3DDiTFlowMatchingPipeline(image, steps, guidance, octree) │   │
│    │ - Runs in ThreadPoolExecutor                                        │   │
│    │ - Output: trimesh object                                            │   │
│    └────────────────────────────────────────────────────────────────────┘   │
│                              │ progress callback                             │
│                              ▼                                               │
│    ┌────────────────────────────────────────────────────────────────────┐   │
│    │ Step 3: Generate Texture (70-90%) [if enabled]                      │   │
│    │ - Hunyuan3DPaintPipeline(mesh, image)                              │   │
│    │ - Runs in ThreadPoolExecutor                                        │   │
│    └────────────────────────────────────────────────────────────────────┘   │
│                              │ progress callback                             │
│                              ▼                                               │
│    ┌────────────────────────────────────────────────────────────────────┐   │
│    │ Step 4: Post-process & Save (90-100%)                               │   │
│    │ - Optional mesh simplification                                      │   │
│    │ - Export to GLB/OBJ/PLY/STL                                         │   │
│    │ - Generate thumbnail (256x256 PNG)                                  │   │
│    │ - Extract metadata (vertex_count, face_count)                       │   │
│    └────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│    Progress callbacks throughout: WebSocket broadcasts to subscribed clients │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 7. On Success:                                                               │
│    - Update Asset record: status=COMPLETED, vertex_count, face_count, etc.  │
│    - Update Job record: status=COMPLETED, progress=1.0                       │
│    - Broadcast: { type: "asset_ready", asset_id, name, thumbnail_url }      │
│                                                                              │
│ 7. On Failure:                                                               │
│    - Update Asset record: status=FAILED, error_message                       │
│    - Update Job record: status=FAILED                                        │
│    - Broadcast: { type: "error", code, message, job_id }                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ WebSocket "asset_ready" or "error"
┌─────────────────────────────────────────────────────────────────────────────┐
│ 8. Frontend handles completion                                               │
│    - queueStore.updateJobStatus(jobId, 'completed')                          │
│    - generationStore.setIsGenerating(false)                                  │
│    - uiStore.addNotification({ type: 'success', message: 'Complete!' })     │
│    - libraryStore.refreshAssets() → fetch updated asset list                │
│    - viewerStore.setModelUrl(asset.file_path) → load 3D model               │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Asset Library Lifecycle

```
┌──────────────────────────────────────────────────────────────────┐
│                    ASSET LIBRARY FLOW                             │
└──────────────────────────────────────────────────────────────────┘

Fetch Assets:
  LibraryPanel mount
    → libraryStore.setLoading(true)
    → assetsApi.listAssets(filters, page, pageSize)
    → GET /api/assets?page=1&page_size=20&search=...&tags=...&sort_by=created
    → libraryStore.setAssets(assets)
    → libraryStore.setTotalAssets(total)

Filter/Sort:
  User changes filter
    → libraryStore.setFilter('search', 'dragon')
    → Trigger re-fetch with updated filters

Update Asset:
  User clicks favorite
    → assetsApi.updateAsset(id, { isFavorite: true })
    → PATCH /api/assets/{id}
    → libraryStore.updateAsset(id, { isFavorite: true })

Delete Asset:
  User clicks delete
    → Confirm dialog
    → assetsApi.deleteAsset(id)
    → DELETE /api/assets/{id}
    → libraryStore.removeAsset(id)

Bulk Operations:
  User selects multiple → clicks bulk delete
    → assetsApi.bulkDeleteAssets(ids)
    → POST /api/assets/bulk-delete
    → libraryStore.removeAssets(ids)
```

### 4.3 WebSocket Message Protocol

**Client → Server Actions**:
```json
{"action": "subscribe", "job_id": "uuid"}
{"action": "unsubscribe", "job_id": "uuid"}
{"action": "request_status"}
{"action": "ping"}
```

**Server → Client Messages**:

```json
// Progress update during generation
{
  "type": "progress",
  "job_id": "uuid",
  "progress": 0.45,
  "stage": "Generating 3D shape...",
  "status": "processing",
  "timestamp": "2026-01-09T12:00:00Z"
}

// Queue status
{
  "type": "queue_status",
  "queue_size": 5,
  "current_job_id": "uuid",
  "pending_count": 4,
  "processing_count": 1,
  "completed_count": 10,
  "failed_count": 2,
  "timestamp": "2026-01-09T12:00:00Z"
}

// Job created notification
{
  "type": "job_created",
  "job_id": "uuid",
  "asset_id": "uuid",
  "job_type": "image_to_3d",
  "queue_position": 5,
  "timestamp": "2026-01-09T12:00:00Z"
}

// Asset ready notification
{
  "type": "asset_ready",
  "asset_id": "uuid",
  "name": "Dragon Model",
  "thumbnail_url": "/storage/generated/uuid/thumbnail.png",
  "download_url": "/storage/generated/uuid/model.glb",
  "timestamp": "2026-01-09T12:00:00Z"
}

// Error notification
{
  "type": "error",
  "code": "GENERATION_FAILED",
  "message": "Failed to generate 3D model",
  "job_id": "uuid",
  "details": { "reason": "CUDA out of memory" },
  "timestamp": "2026-01-09T12:00:00Z"
}

// Pong response
{
  "type": "pong",
  "timestamp": "2026-01-09T12:00:00Z"
}
```

---

## 5. API Reference

### 5.1 Generation Endpoints

#### POST `/api/generation/image-to-3d`

Submit image for 3D generation.

**Request** (multipart/form-data):
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `image` | File | Yes | Image file (PNG, JPG, WEBP) |
| `name` | string | No | Asset name |
| `inference_steps` | int | No | 5-100, default 30 |
| `guidance_scale` | float | No | 1.0-15.0, default 5.5 |
| `octree_resolution` | int | No | 128/256/384/512, default 256 |
| `seed` | int | No | Random seed |
| `generate_texture` | bool | No | Enable texture generation |
| `face_count` | int | No | Target face count for simplification |
| `output_format` | string | No | glb/obj/ply/stl, default glb |
| `mode` | string | No | fast/standard/quality |
| `priority` | string | No | low/normal/high |
| `project_id` | string | No | Associated project |
| `tags` | string | No | Comma-separated tag names |

**Response**:
```json
{
  "jobId": "uuid",
  "assetId": "uuid",
  "status": "pending",
  "message": "Job queued successfully",
  "queuePosition": 3
}
```

#### GET `/api/generation/jobs/{job_id}`

Get job status.

**Response**:
```json
{
  "jobId": "uuid",
  "assetId": "uuid",
  "status": "processing",
  "progress": 0.45,
  "stage": "Generating 3D shape...",
  "error": null,
  "createdAt": "2026-01-09T12:00:00Z",
  "startedAt": "2026-01-09T12:00:05Z",
  "completedAt": null
}
```

#### DELETE `/api/generation/jobs/{job_id}`

Cancel pending job.

**Response**:
```json
{
  "message": "Job cancelled",
  "job_id": "uuid"
}
```

#### GET `/api/generation/queue/status`

Get queue statistics.

**Response**:
```json
{
  "queueSize": 5,
  "currentJobId": "uuid",
  "pendingCount": 4,
  "processingCount": 1,
  "completedCount": 50,
  "failedCount": 3
}
```

### 5.2 Asset Endpoints

#### GET `/api/assets`

List assets with filtering and pagination.

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number |
| `page_size` | int | 20 | Items per page |
| `search` | string | - | Search name/description |
| `tags` | string | - | Comma-separated tag IDs |
| `source_type` | string | - | image_to_3d / text_to_3d |
| `has_lod` | bool | - | Filter by LOD availability |
| `is_favorite` | bool | - | Filter favorites |
| `sort_by` | string | created | created/name/size/rating |
| `sort_order` | string | desc | asc/desc |

**Response**:
```json
{
  "assets": [
    {
      "id": "uuid",
      "name": "Dragon Model",
      "description": "A fire-breathing dragon",
      "sourceType": "image_to_3d",
      "sourceImagePath": "/storage/uploads/2026/01/09/uuid.png",
      "filePath": "/storage/generated/uuid/model.glb",
      "thumbnailPath": "/storage/generated/uuid/thumbnail.png",
      "vertexCount": 15000,
      "faceCount": 10000,
      "fileSizeBytes": 2048576,
      "generationTimeSeconds": 45.5,
      "status": "completed",
      "hasLod": false,
      "isFavorite": true,
      "rating": 4,
      "tags": [{"id": 1, "name": "fantasy", "color": "#6366f1"}],
      "createdAt": "2026-01-09T12:00:00Z",
      "updatedAt": "2026-01-09T12:01:00Z"
    }
  ],
  "total": 150,
  "page": 1,
  "pageSize": 20
}
```

#### GET `/api/assets/{asset_id}`

Get single asset details.

#### PATCH `/api/assets/{asset_id}`

Update asset metadata.

**Request**:
```json
{
  "name": "New Name",
  "description": "Updated description",
  "isFavorite": true,
  "rating": 5,
  "tags": [1, 2, 3]
}
```

#### DELETE `/api/assets/{asset_id}`

Delete asset.

#### POST `/api/assets/bulk-delete`

Bulk delete assets.

**Request**:
```json
{
  "assetIds": ["uuid1", "uuid2", "uuid3"]
}
```

**Response**:
```json
{
  "message": "Assets deleted",
  "deleted_count": 3
}
```

### 5.3 Tag Endpoints

#### GET `/api/assets/tags`

List all tags.

#### POST `/api/assets/tags`

Create new tag.

**Request**:
```json
{
  "name": "fantasy",
  "color": "#6366f1"
}
```

#### DELETE `/api/assets/tags/{tag_id}`

Delete tag.

### 5.4 Export Endpoints

#### POST `/api/export/generate-lods`

Generate LOD levels for asset.

**Request**:
```json
{
  "assetId": "uuid",
  "levels": [1.0, 0.5, 0.25, 0.1]
}
```

#### POST `/api/export/validate`

Validate mesh for game engine compatibility.

**Request**:
```json
{
  "assetId": "uuid",
  "targetEngine": "unity"
}
```

**Response**:
```json
{
  "issues": [
    {
      "severity": "warning",
      "type": "high_poly_count",
      "message": "Mesh has 50000 faces, consider reducing for mobile",
      "suggestion": "Use /api/export/optimize to reduce face count"
    }
  ]
}
```

#### POST `/api/export/optimize`

Optimize mesh (remove degenerate faces, merge vertices, fix normals).

#### POST `/api/export/compress`

Apply Draco compression.

**Request**:
```json
{
  "assetId": "uuid",
  "quality": "balanced"
}
```

#### POST `/api/export/to-engine`

Export to game engine project.

**Request**:
```json
{
  "assetId": "uuid",
  "engine": "unity",
  "projectPath": "C:/Projects/MyGame",
  "subfolder": "Assets/Models",
  "generateLods": true,
  "compress": true
}
```

---

## 6. WebSocket Protocol

### 6.1 Connection

**Endpoint**: `ws://localhost:8000/ws/progress`

### 6.2 Client Actions

```typescript
// Subscribe to job updates
ws.send(JSON.stringify({ action: 'subscribe', job_id: 'uuid' }))

// Unsubscribe from job
ws.send(JSON.stringify({ action: 'unsubscribe', job_id: 'uuid' }))

// Request current queue status
ws.send(JSON.stringify({ action: 'request_status' }))

// Keep-alive ping
ws.send(JSON.stringify({ action: 'ping' }))
```

### 6.3 Server Messages

See [Section 4.3](#43-websocket-message-protocol) for message format details.

### 6.4 Connection Handling

- **Reconnection**: Automatic with exponential backoff (3s base, 1.5x multiplier)
- **Max Attempts**: 10
- **Keep-alive**: Ping every 30 seconds
- **Auto-subscribe**: On reconnect, re-subscribe to active jobs

---

## 7. Database Schema

### 7.1 Entity Relationship Diagram

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│      tags        │     │   asset_tags     │     │     assets       │
├──────────────────┤     ├──────────────────┤     ├──────────────────┤
│ id (PK)          │◄────┤ tag_id (FK)      │     │ id (PK)          │
│ name             │     │ asset_id (FK)    ├────►│ name             │
│ color            │     └──────────────────┘     │ description      │
│ created_at       │                              │ source_type      │
└──────────────────┘     ┌──────────────────┐     │ source_image_path│
                         │  project_assets  │     │ source_prompt    │
┌──────────────────┐     ├──────────────────┤     │ generation_params│
│    projects      │     │ project_id (FK)  │     │ file_path        │
├──────────────────┤◄────┤ asset_id (FK)    ├────►│ thumbnail_path   │
│ id (PK)          │     └──────────────────┘     │ vertex_count     │
│ name             │                              │ face_count       │
│ description      │                              │ file_size_bytes  │
│ engine_type      │                              │ generation_time  │
│ engine_path      │                              │ status           │
│ export_folder    │                              │ has_lod          │
│ created_at       │                              │ lod_levels       │
│ updated_at       │                              │ is_favorite      │
└──────────────────┘                              │ rating           │
                                                  │ created_at       │
┌──────────────────┐                              │ updated_at       │
│ generation_jobs  │                              └────────┬─────────┘
├──────────────────┤                                       │
│ id (PK)          │                                       │
│ asset_id (FK)    ├───────────────────────────────────────┘
│ job_type         │
│ priority         │
│ status           │
│ payload          │
│ result           │
│ error_message    │
│ progress         │
│ stage            │
│ created_at       │
│ started_at       │
│ completed_at     │
└──────────────────┘
```

### 7.2 Table Definitions

#### assets
| Column | Type | Constraints |
|--------|------|-------------|
| id | VARCHAR(36) | PRIMARY KEY |
| name | VARCHAR(255) | NOT NULL |
| description | TEXT | |
| source_type | VARCHAR(20) | NOT NULL |
| source_image_path | VARCHAR(500) | |
| source_prompt | TEXT | |
| generation_params | JSON | |
| file_path | VARCHAR(500) | |
| thumbnail_path | VARCHAR(500) | |
| vertex_count | INTEGER | |
| face_count | INTEGER | |
| file_size_bytes | BIGINT | |
| generation_time_seconds | FLOAT | |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'pending' |
| has_lod | BOOLEAN | DEFAULT FALSE |
| lod_levels | JSON | |
| is_favorite | BOOLEAN | DEFAULT FALSE |
| rating | INTEGER | |
| created_at | DATETIME | DEFAULT NOW |
| updated_at | DATETIME | DEFAULT NOW |

#### generation_jobs
| Column | Type | Constraints |
|--------|------|-------------|
| id | VARCHAR(36) | PRIMARY KEY |
| asset_id | VARCHAR(36) | FOREIGN KEY → assets.id |
| job_type | VARCHAR(50) | NOT NULL |
| priority | INTEGER | DEFAULT 1 |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'pending' |
| payload | JSON | |
| result | JSON | |
| error_message | TEXT | |
| progress | FLOAT | DEFAULT 0.0 |
| stage | VARCHAR(100) | |
| created_at | DATETIME | DEFAULT NOW |
| started_at | DATETIME | |
| completed_at | DATETIME | |

#### tags
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT |
| name | VARCHAR(50) | UNIQUE NOT NULL |
| color | VARCHAR(7) | DEFAULT '#6366f1' |
| created_at | DATETIME | DEFAULT NOW |

#### projects
| Column | Type | Constraints |
|--------|------|-------------|
| id | VARCHAR(36) | PRIMARY KEY |
| name | VARCHAR(255) | NOT NULL |
| description | TEXT | |
| engine_type | VARCHAR(20) | |
| engine_project_path | VARCHAR(500) | |
| default_export_folder | VARCHAR(500) | |
| created_at | DATETIME | DEFAULT NOW |
| updated_at | DATETIME | DEFAULT NOW |

---

## 8. Configuration

### 8.1 Backend Environment Variables

Create `.env` file in `backend/` directory:

```bash
# Application
DEBUG=false
HOST=0.0.0.0
PORT=8000

# Database
DATABASE_URL=sqlite+aiosqlite:///./data/sweedle.db

# Storage
STORAGE_ROOT=./storage
UPLOAD_DIR=./storage/uploads
GENERATED_DIR=./storage/generated
EXPORT_DIR=./storage/exports

# Hunyuan3D
HUNYUAN_MODEL_PATH=tencent/Hunyuan3D-2.1
HUNYUAN_SUBFOLDER=hunyuan3d-dit-v2-1
DEVICE=cuda
LOW_VRAM_MODE=false

# Generation Defaults
DEFAULT_INFERENCE_STEPS=30
DEFAULT_GUIDANCE_SCALE=5.5
DEFAULT_OCTREE_RESOLUTION=256

# Queue
MAX_QUEUE_SIZE=100
JOB_TIMEOUT_SECONDS=600

# LOD (JSON array)
LOD_LEVELS=[1.0, 0.5, 0.25, 0.1]

# Engine Paths (optional)
UNITY_PROJECT_PATH=
UNREAL_PROJECT_PATH=
GODOT_PROJECT_PATH=
```

### 8.2 Frontend Environment Variables

Create `.env` file in `frontend/` directory:

```bash
VITE_API_BASE_URL=http://localhost:8000/api
VITE_WS_BASE_URL=ws://localhost:8000
```

### 8.3 Model Cache Locations

| Model | Cache Path |
|-------|------------|
| Hunyuan3D-2.1 | `~/.cache/huggingface/hub/models--tencent--Hunyuan3D-2.1/` |
| hy3dgen local | `~/.cache/hy3dgen/tencent/Hunyuan3D-2.1/` |
| rembg U2Net | `~/.u2net/` |

---

## 9. Rigging System

### 9.1 Architecture Overview

The rigging system provides automated skeleton generation and weight painting for 3D models using a hybrid approach:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           RIGGING FLOW                                       │
└─────────────────────────────────────────────────────────────────────────────┘

User selects asset in Library
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│  RiggingPanel   │────►│ POST /api/      │
│  (Frontend)     │     │ rigging/auto-rig│
└─────────────────┘     └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │   Job Queue     │
                        │ (rig_asset job) │
                        └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │ Background      │
                        │ Worker          │
                        └────────┬────────┘
                                 │
              ┌──────────────────┴──────────────────┐
              │                                     │
              ▼                                     ▼
     ┌─────────────────┐                   ┌─────────────────┐
     │    UniRig       │                   │    Blender      │
     │  (Humanoid)     │                   │  (Quadruped)    │
     └────────┬────────┘                   └────────┬────────┘
              │                                     │
              └──────────────────┬──────────────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │ Rigged GLB      │
                        │ + Skeleton Data │
                        └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │ WebSocket       │
                        │ (rigging_complete)
                        └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │ Viewer shows    │
                        │ skeleton overlay│
                        └─────────────────┘
```

### 9.2 Backend Components

#### 9.2.1 Rigging Router

**File**: `backend/src/rigging/router.py`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/rigging/auto-rig` | POST | Submit asset for auto-rigging |
| `/api/rigging/jobs/{job_id}` | GET | Get rigging job status |
| `/api/rigging/jobs/{job_id}` | DELETE | Cancel rigging job |
| `/api/rigging/skeleton/{asset_id}` | GET | Get skeleton data |
| `/api/rigging/detect-type` | POST | Detect character type |
| `/api/rigging/templates` | GET | List skeleton templates |
| `/api/rigging/export-fbx` | POST | Export as FBX |

#### 9.2.2 RiggingService

**File**: `backend/src/rigging/service.py`

```python
class RiggingService:
    async def auto_rig(self, asset_id, character_type, processor) -> RiggingResult:
        """
        Main rigging workflow:
        1. Load mesh from asset
        2. Detect character type (if auto)
        3. Select processor (UniRig or Blender)
        4. Generate skeleton
        5. Calculate weights
        6. Export rigged mesh
        """

    async def detect_character_type(self, asset_id) -> CharacterType:
        """Analyze mesh proportions to determine humanoid vs quadruped"""

    async def export_fbx(self, asset_id, engine) -> Path:
        """Convert rigged GLB to FBX using Blender"""
```

#### 9.2.3 Rigging Processors

**Base Processor** (`backend/src/rigging/processors/base.py`):
```python
class BaseRiggingProcessor(ABC):
    @abstractmethod
    async def process(self, mesh_path, character_type, progress_callback) -> RiggingResult

    @abstractmethod
    async def is_available(self) -> bool
```

**UniRig Processor** (`backend/src/rigging/processors/unirig.py`):
- ML-based rigging for humanoid meshes
- Uses heuristic-based skeleton fitting
- Proximity-based weight calculation
- Fast processing (~5-10 seconds)

**Blender Processor** (`backend/src/rigging/processors/blender.py`):
- Headless Blender scripting
- Better for quadrupeds and complex meshes
- FBX export capability
- More control over bone placement

#### 9.2.4 Skeleton Templates

**Humanoid Template** (`backend/src/rigging/skeleton/humanoid.py`):
- 65 bones (Mixamo/Unity compatible)
- Full body: spine, arms, legs, hands, feet
- Bone hierarchy follows industry standards

**Quadruped Template** (`backend/src/rigging/skeleton/quadruped.py`):
- 45 bones
- Spine, four legs, tail, head
- Optimized for animals

### 9.3 Data Models

#### SkeletonData (stored in Asset.rigging_data)

```python
class SkeletonData(BaseModel):
    root_bone: str                    # "Hips" for humanoid
    bones: list[BoneData]             # All bones
    character_type: CharacterType     # "humanoid" | "quadruped"
    bone_count: int                   # Total bones

class BoneData(BaseModel):
    name: str                         # "LeftArm"
    parent: str | None                # "LeftShoulder"
    head_position: tuple[float, 3]    # [x, y, z]
    tail_position: tuple[float, 3]    # [x, y, z]
    rotation: tuple[float, 4]         # Quaternion [x, y, z, w]
```

#### Asset Rigging Fields

```python
# Added to Asset model
is_rigged = Column(Boolean, default=False)
rigging_data = Column(JSON, nullable=True)        # SkeletonData
character_type = Column(String(50), nullable=True)
rigged_mesh_path = Column(String(500), nullable=True)
rigging_processor = Column(String(50), nullable=True)
```

### 9.4 API Reference

#### POST `/api/rigging/auto-rig`

Submit asset for auto-rigging.

**Request** (multipart/form-data):
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `asset_id` | string | Yes | Asset UUID |
| `character_type` | string | No | auto/humanoid/quadruped |
| `processor` | string | No | auto/unirig/blender |
| `priority` | string | No | low/normal/high |

**Response**:
```json
{
  "job_id": "uuid",
  "asset_id": "uuid",
  "status": "pending",
  "message": "Rigging job submitted",
  "queue_position": 2
}
```

#### GET `/api/rigging/jobs/{job_id}`

Get rigging job status.

**Response**:
```json
{
  "job_id": "uuid",
  "asset_id": "uuid",
  "status": "processing",
  "progress": 0.45,
  "stage": "Creating skeleton...",
  "detected_type": "humanoid",
  "processor_used": "unirig",
  "error": null,
  "created_at": "2026-01-09T12:00:00Z",
  "started_at": "2026-01-09T12:00:05Z",
  "completed_at": null
}
```

#### GET `/api/rigging/skeleton/{asset_id}`

Get skeleton data for rigged asset.

**Response**:
```json
{
  "asset_id": "uuid",
  "skeleton": {
    "root_bone": "Hips",
    "bones": [
      {
        "name": "Hips",
        "parent": null,
        "head_position": [0, 1.0, 0],
        "tail_position": [0, 1.1, 0],
        "rotation": [0, 0, 0, 1]
      }
    ],
    "character_type": "humanoid",
    "bone_count": 65
  },
  "rigged_mesh_path": "/storage/generated/uuid/model_rigged.glb",
  "processor_used": "unirig",
  "created_at": "2026-01-09T12:00:00Z"
}
```

#### GET `/api/rigging/templates`

List available skeleton templates.

**Response**:
```json
{
  "templates": [
    {
      "name": "humanoid_standard",
      "character_type": "humanoid",
      "bone_count": 65,
      "description": "Standard humanoid skeleton (Mixamo compatible)"
    },
    {
      "name": "quadruped_standard",
      "character_type": "quadruped",
      "bone_count": 45,
      "description": "Standard quadruped skeleton"
    }
  ]
}
```

### 9.5 WebSocket Messages

#### rigging_progress

```json
{
  "type": "rigging_progress",
  "job_id": "uuid",
  "progress": 0.45,
  "stage": "Creating skeleton...",
  "detected_type": "humanoid"
}
```

#### rigging_complete

```json
{
  "type": "rigging_complete",
  "asset_id": "uuid",
  "character_type": "humanoid",
  "bone_count": 65
}
```

#### rigging_failed

```json
{
  "type": "rigging_failed",
  "asset_id": "uuid",
  "error": "Failed to generate skeleton"
}
```

### 9.6 Frontend Components

#### riggingStore.ts

```typescript
interface RiggingState {
  // Job state
  currentJobId: string | null
  isRigging: boolean
  progress: number
  stage: string
  status: RiggingStatus

  // Configuration
  characterType: 'humanoid' | 'quadruped' | 'auto'
  processor: 'unirig' | 'blender' | 'auto'

  // Results
  detectedType: CharacterType | null
  skeletonData: SkeletonData | null
  error: string | null

  // Viewer
  showSkeleton: boolean
  selectedBone: string | null
}
```

#### RiggingPanel.tsx

Main rigging UI with:
- Asset preview
- Character type selector (auto/humanoid/quadruped)
- Processor selector (auto/unirig/blender)
- Progress display with stages
- Completion/error states

#### SkeletonVisualization.tsx

Three.js component for rendering skeleton:
- Cylinder bones with joint spheres
- Color coding (root=pink, selected=yellow, normal=blue)
- Clickable bones for selection
- Toggle visibility via toolbar

### 9.7 Rigging Flow

```
1. User selects completed asset in Library
2. Opens RiggingPanel
3. Selects character type (or auto-detect)
4. Clicks "Start Auto-Rigging"
5. Frontend calls POST /api/rigging/auto-rig
6. Job queued, returns job_id
7. Worker processes job:
   a. Load mesh (0-15%)
   b. Detect character type (15-25%)
   c. Create skeleton from template (25-50%)
   d. Calculate vertex weights (50-75%)
   e. Export rigged mesh (75-100%)
8. WebSocket broadcasts progress
9. On complete:
   - Asset.is_rigged = true
   - Asset.rigging_data = skeleton
   - Frontend fetches skeleton
   - Viewer shows bone overlay
```

---

## 10. Key Files Reference

### 10.1 Backend Files

| File | Purpose |
|------|---------|
| `backend/src/main.py` | FastAPI app entry point, lifespan, routing |
| `backend/src/config.py` | Pydantic settings, environment variables |
| `backend/src/database.py` | SQLAlchemy async setup |
| `backend/src/generation/models.py` | ORM model definitions |
| `backend/src/generation/router.py` | Generation API endpoints |
| `backend/src/generation/service.py` | Generation business logic |
| `backend/src/generation/schemas.py` | Pydantic request/response schemas |
| `backend/src/assets/router.py` | Asset library API endpoints |
| `backend/src/export/router.py` | Export/LOD API endpoints |
| `backend/src/websocket/router.py` | WebSocket endpoint handler |
| `backend/src/core/queue.py` | Priority job queue |
| `backend/src/core/worker.py` | Background processing loop |
| `backend/src/core/websocket_manager.py` | WebSocket connection manager |
| `backend/src/inference/pipeline.py` | Hunyuan3D wrapper |
| `backend/src/inference/preprocessor.py` | Image preprocessing (rembg) |
| `backend/src/inference/config.py` | Generation configuration |
| `backend/src/rigging/router.py` | Rigging API endpoints |
| `backend/src/rigging/service.py` | RiggingService business logic |
| `backend/src/rigging/schemas.py` | Rigging Pydantic schemas |
| `backend/src/rigging/config.py` | Rigging configuration |
| `backend/src/rigging/processors/unirig.py` | UniRig ML processor |
| `backend/src/rigging/processors/blender.py` | Blender headless processor |
| `backend/src/rigging/skeleton/humanoid.py` | 65-bone humanoid template |
| `backend/src/rigging/skeleton/quadruped.py` | 45-bone quadruped template |

### 10.2 Frontend Files

| File | Purpose |
|------|---------|
| `frontend/src/App.tsx` | Main React application |
| `frontend/src/stores/generationStore.ts` | Generation state |
| `frontend/src/stores/libraryStore.ts` | Asset library state |
| `frontend/src/stores/queueStore.ts` | Job queue state |
| `frontend/src/stores/viewerStore.ts` | 3D viewer state |
| `frontend/src/stores/uiStore.ts` | UI/notification state |
| `frontend/src/stores/riggingStore.ts` | Rigging state management |
| `frontend/src/services/api/client.ts` | HTTP client |
| `frontend/src/services/api/generation.ts` | Generation API calls |
| `frontend/src/services/api/assets.ts` | Asset API calls |
| `frontend/src/services/api/rigging.ts` | Rigging API calls |
| `frontend/src/services/websocket/WebSocketClient.ts` | WebSocket client |
| `frontend/src/hooks/useWebSocket.ts` | WebSocket integration hook |
| `frontend/src/types/index.ts` | TypeScript type definitions |
| `frontend/src/components/generation/` | Generation UI components |
| `frontend/src/components/viewer/` | 3D viewer components |
| `frontend/src/components/viewer/GLBViewer.tsx` | 3D model viewer |
| `frontend/src/components/viewer/SkeletonVisualization.tsx` | Bone rendering |
| `frontend/src/components/library/` | Asset library components |
| `frontend/src/components/rigging/RiggingPanel.tsx` | Main rigging UI |
| `frontend/src/components/rigging/CharacterTypeSelector.tsx` | Type picker |
| `frontend/src/components/rigging/RiggingProgress.tsx` | Progress display |

---

## Appendix A: Known Issues & Workarounds

### A.1 hy3dgen `.to()` Returns None

**Issue**: The Hunyuan3D library's `.to()` method doesn't return `self` (bug in their code).

**Workaround**: Don't reassign after `.to()` call:
```python
# Wrong
self.pipeline = pipeline.to(device)  # Returns None!

# Correct
pipeline.to(device)  # Modifies in place
self.pipeline = pipeline
```

### A.2 Texture Generation Disabled

**Issue**: Requires `custom_rasterizer` CUDA module compilation.

**Workaround**: Texture generation is disabled by default. Models are exported untextured.

### A.3 Thumbnail Generation

**Issue**: Requires `pyglet` which has display dependencies.

**Workaround**: Thumbnails may fail silently on headless systems. Not critical for functionality.

---

## Appendix B: Generation Parameter Guidelines

| Parameter | Fast | Standard | Quality |
|-----------|------|----------|---------|
| Inference Steps | 15 | 30 | 50 |
| Guidance Scale | 4.0 | 5.5 | 7.0 |
| Octree Resolution | 128 | 256 | 512 |
| Typical Time | ~15s | ~30s | ~60s+ |
| VRAM Usage | ~4GB | ~6GB | ~10GB+ |

---

*Document generated for Sweedle v1.1.0 - includes Auto-Rigging System*
