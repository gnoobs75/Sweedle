# Sweedle Frontend

React-based frontend for Sweedle, providing an intuitive UI for 3D asset generation, visualization, and management.

---

## Overview

The frontend delivers:
- **Generation Interface**: Simple and advanced modes for 3D generation
- **3D Viewer**: Real-time GLB preview with React Three Fiber
- **Asset Library**: Browse, search, tag, and manage assets
- **Job Queue**: Monitor and control generation jobs
- **Export Tools**: Export to game engines

---

## Technology Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| **React** | 19.x | UI framework |
| **TypeScript** | 5.x | Type safety |
| **Vite** | 5.4+ | Build tool & dev server |
| **React Three Fiber** | 9.x | 3D rendering |
| **Three.js** | 0.170+ | WebGL library |
| **@react-three/drei** | 10.x | R3F helpers |
| **Zustand** | 5.x | State management |
| **TailwindCSS** | 4.x | Utility-first CSS |
| **clsx** | 2.x | Class name utilities |

---

## Directory Structure

```
frontend/
├── src/
│   ├── main.tsx              # Application entry point
│   ├── App.tsx               # Root component & layout
│   ├── index.css             # Global styles & Tailwind
│   │
│   ├── components/
│   │   ├── ui/               # Reusable UI primitives
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Slider.tsx
│   │   │   ├── Checkbox.tsx
│   │   │   ├── Select.tsx
│   │   │   ├── Toggle.tsx
│   │   │   ├── Badge.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── Spinner.tsx
│   │   │   ├── ProgressBar.tsx
│   │   │   ├── Tooltip.tsx
│   │   │   ├── Toast.tsx
│   │   │   ├── BackendStatus.tsx
│   │   │   ├── DebugPanel.tsx
│   │   │   └── index.ts      # Barrel export
│   │   │
│   │   ├── layout/           # Layout components
│   │   │   ├── AppShell.tsx  # Main app layout
│   │   │   ├── Header.tsx    # Top navigation
│   │   │   └── ResizablePanel.tsx
│   │   │
│   │   ├── generation/       # Generation UI
│   │   │   ├── SimpleModePanel.tsx    # 3-click workflow
│   │   │   ├── AdvancedModePanel.tsx  # Full parameters
│   │   │   ├── GenerationPanel.tsx    # Container
│   │   │   ├── ImageUploader.tsx      # Drag & drop
│   │   │   ├── ParameterControls.tsx  # Sliders/inputs
│   │   │   └── GenerationProgress.tsx # Progress indicator
│   │   │
│   │   ├── viewer/           # 3D viewer
│   │   │   ├── GLBViewer.tsx        # Three.js canvas
│   │   │   ├── ViewerPanel.tsx      # Container
│   │   │   ├── ViewerToolbar.tsx    # View controls
│   │   │   ├── ViewerStates.tsx     # Loading/error states
│   │   │   └── ModelInfo.tsx        # Mesh statistics
│   │   │
│   │   ├── library/          # Asset library
│   │   │   ├── LibraryPanel.tsx     # Main container
│   │   │   ├── AssetGrid.tsx        # Grid layout
│   │   │   ├── AssetCard.tsx        # Asset thumbnail
│   │   │   ├── AssetDetails.tsx     # Detail sidebar
│   │   │   ├── SearchBar.tsx        # Search & filters
│   │   │   ├── TagManager.tsx       # Tag UI
│   │   │   └── BulkActions.tsx      # Multi-select actions
│   │   │
│   │   ├── queue/            # Job queue
│   │   │   ├── QueuePanel.tsx       # Queue container
│   │   │   ├── JobCard.tsx          # Job item
│   │   │   ├── QueueControls.tsx    # Pause/resume/clear
│   │   │   └── FolderImporter.tsx   # Batch import
│   │   │
│   │   └── export/           # Export tools
│   │       ├── ExportPanel.tsx      # Export container
│   │       └── EnginePresets.tsx    # Engine configs
│   │
│   ├── stores/               # Zustand state stores
│   │   ├── generationStore.ts
│   │   ├── viewerStore.ts
│   │   ├── libraryStore.ts
│   │   ├── queueStore.ts
│   │   └── uiStore.ts
│   │
│   ├── hooks/                # Custom React hooks
│   │   ├── useWebSocket.ts   # WebSocket connection
│   │   └── useModelLoader.ts # GLB loading
│   │
│   ├── services/             # API services
│   │   └── api.ts            # REST client
│   │
│   └── types/                # TypeScript types
│       └── index.ts
│
├── public/                   # Static assets
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.js
└── postcss.config.js
```

