# Sweedle Development Roadmap

This document outlines the planned features and enhancements for Sweedle, organized into phases with technical implementation details.

---

## Current State (v1.0.0)

### Implemented Features
- Image-to-3D generation via Hunyuan3D-2.1
- Real-time WebSocket progress updates
- Asset library with search, filter, tag
- Simple and Advanced generation modes
- GLB export format
- 3D viewer with orbit controls
- Background removal preprocessing

### Known Limitations
- Texture generation disabled (requires custom_rasterizer)
- No thumbnail generation (pyglet dependency)
- Single-threaded GPU processing
- No mesh post-processing
- No rigging or animation

---

## Phase 1: Core Improvements

**Timeline**: Next priority
**Goal**: Stabilize and enhance existing functionality

### 1.1 Enable Texture Generation
**Complexity**: High
**Dependencies**: CUDA compilation environment

The Hunyuan3D texture pipeline requires a custom CUDA rasterizer module.

**Implementation Steps:**
1. Set up CUDA development environment
2. Compile `custom_rasterizer` module from hy3dgen
3. Update `pipeline.py` to enable texture generation
4. Add texture resolution parameter
5. Test with various input images

**Files to Modify:**
- `backend/src/inference/pipeline.py` - Enable `_generate_texture` method
- `backend/src/inference/config.py` - Add texture parameters

### 1.2 Thumbnail Generation
**Complexity**: Low
**Dependencies**: Software renderer or alternative

**Options:**
1. Use `trimesh.Scene.save_image()` with osmesa (headless)
2. Generate thumbnails from first frame of viewer
3. Use pyrender with EGL backend

**Implementation:**
```python
# Option 1: trimesh with offscreen rendering
import trimesh
mesh = trimesh.load(path)
scene = trimesh.Scene(mesh)
png = scene.save_image(resolution=(256, 256), visible=True)
```

### 1.3 Batch Processing Improvements
**Complexity**: Medium

**Features:**
- Folder import for bulk generation
- Progress tracking per job
- Estimated time remaining
- Priority queue management
- Pause/resume queue

**Implementation:**
- Add `FolderImporter` component (exists, enhance)
- Improve queue status WebSocket messages
- Add time estimation based on previous jobs

---

## Phase 2: Mesh Enhancement

**Timeline**: After Phase 1
**Goal**: Improve output mesh quality

### 2.1 Mesh Smoothing
**Complexity**: Low
**Library**: trimesh, pymeshlab

Apply Laplacian or Taubin smoothing to reduce noise.

```python
import trimesh

mesh = trimesh.load(path)
# Laplacian smoothing
trimesh.smoothing.filter_laplacian(mesh, iterations=3)
mesh.export('smoothed.glb')
```

**UI Addition:**
- Smoothing iterations slider (0-10)
- Preview before/after

### 2.2 Mesh Decimation (Simplification)
**Complexity**: Low
**Library**: trimesh, pymeshlab

Reduce polygon count while preserving shape.

```python
# Quadric decimation
simplified = mesh.simplify_quadric_decimation(target_faces)
```

**Already Partially Implemented** in `pipeline.py:360`

**Enhancement:**
- Expose as separate post-processing step
- Multiple quality presets
- Face count targeting

### 2.3 Mesh Repair
**Complexity**: Medium
**Library**: trimesh, pymeshlab

Fix common mesh issues:
- Non-manifold edges
- Holes
- Self-intersections
- Degenerate faces

```python
import pymeshlab
ms = pymeshlab.MeshSet()
ms.load_new_mesh(path)
ms.meshing_repair_non_manifold_edges()
ms.meshing_close_holes()
ms.save_current_mesh('repaired.glb')
```

### 2.4 UV Unwrapping
**Complexity**: High
**Library**: xatlas, blender (via subprocess)

Improve UV mapping for textures.

**Options:**
1. **xatlas** - C++ library with Python bindings
2. **Blender** - Call via command line
3. **Smart UV Project** - Built into some mesh libraries

```python
# xatlas approach
import xatlas
atlas = xatlas.Atlas()
atlas.add_mesh(vertices, indices)
atlas.generate()
vmapping, indices, uvs = atlas.get_mesh(0)
```

### 2.5 Normal Map Generation
**Complexity**: Medium
**Library**: Custom implementation or existing tools

Generate normal maps from high-poly to low-poly.

**Implementation:**
1. Keep high-poly version before decimation
2. Bake normals from high to low
3. Save as texture alongside model

---

## Phase 3: Auto-Rigging

**Timeline**: After Phase 2
**Goal**: Automatically add skeletons to humanoid models

### 3.1 Skeleton Detection
**Complexity**: High
**Libraries**: Open-source rigging models, custom ML

Detect if mesh is humanoid and identify body parts.

**Approaches:**
1. **RigNet** - Deep learning for skeleton prediction
2. **Mixamo** - Online service (API integration)
3. **Pinocchio** - Classical algorithm

**RigNet Implementation:**
```python
# RigNet inference
from rignet import RigNet

model = RigNet.load_pretrained()
skeleton = model.predict(mesh_vertices)
```

### 3.2 Automatic Bone Placement
**Complexity**: High

Once body parts detected, place bones appropriately:
- Spine hierarchy
- Limb chains (arm, leg)
- Hand/foot bones
- Head/neck

