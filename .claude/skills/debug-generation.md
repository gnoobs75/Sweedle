# /debug-generation

Diagnose why a generation failed.

## Usage
```
/debug-generation [job_id]
```

## Options
- `job_id`: Specific job ID to debug (optional - uses most recent failed job if not provided)

## Instructions

### 1. Find Failed Job
If no job_id provided, query the database for recent failed jobs:

```python
import sqlite3
conn = sqlite3.connect('C:/Claude/Sweedle/backend/data/sweedle.db')
cursor = conn.cursor()
cursor.execute("""
    SELECT id, asset_id, job_type, status, error_message, created_at
    FROM jobs
    WHERE status = 'failed'
    ORDER BY created_at DESC
    LIMIT 5
""")
for row in cursor.fetchall():
    print(row)
conn.close()
```

### 2. Get Job Details
```
GET http://localhost:8000/api/generation/jobs/{job_id}
```

### 3. Check Logs for Job
Search the log file for the job ID:
```powershell
Select-String -Path "C:\Claude\Sweedle\backend\sweedle.log" -Pattern "<job_id>" -Context 5,10
```

### 4. Common Failure Patterns

#### CUDA Out of Memory
Log pattern: `CUDA out of memory` or `RuntimeError: CUDA`
```
Cause: VRAM exhaustion during generation
Solutions:
1. Use /clear-vram before generation
2. Lower octree_resolution (256 instead of 384)
3. Disable texture generation
4. Close other GPU applications
```

#### Model Not Loaded
Log pattern: `pipeline is None: True`
```
Cause: Model failed to load at startup
Solutions:
1. Check /model-status for missing models
2. Restart backend with start-backend-debug.bat
3. Check disk space for model cache
```

#### Image Preprocessing Failed
Log pattern: `Background removal failed` or `rembg`
```
Cause: rembg/U2Net model issue
Solutions:
1. Check if image is valid (not corrupted)
2. Try different image format (PNG recommended)
3. Restart backend to reload rembg session
```

#### Texture Generation Failed
Log pattern: `Texture generation failed` or `custom_rasterizer`
```
Cause: Texture pipeline requires CUDA compilation
Solutions:
1. Texture is experimental - try with texture_enabled=false
2. Check CUDA toolkit installation
3. This may require building custom_rasterizer from source
```

#### Mesh Export Failed
Log pattern: `Mesh export failed` or `trimesh`
```
Cause: Generated mesh is invalid
Solutions:
1. Try different input image
2. Check if mesh has valid vertices/faces
3. Try different output format (GLB vs OBJ)
```

### 5. Report Format
```
Generation Debug Report
=======================
Job ID: <job_id>
Asset ID: <asset_id>
Status: <status>
Created: <timestamp>

Error
-----
<error_message>

Failure Category: [VRAM/Model/Preprocessing/Texture/Export/Unknown]

Root Cause Analysis
-------------------
<analysis based on log patterns>

Recommended Fix
---------------
1. <step 1>
2. <step 2>
3. <step 3>

Relevant Log Entries
--------------------
<last 10 log lines related to this job>
```

### 6. Auto-Recovery Suggestions
Based on error type, suggest:
- VRAM issues: `/clear-vram` then retry
- Model issues: Restart backend
- Image issues: Try different image
- Texture issues: Disable texture and retry
