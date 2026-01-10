# /model-status

Check status of all AI models (loaded, cached, missing).

## Usage
```
/model-status
```

## Instructions

### 1. Check Model Cache Locations

#### Hugging Face Cache
```powershell
$hfCache = "$env:USERPROFILE\.cache\huggingface\hub"
if (Test-Path $hfCache) {
    $size = (Get-ChildItem $hfCache -Recurse | Measure-Object -Property Length -Sum).Sum / 1GB
    Write-Host "HuggingFace Cache: $([math]::Round($size, 2)) GB"
    Get-ChildItem $hfCache -Directory | Select-Object Name
}
```

#### hy3dgen Cache
```powershell
$hy3dCache = "$env:USERPROFILE\.cache\hy3dgen"
if (Test-Path $hy3dCache) {
    $size = (Get-ChildItem $hy3dCache -Recurse | Measure-Object -Property Length -Sum).Sum / 1GB
    Write-Host "hy3dgen Cache: $([math]::Round($size, 2)) GB"
}
```

#### rembg/U2Net Cache
```powershell
$u2netCache = "$env:USERPROFILE\.u2net"
if (Test-Path $u2netCache) {
    $size = (Get-ChildItem $u2netCache -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
    Write-Host "U2Net Cache: $([math]::Round($size, 2)) MB"
}
```

### 2. Check Required Models

#### Hunyuan3D-2.1 (Shape)
Expected path: `~\.cache\huggingface\hub\models--tencent--Hunyuan3D-2.1\`
Required files:
- `hunyuan3d-dit-v2-1/model.fp16.ckpt` (~21GB)

#### Hunyuan3D-2 (Texture)
Expected path: `~\.cache\huggingface\hub\models--tencent--Hunyuan3D-2\`
Required files:
- `hunyuan3d-paint-v2-0-turbo/` (~18GB)

#### U2Net (Background Removal)
Expected path: `~\.u2net\u2net.onnx`
Size: ~170MB

### 3. Check Runtime Status
Call backend to check if models are loaded in memory:
```
GET http://localhost:8000/health
GET http://localhost:8000/api/device/info
```

### 4. Report Format
```
Model Status
============

Hunyuan3D-2.1 (Shape Generation)
--------------------------------
Cache: [Found/Missing] at ~/.cache/huggingface/hub/models--tencent--Hunyuan3D-2.1
Size: XX.XX GB
Runtime: [Loaded on GPU/Loaded on CPU/Not Loaded]
VRAM Usage: ~21GB when loaded

Hunyuan3D-2 (Texture Generation)
--------------------------------
Cache: [Found/Missing] at ~/.cache/huggingface/hub/models--tencent--Hunyuan3D-2
Size: XX.XX GB
Runtime: [Loaded on GPU/Loaded on CPU/Not Loaded]
VRAM Usage: ~18GB when loaded

U2Net (Background Removal)
--------------------------
Cache: [Found/Missing] at ~/.u2net/u2net.onnx
Size: XXX MB
Runtime: [Loaded/Not Loaded] (CPU-based via ONNX)

Total Cache Size: XX.XX GB
Total VRAM Required: ~21GB (shape) or ~18GB (texture) - swapped dynamically
```

### 5. Recommendations
- If models missing: Provide download instructions
- If cache too large: Suggest `/clear-cache` to free space
- If models not loading: Check logs with `/watch-logs`
