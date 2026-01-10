# /gpu-benchmark

Run a quick benchmark to test generation speed and GPU performance.

## Usage
```
/gpu-benchmark [--quality standard|high]
```

## Options
- `--quality standard` (default): 30 steps, 256 octree
- `--quality high`: 50 steps, 384 octree

## Instructions

### 1. Check Backend is Running
```
GET http://localhost:8000/health
```
If not running, inform user to start backend first.

### 2. Create Benchmark Image
Create a simple test image (solid color square):
```python
from PIL import Image
img = Image.new('RGBA', (512, 512), (128, 128, 128, 255))
img.save('benchmark_input.png')
```

### 3. Run Benchmark Generation
Call the generation API with timing:

```python
import requests
import time

# Upload and generate
start = time.time()

with open('benchmark_input.png', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/api/generation/image-to-3d',
        files={'image': f},
        data={
            'name': 'Benchmark Test',
            'inference_steps': 30,  # or 50 for high
            'octree_resolution': 256,  # or 384 for high
            'texture_enabled': False,  # Skip texture for benchmark
        }
    )

job_id = response.json()['job_id']

# Poll for completion
while True:
    status = requests.get(f'http://localhost:8000/api/generation/jobs/{job_id}').json()
    if status['status'] in ('completed', 'failed'):
        break
    time.sleep(1)

total_time = time.time() - start
```

### 4. Collect Metrics
- Total generation time
- Peak VRAM usage during generation
- GPU utilization during generation

### 5. Report Format
```
GPU Benchmark Results
=====================
Quality: [Standard/High]
Test: Gray cube generation (no texture)

Timing
------
Preprocessing:  X.XX s
Shape Generation: XX.XX s
Post-processing: X.XX s
Total: XX.XX s

Performance
-----------
Peak VRAM: XX.XX GB
GPU Utilization: XX%
Inference Speed: X.XX steps/sec

Comparison
----------
Expected (RTX 4090): ~60s standard, ~90s high
Your Result: [Faster/Normal/Slower] than expected

Hardware
--------
GPU: NVIDIA GeForce RTX 4090
CUDA: 12.x
PyTorch: 2.x
```

### 6. Cleanup
Delete the benchmark test asset after completion to avoid clutter.
