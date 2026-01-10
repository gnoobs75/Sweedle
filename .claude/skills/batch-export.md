# /batch-export

Export multiple assets to game engine format.

## Usage
```
/batch-export [--format glb|fbx|obj] [--engine unity|unreal|godot] [--filter <query>] [--output <folder>]
```

## Options
- `--format`: Export format (default: glb)
  - `glb`: GL Binary (universal, recommended)
  - `fbx`: Autodesk FBX (Unity/Unreal preferred)
  - `obj`: Wavefront OBJ (legacy support)
- `--engine`: Apply engine-specific optimizations
  - `unity`: Y-up, 0.01 scale
  - `unreal`: Z-up, 1.0 scale
  - `godot`: Y-up, 1.0 scale
- `--filter`: Filter assets (see filter syntax below)
- `--output`: Output folder (default: `./exports/<timestamp>/`)

## Filter Syntax
- `tag:character` - Assets with tag "character"
- `name:hero*` - Assets with name starting with "hero"
- `status:completed` - Only completed assets
- `rigged:true` - Only rigged assets

## Instructions

### 1. Query Assets
Get list of assets to export:
```python
import sqlite3
import json

conn = sqlite3.connect('C:/Claude/Sweedle/backend/data/sweedle.db')
cursor = conn.cursor()

# Base query
query = "SELECT id, name, mesh_path, is_rigged FROM assets WHERE status = 'completed'"

# Apply filters
if filter_tag:
    query += f" AND id IN (SELECT asset_id FROM asset_tags WHERE tag = '{filter_tag}')"
if filter_name:
    query += f" AND name LIKE '{filter_name.replace('*', '%')}'"
if filter_rigged:
    query += " AND is_rigged = 1"

cursor.execute(query)
assets = cursor.fetchall()
conn.close()

print(f"Found {len(assets)} assets to export")
```

### 2. Create Output Directory
```python
from pathlib import Path
from datetime import datetime

output_dir = Path(output_folder) if output_folder else Path(f"./exports/{datetime.now().strftime('%Y%m%d_%H%M%S')}")
output_dir.mkdir(parents=True, exist_ok=True)
```

### 3. Export Each Asset
```python
import requests
import shutil

results = []
for asset_id, name, mesh_path, is_rigged in assets:
    print(f"\nExporting: {name}")

    # Use the export API if available
    if format == 'fbx' and is_rigged:
        # FBX export for rigged models
        response = requests.post(
            f'http://localhost:8000/api/export/fbx',
            json={
                'asset_id': asset_id,
                'engine': engine,
            }
        )
        if response.status_code == 200:
            export_path = response.json()['path']
            # Copy to output folder
            shutil.copy(export_path, output_dir / f"{name}.fbx")
            results.append({'name': name, 'status': 'success', 'format': 'fbx'})
        else:
            results.append({'name': name, 'status': 'failed', 'error': response.text})
    else:
        # Direct file copy for GLB/OBJ
        src_path = Path(f"C:/Claude/Sweedle/backend/{mesh_path}")
        if src_path.exists():
            dst_name = f"{name}.{format}"
            shutil.copy(src_path, output_dir / dst_name)
            results.append({'name': name, 'status': 'success', 'format': format})
        else:
            results.append({'name': name, 'status': 'failed', 'error': 'Mesh file not found'})
```

### 4. Apply Engine-Specific Transforms
For Unity:
- Scale: 0.01 (Unity uses meters, models are in cm)
- Axis: Y-up (default)

For Unreal:
- Scale: 1.0
- Axis: Z-up (convert from Y-up)

For Godot:
- Scale: 1.0
- Axis: Y-up (default)

### 5. Report Format
```
Batch Export Report
===================
Output: <output_folder>
Format: <format>
Engine: <engine>
Filter: <filter or "all">

Assets Exported: X/Y

Results
-------
[SUCCESS] character_hero.glb (1.2 MB)
[SUCCESS] prop_sword.glb (0.3 MB)
[FAILED]  character_enemy -> Error: Mesh file not found

Summary
-------
Successful: X
Failed: Y
Total Size: XX.X MB
Output Folder: <full path>
```

### 6. Post-Export
Suggest next steps:
- For Unity: Import folder into Assets/
- For Unreal: Import to Content Browser
- For Godot: Import to res://models/
