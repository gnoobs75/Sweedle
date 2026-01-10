# /clear-cache

Clear model caches to free disk space or force re-download.

## Usage
```
/clear-cache [huggingface|hy3dgen|rembg|all]
```

## Options
- `huggingface`: Clear HuggingFace model cache (~40GB)
- `hy3dgen`: Clear hy3dgen local cache
- `rembg`: Clear U2Net model cache (~170MB)
- `all`: Clear all caches

## Instructions

### WARNING
Always warn the user before clearing:
```
WARNING: Clearing model caches will require re-downloading models on next use.
- HuggingFace cache: ~40GB download
- Models will be re-downloaded automatically on next generation
- This operation cannot be undone

Proceed? (The user must confirm)
```

### Clear HuggingFace Cache
```powershell
$hfCache = "$env:USERPROFILE\.cache\huggingface\hub"

# Show what will be deleted
$models = Get-ChildItem $hfCache -Directory | Where-Object { $_.Name -like "models--tencent--Hunyuan3D*" }
foreach ($model in $models) {
    $size = (Get-ChildItem $model.FullName -Recurse | Measure-Object -Property Length -Sum).Sum / 1GB
    Write-Host "$($model.Name): $([math]::Round($size, 2)) GB"
}

# Delete Hunyuan models only (preserve other cached models)
Remove-Item "$hfCache\models--tencent--Hunyuan3D-2.1" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "$hfCache\models--tencent--Hunyuan3D-2" -Recurse -Force -ErrorAction SilentlyContinue
```

### Clear hy3dgen Cache
```powershell
$hy3dCache = "$env:USERPROFILE\.cache\hy3dgen"
if (Test-Path $hy3dCache) {
    Remove-Item $hy3dCache -Recurse -Force
    Write-Host "Cleared hy3dgen cache"
}
```

### Clear rembg/U2Net Cache
```powershell
$u2netCache = "$env:USERPROFILE\.u2net"
if (Test-Path $u2netCache) {
    Remove-Item $u2netCache -Recurse -Force
    Write-Host "Cleared U2Net cache"
}
```

### Clear All
Run all three cache clears above.

### Report Format
```
Cache Clear Results
===================

Cleared:
- HuggingFace (Hunyuan3D models): XX.XX GB freed
- hy3dgen: XX.XX GB freed
- U2Net: XXX MB freed

Total Freed: XX.XX GB

Next Steps:
- Models will be re-downloaded on next generation
- First generation will take longer (~5-10 min for download)
- Ensure stable internet connection
```

### Post-Clear
After clearing, recommend restarting the backend:
```powershell
# Restart backend to reset model state
cd C:\Claude\Sweedle
.\start-backend-debug.bat
```
