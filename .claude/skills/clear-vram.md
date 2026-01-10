# /clear-vram

Force clear GPU memory when stuck or before heavy operations.

## Usage
```
/clear-vram [--full]
```

## Options
- Default: Empty CUDA cache and run garbage collection
- `--full`: Unload all models completely and reinitialize pipeline

## Instructions

### Default Mode (Cache Clear)

1. Create a temporary Python script to clear VRAM:
```python
import gc
import torch

if torch.cuda.is_available():
    # Synchronize to ensure all operations complete
    torch.cuda.synchronize()

    # Get before stats
    before = torch.cuda.memory_allocated(0) / 1e9

    # Force garbage collection
    gc.collect()
    gc.collect()
    gc.collect()

    # Clear CUDA cache
    torch.cuda.empty_cache()

    # IPC collect if available
    if hasattr(torch.cuda, 'ipc_collect'):
        torch.cuda.ipc_collect()

    # Synchronize again
    torch.cuda.synchronize()

    # Get after stats
    after = torch.cuda.memory_allocated(0) / 1e9

    print(f"VRAM Before: {before:.2f}GB")
    print(f"VRAM After:  {after:.2f}GB")
    print(f"Freed:       {before - after:.2f}GB")
else:
    print("CUDA not available")
```

2. Run it:
```powershell
cd C:\Claude\Sweedle\backend
venv\Scripts\python.exe -c "<script above>"
```

### Full Mode (--full)

1. The backend must be restarted to fully unload models. Warn the user:
   - "This will restart the backend and take ~30 seconds to reload models."

2. If user confirms, stop and restart the backend:
```powershell
# The user should close the current backend terminal
# Then restart with:
cd C:\Claude\Sweedle
.\start-backend-debug.bat
```

3. Alternatively, call the cleanup endpoint (if implemented):
```
POST http://localhost:8000/api/device/cleanup
```

### Report Format
```
VRAM Clear Results
------------------
Before: X.XX GB allocated
After:  X.XX GB allocated
Freed:  X.XX GB

Status: [Success/Partial - some memory still held]
```

### Troubleshooting
If VRAM doesn't clear fully:
- Models may still be loaded in memory
- Use `--full` to completely restart
- Check for other processes using GPU: `nvidia-smi`
