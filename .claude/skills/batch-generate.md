# /batch-generate

Generate multiple 3D models from a folder of images.

## Usage
```
/batch-generate <folder_path> [--quality standard|high|draft] [--skip-existing] [--texture]
```

## Options
- `folder_path`: Path to folder containing images (required)
- `--quality`: Generation quality preset (default: standard)
  - `draft`: 20 steps, 192 octree (fastest)
  - `standard`: 30 steps, 256 octree
  - `high`: 50 steps, 384 octree (slowest)
- `--skip-existing`: Skip images that already have generated assets
- `--texture`: Enable texture generation (slower, more VRAM)

## Instructions

### 1. Validate Folder
Check that the folder exists and contains valid images:
```python
from pathlib import Path

folder = Path("<folder_path>")
if not folder.exists():
    print(f"Error: Folder not found: {folder}")
    exit(1)

# Find all images
image_extensions = {'.png', '.jpg', '.jpeg', '.webp', '.bmp'}
images = [f for f in folder.iterdir() if f.suffix.lower() in image_extensions]

print(f"Found {len(images)} images in {folder}")
for img in images:
    print(f"  - {img.name}")
```

### 2. Quality Presets
```python
PRESETS = {
    'draft': {'inference_steps': 20, 'octree_resolution': 192},
    'standard': {'inference_steps': 30, 'octree_resolution': 256},
    'high': {'inference_steps': 50, 'octree_resolution': 384},
}
```

### 3. Check for Existing Assets (if --skip-existing)
Query the database to find already-generated assets:
```python
import sqlite3
conn = sqlite3.connect('C:/Claude/Sweedle/backend/data/sweedle.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM assets WHERE status = 'completed'")
existing = {row[0] for row in cursor.fetchall()}
conn.close()

# Filter out existing
images = [img for img in images if img.stem not in existing]
```

### 4. Queue Generations
Submit each image to the generation API:
```python
import requests
import time

results = []
for i, image_path in enumerate(images):
    print(f"\n[{i+1}/{len(images)}] Processing: {image_path.name}")

    with open(image_path, 'rb') as f:
        response = requests.post(
            'http://localhost:8000/api/generation/image-to-3d',
            files={'image': f},
            data={
                'name': image_path.stem,
                'inference_steps': preset['inference_steps'],
                'octree_resolution': preset['octree_resolution'],
                'texture_enabled': texture_enabled,
            }
        )

    if response.status_code == 200:
        job_id = response.json()['job_id']
        results.append({'image': image_path.name, 'job_id': job_id, 'status': 'queued'})
        print(f"  Queued: {job_id}")
    else:
        results.append({'image': image_path.name, 'error': response.text, 'status': 'failed'})
        print(f"  Failed to queue: {response.text}")

    # Small delay to avoid overwhelming the API
    time.sleep(0.5)
```

### 5. Monitor Progress
Poll for job completion:
```python
pending = [r for r in results if r['status'] == 'queued']
while pending:
    for result in pending[:]:
        status = requests.get(f"http://localhost:8000/api/generation/jobs/{result['job_id']}").json()
        if status['status'] in ('completed', 'failed'):
            result['status'] = status['status']
            pending.remove(result)
            print(f"  {result['image']}: {status['status']}")
    if pending:
        time.sleep(5)
```

### 6. Report Format
```
Batch Generation Report
=======================
Folder: <folder_path>
Quality: <quality>
Texture: [Enabled/Disabled]

Images Found: X
Skipped (existing): Y
Processed: Z

Results
-------
[SUCCESS] image1.png -> asset_id_1 (XX seconds)
[SUCCESS] image2.png -> asset_id_2 (XX seconds)
[FAILED]  image3.png -> Error: <error message>

Summary
-------
Successful: X
Failed: Y
Total Time: XX minutes
Average Time: XX seconds per model
```

### 7. Error Handling
- If VRAM runs out, pause and run `/clear-vram` before continuing
- If backend crashes, restart and resume from failed images
- Keep a log of progress to allow resuming
