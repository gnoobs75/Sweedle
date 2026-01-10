# /generate-quick

Generate with fast/draft settings for quick iteration.

## Usage
```
/generate-quick <image_path> [name]
```

## Parameters
- `image_path`: Path to input image (required)
- `name`: Asset name (optional, defaults to filename)

## Settings
This preset uses minimal settings for fastest generation:
- Inference Steps: 20 (vs 30 standard)
- Octree Resolution: 192 (vs 256 standard)
- Texture: Disabled
- Expected Time: ~30-40 seconds on RTX 4090

## Instructions

### 1. Validate Image
```python
from pathlib import Path
from PIL import Image

image_path = Path("<image_path>")
if not image_path.exists():
    print(f"Error: Image not found: {image_path}")
    exit(1)

# Validate it's a valid image
try:
    img = Image.open(image_path)
    print(f"Image: {image_path.name} ({img.size[0]}x{img.size[1]}, {img.mode})")
except Exception as e:
    print(f"Error: Invalid image: {e}")
    exit(1)
```

### 2. Generate Asset Name
```python
name = "<provided_name>" if "<provided_name>" else image_path.stem
# Clean name (remove special characters)
name = ''.join(c if c.isalnum() or c in ' _-' else '_' for c in name)
```

### 3. Submit Generation
```python
import requests
import time

start_time = time.time()

with open(image_path, 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/generation/image-to-3d',
        files={'image': f},
        data={
            'name': name,
            'inference_steps': 20,
            'octree_resolution': 192,
            'texture_enabled': False,
        }
    )

if response.status_code != 200:
    print(f"Error: {response.text}")
    exit(1)

result = response.json()
job_id = result['job_id']
asset_id = result['asset_id']
print(f"Job started: {job_id}")
print(f"Asset ID: {asset_id}")
```

### 4. Monitor Progress
```python
while True:
    status = requests.get(f'http://localhost:8000/api/generation/jobs/{job_id}').json()
    progress = status.get('progress', 0)
    message = status.get('progress_message', '')

    print(f"\r[{'='*int(progress*20):20s}] {progress*100:.0f}% - {message}", end='', flush=True)

    if status['status'] == 'completed':
        print(f"\n\nGeneration complete in {time.time() - start_time:.1f}s")
        break
    elif status['status'] == 'failed':
        print(f"\n\nGeneration failed: {status.get('error_message', 'Unknown error')}")
        exit(1)

    time.sleep(1)
```

### 5. Report Result
```python
# Get asset details
asset = requests.get(f'http://localhost:8000/api/assets/{asset_id}').json()

print(f"""
Quick Generation Complete
=========================
Name: {asset['name']}
Asset ID: {asset_id}
Mesh: {asset['mesh_path']}
Vertices: {asset.get('vertex_count', 'N/A')}
Faces: {asset.get('face_count', 'N/A')}
Time: {time.time() - start_time:.1f}s

View in browser: http://localhost:5173/assets/{asset_id}
""")
```

### When to Use
- Rapid prototyping and iteration
- Testing if an image will work well
- Generating placeholder assets
- When you need many quick assets

### Upgrade Path
If the quick result looks good, use `/generate-production` for final quality.
