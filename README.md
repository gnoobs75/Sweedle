# Sweedle

A feature-rich, local 3D asset generator UI for game development, powered by **Hunyuan3D-2.1** from Tencent.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-green.svg)
![Node.js](https://img.shields.io/badge/node.js-18+-green.svg)
![GPU](https://img.shields.io/badge/GPU-NVIDIA%20RTX-76B900.svg)

**GitHub**: https://github.com/gnoobs75/Sweedle.git

---

## Overview

Sweedle transforms 2D concept art, screenshots, or text descriptions into game-ready 3D assets using state-of-the-art AI models. Built for game developers who want to rapidly prototype 3D content without leaving their local machine.

### Key Features

- **Image-to-3D Generation**: Upload concept art, sketches, or screenshots to generate textured 3D models
- **Tiered UI**: Simple mode (3-click workflow) for quick generation, Advanced mode for fine-tuning parameters
- **Real-time Progress**: WebSocket-based progress tracking with stage indicators
- **Asset Library**: Browse, search, tag, and manage all generated assets
- **Batch Processing**: Queue multiple generation jobs with priority control
- **LOD Generation**: Automatic Level of Detail variants for game optimization
- **Game Engine Export**: Direct export to Unity, Unreal Engine, and Godot project folders
- **Background Removal**: Automatic background removal using rembg for cleaner inputs

---

## System Requirements

### Minimum Requirements

| Component | Requirement |
|-----------|-------------|
| **GPU** | NVIDIA RTX 3070 (8GB VRAM) |
| **RAM** | 16GB |
| **Storage** | 20GB free space |
| **OS** | Windows 10/11, Linux (Ubuntu 20.04+) |

### Recommended Requirements

| Component | Requirement |
|-----------|-------------|
| **GPU** | NVIDIA RTX 4090 (24GB VRAM) |
| **RAM** | 64GB+ |
| **Storage** | 50GB+ SSD |
| **OS** | Windows 11 |

### Software Dependencies

| Software | Version | Purpose |
|----------|---------|---------|
| **Python** | 3.11.x (not 3.14!) | Backend runtime |
| **Node.js** | 18+ | Frontend build |
| **CUDA** | 12.1+ | GPU acceleration |
| **Git** | Latest | Version control |

> **Important**: Python 3.14 is too new and incompatible with some dependencies (onnxruntime). Use Python 3.11 or 3.12.

---

## Quick Start

### Windows (Recommended)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/gnoobs75/Sweedle.git
   cd Sweedle
   ```

2. **Run setup** (creates venv, installs dependencies):
   ```bash
   setup.bat
   ```

3. **Start the application**:
   ```bash
   start.bat
   ```

4. Open http://localhost:5173 in your browser

### Manual Installation

#### Backend Setup

```bash
cd backend

# Create virtual environment with Python 3.11
py -3.11 -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install PyTorch with CUDA support
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# Install Hunyuan3D
pip install git+https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1.git

# Install remaining dependencies
pip install -r requirements.txt

# Start the server
uvicorn src.main:app --host 127.0.0.1 --port 8000
```

#### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

---

## Architecture

```
Sweedle/
├── backend/                    # Python FastAPI backend
│   ├── src/
│   │   ├── main.py            # Application entry point
│   │   ├── config.py          # Pydantic settings
│   │   ├── database.py        # SQLite async setup
│   │   │
│   │   ├── core/              # Core infrastructure
│   │   │   ├── queue.py       # asyncio job queue
│   │   │   ├── worker.py      # Background GPU worker
│   │   │   └── websocket_manager.py
│   │   │
│   │   ├── inference/         # AI Model integration
│   │   │   ├── pipeline.py    # Hunyuan3D wrapper
│   │   │   ├── preprocessor.py # rembg background removal
│   │   │   └── config.py      # Generation parameters
│   │   │
│   │   ├── generation/        # Generation API
│   │   │   ├── router.py      # REST endpoints
│   │   │   ├── service.py     # Business logic
│   │   │   ├── models.py      # SQLAlchemy ORM
│   │   │   └── schemas.py     # Pydantic models
│   │   │
│   │   ├── assets/            # Asset library API
│   │   │   ├── router.py      # CRUD endpoints
│   │   │   └── schemas.py     # Asset schemas
│   │   │
│   │   ├── export/            # Export pipeline
│   │   │   ├── lod_generator.py
│   │   │   ├── engine_exporter.py
│   │   │   └── mesh_optimizer.py
│   │   │
│   │   └── websocket/         # Real-time updates
│   │       └── router.py
│   │
│   └── storage/               # File storage
│       ├── uploads/           # Source images
│       └── generated/         # Output 3D models
│
├── frontend/                  # React TypeScript frontend
│   └── src/
│       ├── App.tsx           # Main application
│       ├── components/
│       │   ├── ui/           # Reusable UI components
│       │   ├── generation/   # Generation panels
│       │   ├── viewer/       # 3D model viewer
│       │   ├── library/      # Asset library
│       │   ├── queue/        # Job queue UI
│       │   └── export/       # Export panels
│       │
│       ├── stores/           # Zustand state management
│       ├── hooks/            # Custom React hooks
│       └── services/         # API clients
│
├── start.bat                 # Start both services
├── start-backend-debug.bat   # Backend with verbose output
└── setup.bat                 # Initial setup script
```

---

## Technology Stack

### Backend

| Technology | Version | Purpose |
|------------|---------|---------|
| **FastAPI** | 0.109+ | Async REST API + WebSocket |
| **SQLAlchemy** | 2.0+ | Async ORM |
| **SQLite** | 3.x | Embedded database |
| **PyTorch** | 2.1+ | ML framework (CUDA 12.1) |
| **Hunyuan3D-2.1** | Latest | 3D generation model |
| **rembg** | 2.0+ | Background removal |
| **trimesh** | 4.0+ | Mesh processing |
| **Pillow** | 10.0+ | Image processing |

### Frontend

| Technology | Version | Purpose |
|------------|---------|---------|
| **React** | 19.x | UI framework |
| **TypeScript** | 5.x | Type safety |
| **Vite** | 5.x | Build tool |
| **React Three Fiber** | 9.x | 3D rendering |
| **Three.js** | 0.170+ | WebGL library |
| **Zustand** | 5.x | State management |
| **TailwindCSS** | 4.x | Styling |

### Third-Party AI Models

| Model | Provider | Purpose |
|-------|----------|---------|
| **Hunyuan3D-2.1** | Tencent | Image-to-3D generation |
| **U2Net** | rembg | Background removal |
| **DINO** | (via hy3dgen) | Image understanding |

---

## API Reference

### Generation Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/generation/image-to-3d` | Submit image for 3D generation |
| `POST` | `/api/generation/text-to-3d` | Submit text prompt (planned) |
| `GET` | `/api/generation/jobs/{id}` | Get job status |
| `DELETE` | `/api/generation/jobs/{id}` | Cancel pending job |
| `GET` | `/api/generation/queue/status` | Get queue status |

### Asset Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/assets` | List assets (paginated, filterable) |
| `GET` | `/api/assets/{id}` | Get asset details |
| `PATCH` | `/api/assets/{id}` | Update asset metadata |
| `DELETE` | `/api/assets/{id}` | Delete asset |
| `GET` | `/api/assets/tags` | List all tags |

### WebSocket

| Endpoint | Purpose |
|----------|---------|
| `/ws/progress` | Real-time progress updates |

---

## Configuration

### Environment Variables

Create a `.env` file in the `backend/` directory:

```env
# Application
APP_NAME=Sweedle
DEBUG=false

# Server
HOST=0.0.0.0
PORT=8000

# Hunyuan3D
HUNYUAN_MODEL_PATH=tencent/Hunyuan3D-2.1
DEVICE=cuda
LOW_VRAM_MODE=false

# Generation defaults
DEFAULT_INFERENCE_STEPS=30
DEFAULT_GUIDANCE_SCALE=5.5
DEFAULT_OCTREE_RESOLUTION=256

# Engine export paths (optional)
UNITY_PROJECT_PATH=
UNREAL_PROJECT_PATH=
GODOT_PROJECT_PATH=
```

---

## Troubleshooting

### Common Issues

#### "Python not found"
Install Python 3.11 from https://www.python.org/downloads/release/python-3119/
Make sure to check "Add Python to PATH" during installation.

#### "onnxruntime requires Python <3.14"
You have Python 3.14 installed. Install Python 3.11 or 3.12 instead.

#### "CUDA out of memory"
- Enable `LOW_VRAM_MODE=true` in .env
- Reduce `octree_resolution` to 128
- Close other GPU-intensive applications

#### "Model files not found"
The first run downloads ~8GB of model files. Ensure you have:
- Stable internet connection
- Sufficient disk space in `~/.cache/huggingface/`

#### Backend shows "Using mock mesh generation"
The Hunyuan3D model isn't loading. Check:
1. CUDA is properly installed (`nvidia-smi`)
2. PyTorch has CUDA support (`python -c "import torch; print(torch.cuda.is_available())"`)
3. Model files downloaded successfully

---

## Future Roadmap

### Planned Features

- [ ] **Mesh Refinement**: Apply subdivision and smoothing
- [ ] **Auto-Rigging**: Automatic skeleton generation for characters
- [ ] **Texture Enhancement**: AI upscaling and PBR material generation
- [ ] **Animation Support**: Basic idle/walk animations
- [ ] **Multi-Model Pipeline**: Chain multiple AI models for better results
- [ ] **Blender Integration**: Direct export to Blender projects
- [ ] **Custom Training**: Fine-tune models on your art style

### Version History

- **v1.0.0** - Initial release with image-to-3D generation

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

MIT License - See [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- [Hunyuan3D-2.1](https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1) by Tencent
- [React Three Fiber](https://github.com/pmndrs/react-three-fiber) by Poimandres
- [rembg](https://github.com/danielgatis/rembg) by Daniel Gatis
- [FastAPI](https://fastapi.tiangolo.com/) by Sebastián Ramírez

---

## Support

- **Issues**: https://github.com/gnoobs75/Sweedle/issues
- **Discussions**: https://github.com/gnoobs75/Sweedle/discussions
