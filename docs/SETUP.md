# Sweedle Setup Guide

Complete guide for setting up Sweedle on Windows with NVIDIA GPU.

---

## Prerequisites

### Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| GPU | NVIDIA RTX 3070 (8GB) | RTX 4090 (24GB) |
| RAM | 16GB | 64GB |
| Storage | 20GB free | 50GB+ SSD |
| CPU | Any modern 4-core | 8+ cores |

### Software Requirements

| Software | Version | Download |
|----------|---------|----------|
| Python | 3.11.x | [python.org](https://www.python.org/downloads/release/python-3119/) |
| Node.js | 18+ | [nodejs.org](https://nodejs.org/) |
| Git | Latest | [git-scm.com](https://git-scm.com/) |
| NVIDIA Driver | 525+ | [nvidia.com](https://www.nvidia.com/drivers) |

> **Warning**: Python 3.14 is NOT supported. Use Python 3.11 or 3.12.

---

## Step 1: Install Python 3.11

### Option A: Direct Download (Recommended)
1. Download Python 3.11.9 from: https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
2. Run installer
3. **Check "Add Python to PATH"**
4. Click "Install Now"

### Option B: Windows Store
1. Open Microsoft Store
2. Search "Python 3.11"
3. Install

### Verify Installation
```powershell
py -3.11 --version
# Should output: Python 3.11.x
```

---

## Step 2: Install Node.js

1. Download from: https://nodejs.org/ (LTS version)
2. Run installer with default options
3. Verify:
```powershell
node --version
# Should output: v18.x.x or higher

npm --version
# Should output: 9.x.x or higher
```

---

## Step 3: Install Git

1. Download from: https://git-scm.com/download/win
2. Run installer with default options
3. Verify:
```powershell
git --version
# Should output: git version 2.x.x
```

---

## Step 4: Verify NVIDIA Setup

```powershell
# Check GPU is detected
nvidia-smi
```

You should see your GPU model and driver version. Driver should be 525+.

---

## Step 5: Clone Repository

```powershell
# Navigate to desired location
cd C:\Claude  # or your preferred location

# Clone repository
git clone https://github.com/gnoobs75/Sweedle.git

# Enter directory
cd Sweedle
```

---

## Step 6: Backend Setup

### Automatic Setup (Windows)
```powershell
# Run setup script
.\setup.bat
```

This will:
1. Create Python virtual environment
2. Install all dependencies
3. Set up frontend (if Node.js found)

### Manual Setup

```powershell
# Navigate to backend
cd backend

# Create virtual environment with Python 3.11
py -3.11 -m venv venv

# Activate virtual environment
venv\Scripts\activate

# Upgrade pip
python -m pip install --upgrade pip

# Install PyTorch with CUDA 12.1
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# Install Hunyuan3D
pip install git+https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1.git

# Install remaining dependencies
pip install -r requirements.txt
```

### Verify PyTorch CUDA
```powershell
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"
```

Expected output:
```
CUDA available: True
Device: NVIDIA GeForce RTX 4090  # or your GPU
```

---

## Step 7: Frontend Setup

```powershell
# Navigate to frontend
cd ..\frontend  # from backend
# or
cd frontend     # from Sweedle root

# Install dependencies
npm install
```

---

## Step 8: First Run

### Option A: Using Start Scripts (Recommended)

```powershell
# From Sweedle root directory
.\start.bat
```

This starts both backend and frontend.

### Option B: Manual Start

**Terminal 1 - Backend:**
```powershell
cd backend
venv\Scripts\activate
uvicorn src.main:app --host 127.0.0.1 --port 8000
```

**Terminal 2 - Frontend:**
```powershell
cd frontend
npm run dev
```

### Access Application
Open browser to: http://localhost:5173

---

## Step 9: First Generation

The first generation will download the Hunyuan3D model (~8GB). This may take several minutes depending on your internet connection.

1. Open http://localhost:5173
2. Click "Simple" mode
3. Drag & drop or click to upload an image
4. Click "Generate 3D"
5. Wait for generation (watch progress bar)
6. View result in 3D viewer

---

## Troubleshooting

### "Python not found"

**Solution**: Install Python 3.11 and ensure it's in PATH.

```powershell
# Check if py launcher works
py -3.11 --version

# If not, add Python to PATH manually or reinstall
```

### "CUDA not available"

**Causes:**
- Wrong PyTorch version installed
- NVIDIA drivers outdated
- GPU not CUDA-capable

**Solution:**
```powershell
# Reinstall PyTorch with CUDA
pip uninstall torch torchvision
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

### "Model download failed"

**Causes:**
- Network issues
- Insufficient disk space
- Hugging Face rate limiting

**Solution:**
```powershell
# Clear cache and retry
Remove-Item -Recurse -Force "$env:USERPROFILE\.cache\huggingface\hub\models--tencent--Hunyuan3D-2.1"
```

### "onnxruntime error" or "Python version"

**Cause**: Using Python 3.14

**Solution**: Install and use Python 3.11:
```powershell
py -3.11 -m venv venv
```

### "CUDA out of memory"

**Solutions:**
1. Close other GPU applications
2. Reduce octree_resolution (try 128)
3. Enable LOW_VRAM_MODE in backend/.env
4. Restart backend to clear GPU memory

### "WebSocket connection failed"

**Cause**: Backend not running

**Solution**: Ensure backend is started before frontend.

### "Using mock mesh generation"

**Cause**: Hunyuan3D model not loaded properly

**Check logs for:**
- "Model loaded on CUDA device"
- "pipeline is None: False"

**If pipeline is None: True**, there was a loading error. Check for:
- CUDA availability
- Model file integrity
- Sufficient GPU memory

---

## Directory Structure After Setup

```
Sweedle/
├── backend/
│   ├── venv/                  # Python virtual environment
│   │   ├── Scripts/
│   │   │   ├── python.exe
│   │   │   └── pip.exe
│   │   └── Lib/site-packages/ # Installed packages
│   ├── storage/               # Created on first run
│   │   ├── uploads/
│   │   └── generated/
│   ├── data/                  # Created on first run
│   │   └── sweedle.db
│   └── src/
│
├── frontend/
│   └── node_modules/          # NPM packages
│
└── start.bat
```

---

## Model Cache Locations

Models are cached to avoid re-downloading:

| Model | Location | Size |
|-------|----------|------|
| Hunyuan3D | `~\.cache\huggingface\hub\models--tencent--Hunyuan3D-2.1\` | ~8GB |
| U2Net (rembg) | `~\.u2net\` | ~170MB |

To free space, you can delete these, but they'll re-download on next use.

---

## Updating Sweedle

```powershell
# Pull latest changes
cd C:\Claude\Sweedle
git pull

# Update backend dependencies
cd backend
venv\Scripts\activate
pip install -r requirements.txt

# Update frontend dependencies
cd ..\frontend
npm install
```

---

## Uninstalling

```powershell
# Remove Sweedle directory
Remove-Item -Recurse -Force C:\Claude\Sweedle

# Optional: Remove model caches
Remove-Item -Recurse -Force "$env:USERPROFILE\.cache\huggingface\hub\models--tencent--Hunyuan3D-2.1"
Remove-Item -Recurse -Force "$env:USERPROFILE\.cache\hy3dgen"
Remove-Item -Recurse -Force "$env:USERPROFILE\.u2net"
```

---

## Getting Help

- **GitHub Issues**: https://github.com/gnoobs75/Sweedle/issues
- **Hunyuan3D Issues**: https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1/issues
- **Check logs**: Run `start-backend-debug.bat` for detailed output
