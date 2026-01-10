# /generate-production

Generate with maximum quality settings for production use.

## Usage
```
/generate-production <image_path> [name] [--texture] [--high-poly]
```

## Parameters
- `image_path`: Path to input image (required)
- `name`: Asset name (optional, defaults to filename)
- `--texture`: Enable texture generation (requires more VRAM)
- `--high-poly`: Use higher polygon count (50k+ faces)

## Settings
This preset uses maximum quality settings:
- Inference Steps: 50 (vs 30 standard)
- Octree Resolution: 384 (vs 256 standard)
- Guidance Scale: 7.0 (vs 5.5 standard)
- Texture: Optional (adds ~2-3 minutes)
- Expected Time: ~90-120 seconds on RTX 4090 (without texture)

## Instructions

### 1. Pre-flight Checks
```python
import requests

# Check GPU status
stats = requests.get('http://localhost:8000/api/device/stats').json()
if stats.get('gpu'):
    vram_percent = stats['gpu'].get('vram_percent', 0)
    if vram_percent > 50:
        print(f"Warning: VRAM at {vram_percent}% - consider /clear-vram first")

# Check queue
health = requests.get('http://localhost:8000/health').json()
queue_size = health.get('queue_size', 0)
if queue_size > 0:
    print(f"Note: {queue_size} jobs in queue ahead of this one")
```

### 2. Validate Image
```python
from pathlib import Path
from PIL import Image

image_path = Path("<image_path>")
if not image_path.exists():
    print(f"Error: Image not found: {image_path}")
    exit(1)

img = Image.open(image_path)
print(f"Image: {image_path.name} ({img.size[0]}x{img.size[1]}, {img.mode})")

# Recommend PNG with transparency for best results
if img.mode != 'RGBA':
    print("Tip: PNG with transparent background produces best results")
```

### 3. Submit Generation
```python
import requests
import time

start_time = time.time()
name = "<provided_name>" if "<provided_name>" else image_path.stem

# Production settings
settings = {
    'name': name,
    'inference_steps': 50,
    'octree_resolution': 384,
    'guidance_scale': 7.0,
    'texture_enabled': <texture_flag>,
    'face_count': 100000 if <high_poly_flag> else 50000,
}

print(f"Starting production generation...")
print(f"  Quality: Maximum (50 steps, 384 octree)")
print(f"  Texture: {'Enabled' if settings['texture_enabled'] else 'Disabled'}")
print(f"  Target Faces: {settings['face_count']:,}")

with open(image_path, 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/generation/image-to-3d',
        files={'image': f},
        data=settings
    )

if response.status_code != 200:
    print(f"Error: {response.text}")
    exit(1)

result = response.json()
job_id = result['job_id']
asset_id = result['asset_id']
```

### 4. Monitor Progress with Detailed Updates
```python
last_stage = ""
while True:
    status = requests.get(f'http://localhost:8000/api/generation/jobs/{job_id}').json()
    progress = status.get('progress', 0)
    message = status.get('progress_message', '')

    # Track stages
    if 'Preprocessing' in message and last_stage != 'preprocess':
        print("\n[Stage 1/4] Preprocessing image...")
        last_stage = 'preprocess'
    elif 'shape' in message.lower() and last_stage != 'shape':
        print("\n[Stage 2/4] Generating 3D shape (this takes ~60-90s)...")
        last_stage = 'shape'
    elif 'texture' in message.lower() and last_stage != 'texture':
        print("\n[Stage 3/4] Generating texture (this takes ~60-90s)...")
        last_stage = 'texture'
    elif 'Saving' in message and last_stage != 'save':
        print("\n[Stage 4/4] Saving mesh...")
        last_stage = 'save'

    print(f"\r  Progress: {progress*100:.0f}% - {message}", end='', flush=True)

    if status['status'] == 'completed':
        elapsed = time.time() - start_time
        print(f"\n\nGeneration complete in {elapsed/60:.1f} minutes")
        break
    elif status['status'] == 'failed':
        print(f"\n\nGeneration failed: {status.get('error_message', 'Unknown error')}")
        print("Try: /debug-generation " + job_id)
        exit(1)

    time.sleep(2)
```

### 5. Report Result
```python
asset = requests.get(f'http://localhost:8000/api/assets/{asset_id}').json()

print(f"""
Production Generation Complete
==============================
Name: {asset['name']}
Asset ID: {asset_id}

Quality
-------
Vertices: {asset.get('vertex_count', 'N/A'):,}
Faces: {asset.get('face_count', 'N/A'):,}
Textured: {'Yes' if asset.get('has_texture') else 'No'}

Files
-----
Mesh: {asset['mesh_path']}
Thumbnail: {asset.get('thumbnail_path', 'N/A')}

Time: {(time.time() - start_time)/60:.1f} minutes

View: http://localhost:5173/assets/{asset_id}

Next Steps
----------
- /rig-asset {asset_id} - Add skeleton for animation
- /batch-export --format fbx - Export for game engine
""")
```

### VRAM Requirements
- Shape only: ~21GB VRAM
- Shape + Texture: ~21GB → swap → ~18GB (sequential)
- High-poly mode: Same VRAM, more processing time

### Tips for Best Results
1. Use PNG with transparent background
2. Front-facing, centered subject
3. Good lighting, no harsh shadows
4. Clear silhouette
5. Simple, solid colors work better than complex patterns
