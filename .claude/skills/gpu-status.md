# /gpu-status

Check GPU health, VRAM usage, and loaded models.

## Usage
```
/gpu-status
```

## Instructions

When this skill is invoked, perform the following checks:

### 1. Check GPU Hardware Status
Run this command to get GPU info:
```powershell
nvidia-smi --query-gpu=name,memory.total,memory.used,memory.free,temperature.gpu,utilization.gpu --format=csv,noheader,nounits
```

### 2. Check PyTorch VRAM Status
Read the current VRAM state by calling the backend API:
```
GET http://localhost:8000/api/device/stats
```

Or run Python directly:
```powershell
cd C:\Claude\Sweedle\backend
venv\Scripts\python.exe -c "import torch; print(f'CUDA Available: {torch.cuda.is_available()}'); print(f'Device: {torch.cuda.get_device_name(0)}'); print(f'Allocated: {torch.cuda.memory_allocated(0)/1e9:.2f}GB'); print(f'Reserved: {torch.cuda.memory_reserved(0)/1e9:.2f}GB'); print(f'Total: {torch.cuda.get_device_properties(0).total_memory/1e9:.2f}GB')"
```

### 3. Check Loaded Models
Check the backend health endpoint:
```
GET http://localhost:8000/health
```

### 4. Report Format
Present the results in this format:

```
GPU Status
----------
Device: NVIDIA GeForce RTX 4090
Temperature: XX°C
Utilization: XX%

VRAM Usage
----------
Allocated: X.XX GB / 24.00 GB (XX%)
Reserved:  X.XX GB
Free:      X.XX GB

Loaded Models
-------------
- Shape Pipeline: [Loaded/Not Loaded] (~21GB when loaded)
- Texture Pipeline: [Loaded/Not Loaded] (~18GB when loaded)
- rembg (U2Net): [Loaded/Not Loaded] (~170MB, CPU)

Backend Status
--------------
Worker: [Running/Stopped]
Queue Size: X
WebSocket Connections: X
```

### 5. Warnings
Flag any issues:
- VRAM > 90% = Warning: Low VRAM
- Temperature > 80°C = Warning: High temperature
- Worker not running = Error: Backend worker stopped