---

## Component Documentation

### UI Components (`components/ui/`)

Reusable primitive components following a consistent design system.

#### Button
```tsx
import { Button } from '@/components/ui';

<Button variant="primary" size="lg" onClick={handleClick}>
  Generate 3D
</Button>
```

**Props:**
- `variant`: 'primary' | 'secondary' | 'ghost' | 'danger'
- `size`: 'sm' | 'md' | 'lg'
- `loading`: boolean
- `disabled`: boolean

#### Slider
```tsx
<Slider
  label="Inference Steps"
  value={30}
  min={5}
  max={100}
  step={5}
  onChange={setValue}
/>
```

#### Input, Select, Checkbox, Toggle
Standard form controls with consistent styling.

---

### Generation Components (`components/generation/`)

#### SimpleModePanel
3-click generation workflow:
1. Upload image
2. Click generate
3. View result

```tsx
<SimpleModePanel onGenerate={handleGenerate} />
```

#### AdvancedModePanel
Full parameter control:
- Inference steps (5-100)
- Guidance scale (1.0-15.0)
- Octree resolution (128, 256, 384, 512)
- Seed (for reproducibility)
- Texture generation toggle
- Face count target

```tsx
<AdvancedModePanel
  parameters={params}
  onChange={setParams}
  onGenerate={handleGenerate}
/>
```

#### ImageUploader
Drag-and-drop or click-to-browse image uploader.

```tsx
<ImageUploader
  onImageSelect={handleImage}
  accept="image/*"
  maxSize={10 * 1024 * 1024} // 10MB
/>
```

---

### Viewer Components (`components/viewer/`)

#### GLBViewer
React Three Fiber canvas for 3D model visualization.

```tsx
<GLBViewer
  modelUrl="/storage/generated/{id}/{id}.glb"
  onLoad={handleLoad}
  onError={handleError}
/>
```

**Features:**
- Orbit controls (rotate, zoom, pan)
- Environment lighting (HDR)
- Grid helper
- Wireframe mode
- Auto-fit camera to model

#### ViewerToolbar
Controls for viewer interaction:
- Wireframe toggle
- Grid toggle
- Auto-rotate toggle
- Reset camera
- Full-screen

---

### Library Components (`components/library/`)

#### LibraryPanel
Main asset library container with:
- Search bar with filters
- Grid/list view toggle
- Pagination
- Sort controls

#### AssetCard
Thumbnail card for each asset:
- Preview image/placeholder
- Name
- Vertex/face count
- Status badge
- Quick actions (view, delete)

#### SearchBar
Filter controls:
- Text search
- Source type filter
- Status filter
- Tag filter
- Sort options

---

### Queue Components (`components/queue/`)

#### QueuePanel
Real-time job queue display:
- Current job with progress
- Pending jobs list
- Completed/failed history

#### JobCard
Individual job display:
- Progress bar
- Stage indicator
- Cancel button
- Error display

---

## State Management

Using Zustand for global state.

### generationStore
```typescript
interface GenerationState {
  mode: 'simple' | 'advanced';
  parameters: GenerationParameters;
  currentImage: File | null;
  isGenerating: boolean;
  currentJobId: string | null;
  progress: number;
  stage: string;

  setMode: (mode: 'simple' | 'advanced') => void;
  setParameters: (params: Partial<GenerationParameters>) => void;
  setCurrentImage: (file: File | null) => void;
  startGeneration: () => void;
  updateProgress: (progress: number, stage: string) => void;
  completeGeneration: () => void;
}
```

