# /debug-rigging

Debug rigging pipeline issues and verify system configuration.

## Usage

```
/debug-rigging [--check-all] [--job job_id]
```

## Arguments

- `--check-all`: Run all diagnostic checks
- `--job job_id`: Debug a specific failed rigging job

## Examples

```bash
# Run all diagnostics
/debug-rigging --check-all

# Debug a specific job failure
/debug-rigging --job abc123-def456
```

## Instructions

When the user invokes this skill:

### 1. System Checks

Run these diagnostic checks:

```python
# Check UniRig availability
- Verify unirig model path exists
- Check if scipy is installed (for weight calculation)
- Test mesh loading capability

# Check Blender availability
- Verify Blender executable path
- Test Blender version (needs 4.x)
- Run simple Blender script test

# Check GPU/CUDA
- Verify CUDA is available for PyTorch
- Check GPU memory availability
- Test tensor operations on GPU
```

### 2. Backend Health Check

```bash
# Check rigging service is running
curl http://localhost:8000/api/rigging/templates
```

Expected response:
```json
{
  "templates": [
    {"name": "humanoid_standard", "character_type": "humanoid", "bone_count": 65},
    {"name": "quadruped_standard", "character_type": "quadruped", "bone_count": 45}
  ]
}
```

### 3. Recent Job Analysis

If checking a specific job or recent failures:

```bash
# Get job status
curl http://localhost:8000/api/rigging/jobs/{job_id}
```

Check for common errors:
- `"Mesh file not found"`: Asset GLB missing or corrupted
- `"Failed to load mesh"`: GLB format issue, try re-generating
- `"Character type detection failed"`: Mesh too complex or unusual shape
- `"Weight calculation timeout"`: Mesh too large, need decimation
- `"Blender not found"`: Install Blender and configure path

### 4. Configuration Verification

Check these settings in `backend/src/rigging/config.py`:

```python
UNIRIG_MODEL_PATH = "models/unirig"  # ML model location
BLENDER_PATH = "blender"             # Blender executable
MAX_VERTICES_FOR_UNIRIG = 100000     # Vertex limit
ENABLE_FBX_EXPORT = True             # FBX export toggle
DEFAULT_PROCESSOR = "auto"           # Default processor
```

### 5. Log Analysis

Check backend logs for rigging-related entries:

```bash
# Look for rigging errors in recent logs
grep -i "rigging\|rig_asset\|skeleton" backend/logs/*.log
```

Common log patterns:
- `"Starting rig_asset job"`: Job started successfully
- `"Character type detected: humanoid"`: Detection working
- `"Skeleton created with X bones"`: Skeleton generation OK
- `"Weight calculation complete"`: Weights computed
- `"Rigging complete"`: Full success

### 6. Report Format

Output a diagnostic report:

```
=== Rigging System Diagnostics ===

System Status:
  UniRig:     [OK] Model loaded
  Blender:    [OK] v4.0.2 found at /usr/bin/blender
  CUDA:       [OK] GPU available (RTX 3080)

Configuration:
  Max vertices:    100,000
  FBX export:      Enabled
  Default proc:    auto

Recent Jobs (last 5):
  job_abc123: completed - humanoid (65 bones)
  job_def456: completed - quadruped (45 bones)
  job_ghi789: failed - "Mesh file not found"

Recommendations:
  - All systems operational
  - Or: Install Blender for quadruped support
  - Or: Reduce mesh complexity before rigging
```

## Troubleshooting Common Issues

### UniRig Not Working
1. Check scipy is installed: `pip install scipy`
2. Verify model path in config
3. Check GPU memory (needs ~4GB for large meshes)

### Blender Not Found
1. Install Blender 4.x from blender.org
2. Add to system PATH, or
3. Set `BLENDER_PATH` environment variable

### Weight Calculation Slow
1. Decimate mesh first (reduce to <50k vertices)
2. Use LOD system to create lighter version
3. Increase worker timeout if needed

### FBX Export Fails
1. Requires Blender (not just UniRig)
2. Check Blender script permissions
3. Verify output directory is writable
