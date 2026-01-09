# /export-rigged

Export a rigged 3D model to game engine-compatible format.

## Usage

```
/export-rigged [asset_id] [--format glb|fbx] [--engine unity|unreal|godot]
```

## Arguments

- `asset_id` (optional): The UUID of the rigged asset. If not provided, uses currently selected asset.
- `--format`: Export format
  - `glb` (default): GLTF Binary - universal, smaller file size
  - `fbx`: Autodesk FBX - better Unity/Unreal compatibility
- `--engine`: Target game engine (applies engine-specific settings)
  - `unity`: Unity-optimized settings (Y-up, -Z forward)
  - `unreal`: Unreal-optimized settings (Z-up, X forward)
  - `godot`: Godot-optimized settings (Y-up, -Z forward)

## Examples

```bash
# Export current asset as GLB
/export-rigged

# Export specific asset as FBX for Unity
/export-rigged abc123 --format fbx --engine unity

# Export for Unreal Engine
/export-rigged --format fbx --engine unreal
```

## Instructions

When the user invokes this skill:

### 1. Verify Asset is Rigged

```typescript
// Check asset has rigging data
const asset = await fetch(`/api/assets/${assetId}`);
if (!asset.is_rigged) {
  // Prompt user to rig first
  console.log("Asset is not rigged. Run /rig-asset first.");
  return;
}
```

### 2. Prepare Export Request

```typescript
const exportRequest = {
  asset_id: assetId,
  format: format,        // 'glb' or 'fbx'
  engine: engine,        // 'unity', 'unreal', or 'godot'
  include_skeleton: true,
  include_weights: true,
  optimize_for_realtime: true
};
```

### 3. Call Export API

```bash
# For GLB export (built-in)
POST /api/export/engine
{
  "asset_id": "uuid",
  "format": "glb",
  "engine": "unity"
}

# For FBX export (requires Blender)
POST /api/rigging/export-fbx
{
  "asset_id": "uuid",
  "engine": "unity"
}
```

### 4. Engine-Specific Settings

#### Unity Export Settings
```json
{
  "coordinate_system": "y_up",
  "forward_axis": "-z",
  "scale_factor": 1.0,
  "bone_naming": "mixamo_compatible",
  "embed_textures": true
}
```

#### Unreal Export Settings
```json
{
  "coordinate_system": "z_up",
  "forward_axis": "x",
  "scale_factor": 100.0,
  "bone_naming": "ue_compatible",
  "embed_textures": true
}
```

#### Godot Export Settings
```json
{
  "coordinate_system": "y_up",
  "forward_axis": "-z",
  "scale_factor": 1.0,
  "bone_naming": "standard",
  "embed_textures": true
}
```

### 5. Download/Save File

After export completes:
```typescript
// Get download URL
const downloadUrl = `/api/assets/${assetId}/download?format=${format}`;

// Or save to specific location
const savePath = `exports/${assetName}_rigged.${format}`;
```

### 6. Report Results

```
Export Complete!

File: character_rigged.fbx
Size: 2.4 MB
Format: FBX (Unity optimized)

Skeleton Info:
  Type: Humanoid
  Bones: 65
  Root: Hips

Import Instructions (Unity):
  1. Drag FBX into Assets folder
  2. Select file, go to Rig tab
  3. Set Animation Type to "Humanoid"
  4. Click "Configure" to verify bone mapping
  5. Apply changes

The model is ready for Mecanim animations!
```

## Format Comparison

| Feature | GLB | FBX |
|---------|-----|-----|
| File size | Smaller | Larger |
| Compression | DRACO support | Limited |
| Unity support | Good | Excellent |
| Unreal support | Good | Excellent |
| Godot support | Excellent | Good |
| Animation | Basic | Full |
| Blend shapes | Yes | Yes |
| PBR materials | Native | Converted |

## Troubleshooting

### "Asset not rigged"
Run `/rig-asset` first to add skeleton and weights.

### "FBX export failed"
- FBX requires Blender to be installed
- Run `/debug-rigging` to check Blender path
- Try GLB format as alternative

### "Skeleton not recognized in Unity"
- Check bone naming matches Humanoid standard
- Use "Configure" in Unity to manually map bones
- Ensure T-pose is correct

### "Model scaled wrong in Unreal"
- Unreal uses centimeters (scale 100x)
- Use `--engine unreal` flag for correct scaling
- Check "Import Uniform Scale" in Unreal

### "Textures missing"
- Ensure textures were generated with original model
- Check "Embed Textures" option is enabled
- For FBX, textures should be in same folder