### viewerStore
```typescript
interface ViewerState {
  currentAsset: Asset | null;
  modelUrl: string | null;
  isLoading: boolean;
  showWireframe: boolean;
  showGrid: boolean;
  autoRotate: boolean;

  loadAsset: (asset: Asset) => void;
  toggleWireframe: () => void;
  toggleGrid: () => void;
  toggleAutoRotate: () => void;
}
```

### libraryStore
```typescript
interface LibraryState {
  assets: Asset[];
  selectedIds: string[];
  filters: AssetFilters;
  pagination: PaginationState;

  fetchAssets: () => Promise<void>;
  selectAsset: (id: string) => void;
  deleteAsset: (id: string) => Promise<void>;
  updateFilters: (filters: Partial<AssetFilters>) => void;
}
```

---

## WebSocket Integration

Real-time updates via WebSocket connection.

### Connection
```typescript
import { useWebSocket } from '@/hooks/useWebSocket';

const { isConnected, lastMessage } = useWebSocket('/ws/progress');
```

### Message Types

```typescript
// Progress update
{
  type: 'progress',
  data: {
    job_id: string,
    progress: number,  // 0.0 - 1.0
    stage: string,
    status: 'processing' | 'completed' | 'failed'
  }
}

// Asset ready
{
  type: 'asset_ready',
  data: {
    asset_id: string,
    name: string,
    thumbnail_url: string,
    download_url: string
  }
}

// Queue status
{
  type: 'queue_status',
  data: {
    queue_size: number,
    current_job_id: string | null,
    pending_count: number
  }
}
```

---

## API Integration

### REST Client

```typescript
import { api } from '@/services/api';

// Submit generation
const response = await api.post('/api/generation/image-to-3d', formData);

// Fetch assets
const assets = await api.get('/api/assets', { params: filters });

// Delete asset
await api.delete(`/api/assets/${id}`);
```

### Base URL Configuration

The Vite dev server proxies `/api` and `/ws` to the backend:

```typescript
// vite.config.ts
export default defineConfig({
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/ws': { target: 'ws://localhost:8000', ws: true },
      '/storage': 'http://localhost:8000'
    }
  }
});
```

---

## Styling

### TailwindCSS
Utility-first CSS with custom configuration.

```tsx
<div className="flex items-center gap-4 p-4 bg-gray-800 rounded-lg">
  <span className="text-sm text-gray-400">Status:</span>
  <Badge variant="success">Complete</Badge>
</div>
```

### Custom Classes
Extended in `tailwind.config.js`:
- Custom colors for dark theme
- Animation utilities
- 3D transform utilities

### CSS Variables
Global variables in `index.css`:
```css
:root {
  --primary: #3b82f6;
  --background: #0f172a;
  --foreground: #f8fafc;
  /* ... */
}
```

---

## Development

### Start Development Server

```bash
npm run dev
```

Opens at http://localhost:5173 with hot reload.

### Build for Production

```bash
npm run build
```

Output in `dist/` directory.

### Preview Production Build

```bash
npm run preview
```

### Lint

```bash
npm run lint
```

---

## Type Definitions

### Asset
```typescript
interface Asset {
  id: string;
  name: string;
  source_type: 'image_to_3d' | 'text_to_3d';
  source_image_path?: string;
  source_prompt?: string;
  file_path: string;
  thumbnail_path?: string;
  vertex_count: number;
  face_count: number;
  file_size_bytes: number;
  generation_time_seconds: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  is_favorite: boolean;
  tags: Tag[];
  created_at: string;
  updated_at: string;
}
```

### GenerationParameters
```typescript
interface GenerationParameters {
  inference_steps: number;      // 5-100
  guidance_scale: number;       // 1.0-15.0
  octree_resolution: number;    // 128, 256, 384, 512
  seed?: number;
  generate_texture: boolean;
  face_count?: number;
  output_format: 'glb' | 'obj' | 'fbx';
  mode: 'simple' | 'standard' | 'detailed';
}
```

### Job
```typescript
interface Job {
  id: string;
  asset_id: string;
  job_type: 'image_to_3d' | 'text_to_3d';
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  stage: string;
  error?: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
}
```

---

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

WebGL 2.0 required for 3D viewer.