**Output Format:**
- GLTF skeleton
- FBX skeleton
- Unity/Unreal compatible

### 3.3 Automatic Weight Painting
**Complexity**: High
**Libraries**: RigNet, custom algorithms

Assign vertex weights to bones.

**Approaches:**
1. **Heat diffusion** - Classic algorithm
2. **Voxelization** - Volumetric approach
3. **ML-based** - Learn from examples

### 3.4 T-Pose Normalization
**Complexity**: Medium

Ensure models are in standard T-pose for rigging.

**Implementation:**
1. Detect current pose
2. Calculate rotation corrections
3. Apply transforms to vertices
4. Output T-posed mesh

---

## Phase 4: Animation

**Timeline**: After Phase 3
**Goal**: Add basic animations to rigged models

### 4.1 Idle Animation
**Complexity**: Medium
**Approach**: Procedural or library

Generate subtle breathing/shifting animation.

```python
# Procedural idle
def generate_idle_animation(skeleton, duration=2.0, fps=30):
    frames = []
    for t in range(int(duration * fps)):
        # Subtle spine rotation (breathing)
        spine_rotation = sin(t * 0.1) * 0.02
        # Weight shifting
        hip_offset = sin(t * 0.05) * 0.01
        frames.append(...)
    return AnimationClip(frames)
```

### 4.2 Walk/Run Cycles
**Complexity**: High
**Approach**: Motion library or procedural

**Options:**
1. **Mixamo animations** - Download and retarget
2. **CMU Motion Capture** - Free mocap database
3. **Procedural** - IK-based walk generation

### 4.3 Animation Retargeting
**Complexity**: High

Apply animations from one skeleton to another.

**Implementation:**
1. Map bone names between skeletons
2. Calculate relative transforms
3. Apply with scaling/rotation adjustments

### 4.4 Mixamo Integration
**Complexity**: Medium
**Approach**: API integration (if available) or web automation

**Workflow:**
1. Export mesh in Mixamo-compatible format
2. Upload to Mixamo
3. Download rigged + animated
4. Import back to Sweedle

---

## Phase 5: Multi-Model Pipeline

**Timeline**: Long-term
**Goal**: Chain multiple AI models for better results

### 5.1 Text-to-Image + Image-to-3D
**Complexity**: Medium
**Models**: Stable Diffusion + Hunyuan3D

```
User Prompt → SD Image → Hunyuan3D → 3D Model
```

**Implementation:**
1. Integrate Stable Diffusion (diffusers)
2. Generate image from prompt
3. Pass to existing pipeline
4. Return combined result

### 5.2 Multi-View Generation
**Complexity**: High
**Models**: Wonder3D, Zero123, etc.

Generate multiple views for better 3D reconstruction.

### 5.3 Style Transfer
**Complexity**: Medium

Apply art styles to generated models:
- Low-poly
- Voxel
- Stylized
- Realistic

### 5.4 ControlNet Integration
**Complexity**: High

Use ControlNet for guided generation:
- Pose control
- Depth control
- Edge control

---

## Phase 6: Game Engine Integration

**Timeline**: Ongoing
**Goal**: Seamless export to game engines

### 6.1 Unity Package
**Complexity**: Medium

Create Unity package for import:
- Prefab generation
- Material setup
- LOD group configuration
- Animation controller

### 6.2 Unreal Plugin
**Complexity**: High

Create Unreal plugin:
- Asset import
- Material instances
- Blueprint integration
- Nanite support

### 6.3 Godot Integration
**Complexity**: Low-Medium

Godot-specific export:
- .tscn scene generation
- Material resources
- Animation player setup

### 6.4 Blender Add-on
**Complexity**: Medium

Blender integration:
- Direct import
- Material node setup
- Armature import
- Animation import

---

## Technical Requirements by Phase

### Phase 1
- CUDA development toolkit
- Visual Studio (for compilation)
- osmesa or EGL for headless rendering

### Phase 2
- pymeshlab
- xatlas (optional)
- numpy

### Phase 3
- PyTorch (already have)
- RigNet or similar
- scipy for optimization

### Phase 4
- Animation library (custom or existing)
- FBX SDK (optional)
- Mixamo account (optional)

### Phase 5
- Additional GPU memory (24GB+ recommended)
- Multiple model weights
- Increased storage

### Phase 6
- Unity Editor (for testing)
- Unreal Engine (for testing)
- Godot 4.x (for testing)
- Blender 4.x (for testing)

---

## Contributing to Roadmap Features

If you want to help implement any of these features:

1. Check if there's an open issue for the feature
2. Discuss implementation approach in the issue
3. Fork the repository
4. Create a feature branch
5. Implement with tests
6. Submit a pull request

### Priority Features Needing Help
1. Texture generation (CUDA compilation)
2. RigNet integration
3. Mixamo integration
4. Unity/Unreal export improvements

---

## Version Planning

| Version | Features | Target |
|---------|----------|--------|
| v1.1 | Thumbnail generation, batch improvements | Soon |
| v1.2 | Mesh smoothing, decimation UI | Soon |
| v1.3 | Texture generation | When possible |
| v2.0 | Auto-rigging (basic) | Future |
| v2.5 | Animation support | Future |
| v3.0 | Multi-model pipeline | Long-term |
