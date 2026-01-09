# /rig-asset

Auto-rig an existing 3D asset from the library with skeleton and weights.

## Usage

```
/rig-asset [asset_id] [--type humanoid|quadruped|auto] [--processor unirig|blender|auto]
```

## Arguments

- `asset_id` (optional): The UUID of the asset to rig. If not provided, uses the currently selected asset in the viewer.
- `--type`: Character type for rigging
  - `auto` (default): Automatically detect character type
  - `humanoid`: Force humanoid skeleton (65 bones)
  - `quadruped`: Force quadruped skeleton (45 bones)
- `--processor`: Rigging engine to use
  - `auto` (default): Auto-select best processor
  - `unirig`: ML-based rigging (faster, humanoids)
  - `blender`: Blender headless (more control, quadrupeds)

## Examples

```bash
# Rig the currently selected asset with auto-detection
/rig-asset

# Rig a specific asset
/rig-asset abc123-def456

# Force humanoid rigging
/rig-asset --type humanoid

# Use Blender processor for quadruped
/rig-asset abc123 --type quadruped --processor blender
```

## Instructions

When the user invokes this skill:

1. **Identify the asset**:
   - If `asset_id` is provided, use that
   - Otherwise, check the current viewer state for selected asset
   - If no asset selected, ask user to select one

2. **Start rigging job**:
   ```typescript
   // Call the rigging API
   const response = await fetch('/api/rigging/auto-rig', {
     method: 'POST',
     body: formData containing:
       - asset_id: string
       - character_type: 'auto' | 'humanoid' | 'quadruped'
       - processor: 'auto' | 'unirig' | 'blender'
       - priority: 'normal'
   });
   ```

3. **Monitor progress**:
   - WebSocket messages will broadcast progress
   - Stages: Loading mesh -> Analyzing character -> Creating skeleton -> Computing weights -> Exporting mesh

4. **Report completion**:
   - Show bone count and character type detected
   - Inform user they can toggle skeleton visibility in viewer

## API Reference

### POST /api/rigging/auto-rig

Request:
```json
{
  "asset_id": "uuid",
  "character_type": "auto",
  "processor": "auto",
  "priority": "normal"
}
```

Response:
```json
{
  "job_id": "uuid",
  "asset_id": "uuid",
  "status": "pending",
  "message": "Rigging job submitted",
  "queue_position": 1
}
```

### WebSocket Messages

```json
{
  "type": "rigging_progress",
  "job_id": "uuid",
  "progress": 0.45,
  "stage": "Creating skeleton...",
  "detected_type": "humanoid"
}
```

```json
{
  "type": "rigging_complete",
  "asset_id": "uuid",
  "character_type": "humanoid",
  "bone_count": 65
}
```

## Troubleshooting

- **"Asset not found"**: Verify the asset_id exists in the library
- **"Asset not completed"**: Wait for 3D generation to finish first
- **"Rigging failed"**: Run `/debug-rigging` to diagnose issues
- **Slow rigging**: Large meshes (>100k vertices) take longer; consider decimation first
