"""
GLTF Skinned Mesh Exporter

Exports rigged meshes as proper GLTF/GLB files with:
- Preserved materials and textures from source
- Embedded skeleton (bone hierarchy as nodes)
- Skinning weights (JOINTS_0, WEIGHTS_0 attributes)
- Animations (as GLTF animation clips)

Compatible with Godot 4.x, Unity, Unreal, and Three.js.
"""

import logging
import struct
import copy
from pathlib import Path
from typing import Optional
import numpy as np

from pygltflib import (
    GLTF2,
    Asset,
    Scene,
    Node,
    Mesh,
    Primitive,
    Attributes,
    Accessor,
    BufferView,
    Buffer,
    Skin,
    Animation,
    AnimationChannel,
    AnimationChannelTarget,
    AnimationSampler,
    FLOAT,
    UNSIGNED_SHORT,
    UNSIGNED_INT,
    ARRAY_BUFFER,
    ELEMENT_ARRAY_BUFFER,
    VEC3,
    VEC4,
    MAT4,
    SCALAR,
    LINEAR,
)

from ..rigging.schemas import SkeletonData, BoneData, SkinningData, WeightData

logger = logging.getLogger(__name__)


class GLTFSkinnedExporter:
    """
    Exports meshes with embedded skeleton and skinning for game engines.

    PRESERVES the original materials, textures, and appearance while adding:
    - Bone hierarchy as GLTF nodes
    - Skinning attributes (JOINTS_0, WEIGHTS_0)
    - Inverse bind matrices for skeletal deformation
    - Optional: Animation clips
    """

    def __init__(self):
        self.gltf: Optional[GLTF2] = None
        self.bone_node_indices: dict[str, int] = {}
        self.additional_data: bytearray = bytearray()
        self.original_buffer_length: int = 0

    def export(
        self,
        mesh_path: Path,
        skeleton: SkeletonData,
        skinning: SkinningData,
        output_path: Path,
        animations: Optional[list[dict]] = None,
        ground_origin: bool = True,
    ) -> Path:
        """
        Export a rigged mesh as a skinned GLB file, preserving materials/textures.

        Args:
            mesh_path: Path to source mesh (GLB with textures)
            skeleton: Skeleton data with bone hierarchy
            skinning: Skinning weights per vertex
            output_path: Output GLB path
            animations: Optional list of animation data dicts
            ground_origin: Move mesh so bottom is at Y=0 (fixes models spawning half in ground)

        Returns:
            Path to exported GLB
        """
        logger.info(f"Exporting skinned GLB: {mesh_path} -> {output_path}")
        logger.info(f"Skeleton has {len(skeleton.bones)} bones, skinning has {len(skinning.weights)} weight entries")

        # Load original GLTF (preserves materials, textures, etc.)
        self.gltf = GLTF2.load(str(mesh_path))

        # Get original binary blob
        original_blob = self.gltf.binary_blob() or b''
        self.original_buffer_length = len(original_blob)
        self.additional_data = bytearray(original_blob)

        # Apply ground_origin transformation if enabled
        y_offset = 0.0
        if ground_origin:
            y_offset = self._apply_ground_origin(skeleton)

        logger.info(f"Loaded source GLTF with {len(self.gltf.nodes)} nodes, {len(self.gltf.meshes)} meshes, {len(self.gltf.materials or [])} materials")

        # Ensure lists exist
        if self.gltf.skins is None:
            self.gltf.skins = []
        if self.gltf.animations is None:
            self.gltf.animations = []

        # Create bone hierarchy as nodes
        skeleton_root_idx = self._create_bone_nodes(skeleton)

        # Get vertex count from mesh for validation
        vertex_count = self._get_vertex_count()
        logger.info(f"Mesh has {vertex_count} vertices, skinning weights cover {skinning.vertex_count} vertices")

        # Add skinning attributes to the mesh
        self._add_skinning_to_mesh(skeleton, skinning)

        # Create skin linking mesh to skeleton
        mesh_node_idx = self._find_mesh_node()
        self._create_skin(skeleton, mesh_node_idx, skeleton_root_idx)

        # Add animations if provided
        if animations:
            self._add_animations(animations)

        # Finalize buffer
        self._finalize_buffer()

        # Save GLB
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self.gltf.save(str(output_path))

        # Debug: Log GLTF structure
        logger.info(f"GLTF structure after export:")
        logger.info(f"  - Nodes: {len(self.gltf.nodes)}")
        logger.info(f"  - Meshes: {len(self.gltf.meshes)}")
        logger.info(f"  - Skins: {len(self.gltf.skins)}")
        logger.info(f"  - Animations: {len(self.gltf.animations)}")
        logger.info(f"  - Materials: {len(self.gltf.materials or [])}")
        logger.info(f"  - Textures: {len(self.gltf.textures or [])}")
        logger.info(f"  - Images: {len(self.gltf.images or [])}")

        # Log mesh node and skin linkage
        for i, node in enumerate(self.gltf.nodes):
            if node.mesh is not None:
                logger.info(f"  - Node {i} '{node.name}' has mesh={node.mesh}, skin={node.skin}")

        logger.info(f"Exported skinned GLB with {len(skeleton.bones)} bones to {output_path}")
        return output_path

    def _get_vertex_count(self) -> int:
        """Get vertex count from the first mesh primitive."""
        if not self.gltf.meshes:
            return 0

        mesh = self.gltf.meshes[0]
        if not mesh.primitives:
            return 0

        prim = mesh.primitives[0]
        if prim.attributes.POSITION is None:
            return 0

        pos_accessor = self.gltf.accessors[prim.attributes.POSITION]
        return pos_accessor.count

    def _apply_ground_origin(self, skeleton: SkeletonData) -> float:
        """
        Move mesh vertices and skeleton so the bottom of the mesh is at Y=0.

        This fixes models appearing half-sunk in the ground in game engines.

        Args:
            skeleton: Skeleton data to adjust (bone positions will be modified)

        Returns:
            The Y offset that was applied (negative means mesh was below origin)
        """
        if not self.gltf.meshes:
            return 0.0

        # Find minimum Y across all mesh primitives
        min_y = float('inf')

        for mesh in self.gltf.meshes:
            for prim in mesh.primitives:
                if prim.attributes.POSITION is None:
                    continue

                pos_accessor = self.gltf.accessors[prim.attributes.POSITION]
                pos_view = self.gltf.bufferViews[pos_accessor.bufferView]

                # Read vertex positions from buffer
                start = pos_view.byteOffset + (pos_accessor.byteOffset or 0)
                vertex_count = pos_accessor.count

                # VEC3 of floats = 12 bytes per vertex
                pos_data = np.frombuffer(
                    bytes(self.additional_data[start:start + vertex_count * 12]),
                    dtype=np.float32
                ).reshape(-1, 3)

                primitive_min_y = pos_data[:, 1].min()
                min_y = min(min_y, primitive_min_y)

        if min_y == float('inf') or abs(min_y) < 1e-6:
            logger.info("Mesh already grounded or no vertices found")
            return 0.0

        # Convert to Python float to avoid numpy serialization issues
        y_offset = float(-min_y)
        logger.info(f"Grounding mesh: min_y={min_y:.4f}, applying offset={y_offset:.4f}")

        # Apply offset to all mesh vertex positions
        for mesh in self.gltf.meshes:
            for prim in mesh.primitives:
                if prim.attributes.POSITION is None:
                    continue

                pos_accessor = self.gltf.accessors[prim.attributes.POSITION]
                pos_view = self.gltf.bufferViews[pos_accessor.bufferView]

                start = pos_view.byteOffset + (pos_accessor.byteOffset or 0)
                vertex_count = pos_accessor.count

                # Read, modify, write back
                pos_data = np.frombuffer(
                    bytes(self.additional_data[start:start + vertex_count * 12]),
                    dtype=np.float32
                ).reshape(-1, 3).copy()

                pos_data[:, 1] += y_offset

                # Write modified data back to buffer
                self.additional_data[start:start + vertex_count * 12] = pos_data.tobytes()

                # Update accessor min/max if present
                # Convert to Python float to avoid numpy serialization issues
                if pos_accessor.min is not None and len(pos_accessor.min) >= 2:
                    pos_accessor.min[1] = float(pos_accessor.min[1] + y_offset)
                if pos_accessor.max is not None and len(pos_accessor.max) >= 2:
                    pos_accessor.max[1] = float(pos_accessor.max[1] + y_offset)

        # Adjust skeleton bone positions by the same offset
        # Convert to Python floats to avoid numpy serialization issues
        for bone in skeleton.bones:
            bone.head_position = (
                float(bone.head_position[0]),
                float(bone.head_position[1] + y_offset),
                float(bone.head_position[2])
            )
            if bone.tail_position:
                bone.tail_position = (
                    float(bone.tail_position[0]),
                    float(bone.tail_position[1] + y_offset),
                    float(bone.tail_position[2])
                )

        logger.info(f"Grounded {len(skeleton.bones)} bone positions")
        return y_offset

    def _find_mesh_node(self) -> int:
        """Find the node containing the mesh."""
        for i, node in enumerate(self.gltf.nodes):
            if node.mesh is not None:
                return i
        raise ValueError("No mesh node found in GLTF")

    def _create_bone_nodes(self, skeleton: SkeletonData) -> int:
        """
        Create GLTF nodes for each bone in the skeleton hierarchy.

        Returns the index of the root bone node.
        """
        bone_map = {b.name: b for b in skeleton.bones}
        root_bones = [b for b in skeleton.bones if not b.parent]

        if not root_bones:
            raise ValueError("No root bone found in skeleton")

        # Starting index for new nodes
        node_start_idx = len(self.gltf.nodes)

        # Create nodes for all bones
        for bone in skeleton.bones:
            node = Node(name=bone.name)
            # Set bone position (in world space initially)
            # Convert to Python floats to avoid numpy serialization issues
            node.translation = [float(x) for x in bone.head_position]

            node_idx = len(self.gltf.nodes)
            self.gltf.nodes.append(node)
            self.bone_node_indices[bone.name] = node_idx

        # Set up parent-child relationships and convert to local space
        for bone in skeleton.bones:
            if bone.parent and bone.parent in self.bone_node_indices:
                parent_idx = self.bone_node_indices[bone.parent]
                child_idx = self.bone_node_indices[bone.name]

                if self.gltf.nodes[parent_idx].children is None:
                    self.gltf.nodes[parent_idx].children = []
                self.gltf.nodes[parent_idx].children.append(child_idx)

                # Convert to local space relative to parent
                parent_bone = bone_map[bone.parent]
                parent_pos = np.array(parent_bone.head_position)
                child_pos = np.array(bone.head_position)
                local_pos = child_pos - parent_pos
                # Convert to Python floats to avoid numpy serialization issues
                self.gltf.nodes[child_idx].translation = [float(x) for x in local_pos]

        logger.info(f"Created {len(skeleton.bones)} bone nodes starting at index {node_start_idx}")
        return self.bone_node_indices[root_bones[0].name]

    def _add_skinning_to_mesh(self, skeleton: SkeletonData, skinning: SkinningData):
        """Add JOINTS_0 and WEIGHTS_0 attributes to the mesh."""
        if not self.gltf.meshes:
            raise ValueError("No meshes in GLTF")

        # Get vertex count
        vertex_count = self._get_vertex_count()

        # Create bone name to index mapping
        bone_indices = {b.name: i for i, b in enumerate(skeleton.bones)}

        # Prepare skinning arrays
        joints = np.zeros((vertex_count, 4), dtype=np.uint16)
        weights = np.zeros((vertex_count, 4), dtype=np.float32)

        # Build weight lookup
        weight_map = {w.vertex_index: w.bone_weights for w in skinning.weights}

        for vi in range(vertex_count):
            bone_weights = weight_map.get(vi, {})

            if not bone_weights:
                # No weights - bind to first bone with full weight
                joints[vi, 0] = 0
                weights[vi, 0] = 1.0
                continue

            # Sort by weight descending, take top 4
            sorted_weights = sorted(bone_weights.items(), key=lambda x: -x[1])[:4]

            for i, (bone_name, weight) in enumerate(sorted_weights):
                if bone_name in bone_indices:
                    joints[vi, i] = bone_indices[bone_name]
                    weights[vi, i] = weight

            # Normalize weights to sum to 1.0
            weight_sum = weights[vi].sum()
            if weight_sum > 0:
                weights[vi] /= weight_sum

        # Add joints accessor
        joints_accessor_idx = self._add_accessor(
            joints.tobytes(),
            UNSIGNED_SHORT,
            VEC4,
            vertex_count,
            ARRAY_BUFFER,
        )

        # Add weights accessor
        weights_accessor_idx = self._add_accessor(
            weights.tobytes(),
            FLOAT,
            VEC4,
            vertex_count,
            ARRAY_BUFFER,
        )

        # Add attributes to all mesh primitives
        for mesh_idx, mesh in enumerate(self.gltf.meshes):
            for prim_idx, prim in enumerate(mesh.primitives):
                prim.attributes.JOINTS_0 = joints_accessor_idx
                prim.attributes.WEIGHTS_0 = weights_accessor_idx
                logger.info(f"Mesh {mesh_idx} primitive {prim_idx}: POSITION={prim.attributes.POSITION}, JOINTS_0={prim.attributes.JOINTS_0}, WEIGHTS_0={prim.attributes.WEIGHTS_0}")

        logger.info(f"Added skinning attributes: JOINTS_0={joints_accessor_idx}, WEIGHTS_0={weights_accessor_idx}")

    def _create_skin(self, skeleton: SkeletonData, mesh_node_idx: int, skeleton_root_idx: int):
        """Create GLTF skin linking mesh to skeleton."""
        num_bones = len(skeleton.bones)

        # Calculate inverse bind matrices
        ibm_data = np.zeros((num_bones, 16), dtype=np.float32)

        for i, bone in enumerate(skeleton.bones):
            bone_pos = np.array(bone.head_position)

            # Inverse bind matrix: translates from mesh space to bone space
            ibm = np.eye(4, dtype=np.float32)
            ibm[0, 3] = -bone_pos[0]
            ibm[1, 3] = -bone_pos[1]
            ibm[2, 3] = -bone_pos[2]

            # GLTF uses column-major order
            ibm_data[i] = ibm.T.flatten()

        # Add inverse bind matrices accessor
        ibm_accessor_idx = self._add_accessor(
            ibm_data.tobytes(),
            FLOAT,
            MAT4,
            num_bones,
            None,  # No target for IBMs
        )

        # Get joint node indices in skeleton bone order
        joint_indices = [self.bone_node_indices[b.name] for b in skeleton.bones]

        # Create skin
        skin = Skin(
            name="Armature",
            joints=joint_indices,
            inverseBindMatrices=ibm_accessor_idx,
            skeleton=skeleton_root_idx,
        )

        skin_idx = len(self.gltf.skins)
        self.gltf.skins.append(skin)

        # Link mesh node to skin
        self.gltf.nodes[mesh_node_idx].skin = skin_idx

        # Add skeleton root as child of mesh node so it's in the scene
        if self.gltf.nodes[mesh_node_idx].children is None:
            self.gltf.nodes[mesh_node_idx].children = []
        self.gltf.nodes[mesh_node_idx].children.append(skeleton_root_idx)

        logger.info(f"Created skin with {num_bones} joints, linked to mesh node {mesh_node_idx}")

    def _add_animations(self, animations: list[dict]):
        """
        Add animations to the GLTF.

        Args:
            animations: List of animation dicts with format:
                {
                    "name": "Idle",
                    "duration": 2.0,
                    "tracks": [
                        {
                            "bone_name": "Hips",
                            "times": [0.0, 1.0, 2.0],
                            "rotations": [[x,y,z,w], ...],  # quaternions
                            "positions": [[x,y,z], ...],    # optional
                        }
                    ]
                }
        """
        for anim_data in animations:
            anim_name = anim_data.get("name", "Animation")
            tracks = anim_data.get("tracks", [])

            if not tracks:
                continue

            samplers = []
            channels = []

            for track in tracks:
                bone_name = track.get("bone_name")
                if bone_name not in self.bone_node_indices:
                    logger.warning(f"Bone '{bone_name}' not found, skipping track")
                    continue

                target_node = self.bone_node_indices[bone_name]
                times = np.array(track.get("times", []), dtype=np.float32)

                if len(times) == 0:
                    continue

                # Add rotation track
                rotations = track.get("rotations")
                if rotations and len(rotations) > 0:
                    rot_data = np.array(rotations, dtype=np.float32).flatten()

                    time_accessor = self._add_accessor(
                        times.tobytes(),
                        FLOAT,
                        SCALAR,
                        len(times),
                        None,
                        min_values=[float(times.min())],
                        max_values=[float(times.max())],
                    )

                    rot_accessor = self._add_accessor(
                        rot_data.tobytes(),
                        FLOAT,
                        VEC4,
                        len(rotations),
                        None,
                    )

                    sampler_idx = len(samplers)
                    samplers.append(AnimationSampler(
                        input=time_accessor,
                        output=rot_accessor,
                        interpolation=LINEAR,
                    ))

                    channels.append(AnimationChannel(
                        sampler=sampler_idx,
                        target=AnimationChannelTarget(
                            node=target_node,
                            path="rotation",
                        ),
                    ))

                # Add position track if present
                positions = track.get("positions")
                if positions and len(positions) > 0:
                    pos_data = np.array(positions, dtype=np.float32).flatten()

                    time_accessor = self._add_accessor(
                        times.tobytes(),
                        FLOAT,
                        SCALAR,
                        len(times),
                        None,
                        min_values=[float(times.min())],
                        max_values=[float(times.max())],
                    )

                    pos_accessor = self._add_accessor(
                        pos_data.tobytes(),
                        FLOAT,
                        VEC3,
                        len(positions),
                        None,
                    )

                    sampler_idx = len(samplers)
                    samplers.append(AnimationSampler(
                        input=time_accessor,
                        output=pos_accessor,
                        interpolation=LINEAR,
                    ))

                    channels.append(AnimationChannel(
                        sampler=sampler_idx,
                        target=AnimationChannelTarget(
                            node=target_node,
                            path="translation",
                        ),
                    ))

            if samplers and channels:
                animation = Animation(
                    name=anim_name,
                    samplers=samplers,
                    channels=channels,
                )
                self.gltf.animations.append(animation)
                logger.info(f"Added animation '{anim_name}' with {len(channels)} channels")

    def _add_accessor(
        self,
        data: bytes,
        component_type: int,
        accessor_type: str,
        count: int,
        target: Optional[int],
        min_values: Optional[list] = None,
        max_values: Optional[list] = None,
    ) -> int:
        """Add data to buffer and create accessor."""
        # Align to 4 bytes
        while len(self.additional_data) % 4 != 0:
            self.additional_data.append(0)

        byte_offset = len(self.additional_data)
        self.additional_data.extend(data)

        # Create buffer view
        buffer_view = BufferView(
            buffer=0,
            byteOffset=byte_offset,
            byteLength=len(data),
        )
        if target is not None:
            buffer_view.target = target

        buffer_view_idx = len(self.gltf.bufferViews)
        self.gltf.bufferViews.append(buffer_view)

        # Create accessor
        accessor = Accessor(
            bufferView=buffer_view_idx,
            byteOffset=0,
            componentType=component_type,
            count=count,
            type=accessor_type,
        )
        if min_values is not None:
            accessor.min = min_values
        if max_values is not None:
            accessor.max = max_values

        accessor_idx = len(self.gltf.accessors)
        self.gltf.accessors.append(accessor)

        return accessor_idx

    def _finalize_buffer(self):
        """Finalize the binary buffer."""
        # Align to 4 bytes
        while len(self.additional_data) % 4 != 0:
            self.additional_data.append(0)

        # Update buffer size
        if self.gltf.buffers:
            self.gltf.buffers[0].byteLength = len(self.additional_data)
        else:
            self.gltf.buffers = [Buffer(byteLength=len(self.additional_data))]

        # Set binary blob
        self.gltf.set_binary_blob(bytes(self.additional_data))

        logger.info(f"Finalized buffer: {self.original_buffer_length} -> {len(self.additional_data)} bytes")


# Convenience function
def export_skinned_glb(
    mesh_path: Path,
    skeleton: SkeletonData,
    skinning: SkinningData,
    output_path: Path,
    animations: Optional[list[dict]] = None,
    ground_origin: bool = True,
) -> Path:
    """
    Export a skinned GLB file, preserving materials and textures.

    Args:
        mesh_path: Path to source mesh (GLB with textures)
        skeleton: Skeleton data
        skinning: Skinning weights
        output_path: Output path
        animations: Optional animation data
        ground_origin: Move mesh so bottom is at Y=0 (default: True)

    Returns:
        Path to exported GLB
    """
    exporter = GLTFSkinnedExporter()
    return exporter.export(mesh_path, skeleton, skinning, output_path, animations, ground_origin)
