"""
UniRig ML-based auto-rigging processor.

Uses machine learning to predict skeleton joints and skinning weights
from mesh geometry. Optimized for humanoid characters.
"""

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Optional

import numpy as np

try:
    import trimesh
except ImportError:
    trimesh = None

try:
    import torch
except ImportError:
    torch = None

from ..config import rigging_settings
from ..schemas import (
    CharacterType,
    RiggingResult,
    SkeletonData,
    SkinningData,
    WeightData,
    CharacterAnalysis,
)
from ..skeleton import create_humanoid_skeleton, Skeleton
from .base import BaseRiggingProcessor

logger = logging.getLogger(__name__)


class UniRigProcessor(BaseRiggingProcessor):
    """
    UniRig ML-based rigging processor.

    Currently implements a heuristic-based approach with plans to integrate
    the full UniRig ML model when available.
    """

    name = "unirig"
    supported_types = [CharacterType.HUMANOID, CharacterType.AUTO]

    def __init__(self):
        self._model = None
        self._device = rigging_settings.UNIRIG_DEVICE
        self._initialized = False
        self._executor = ThreadPoolExecutor(max_workers=2)

    async def initialize(self) -> None:
        """Initialize the UniRig processor."""
        if self._initialized:
            return

        logger.info("Initializing UniRig processor...")

        # Check for required dependencies
        if trimesh is None:
            raise RuntimeError("trimesh is required for UniRig processor")

        # Check for CUDA if specified
        if self._device == "cuda" and torch is not None:
            if not torch.cuda.is_available():
                logger.warning("CUDA not available, falling back to CPU")
                self._device = "cpu"

        # TODO: Load actual UniRig model when available
        # For now, we use heuristic-based skeleton fitting
        logger.info(f"UniRig processor initialized (device: {self._device})")
        self._initialized = True

    async def process(
        self,
        mesh_path: Path,
        character_type: CharacterType,
        output_dir: Path,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> RiggingResult:
        """
        Process a mesh and generate rigging using UniRig approach.

        Args:
            mesh_path: Path to input mesh (GLB/OBJ)
            character_type: Character type to rig
            output_dir: Output directory
            progress_callback: Progress callback

        Returns:
            RiggingResult with skeleton and weights
        """
        start_time = time.time()

        try:
            if not self._initialized:
                await self.initialize()

            self._report_progress(progress_callback, 0.05, "Loading mesh...")

            # Load mesh
            mesh = await asyncio.get_event_loop().run_in_executor(
                self._executor,
                lambda: trimesh.load(str(mesh_path))
            )

            # Handle scene vs single mesh
            if isinstance(mesh, trimesh.Scene):
                # Combine all geometries
                geometries = list(mesh.geometry.values())
                if not geometries:
                    return RiggingResult(
                        success=False,
                        error="No geometry found in mesh file"
                    )
                mesh = trimesh.util.concatenate(geometries)

            vertex_count = len(mesh.vertices)
            logger.info(f"Loaded mesh with {vertex_count} vertices")

            # Check vertex limit
            if vertex_count > rigging_settings.MAX_VERTICES_FOR_UNIRIG:
                return RiggingResult(
                    success=False,
                    error=f"Mesh has {vertex_count} vertices, exceeds limit of {rigging_settings.MAX_VERTICES_FOR_UNIRIG}"
                )

            self._report_progress(progress_callback, 0.15, "Analyzing mesh...")

            # Analyze mesh to detect character type if auto
            analysis = await self._analyze_mesh(mesh)

            if character_type == CharacterType.AUTO:
                if analysis.is_humanoid_likely:
                    character_type = CharacterType.HUMANOID
                elif analysis.is_quadruped_likely:
                    character_type = CharacterType.QUADRUPED
                else:
                    character_type = CharacterType.HUMANOID  # Default
                logger.info(f"Auto-detected character type: {character_type.value}")

            self._report_progress(progress_callback, 0.25, "Creating skeleton...")

            # Create skeleton from template
            skeleton = await asyncio.get_event_loop().run_in_executor(
                self._executor,
                lambda: self._create_fitted_skeleton(mesh, character_type, analysis)
            )

            self._report_progress(progress_callback, 0.50, "Computing skinning weights...")

            # Compute skinning weights
            skinning = await asyncio.get_event_loop().run_in_executor(
                self._executor,
                lambda: self._compute_skinning_weights(mesh, skeleton)
            )

            self._report_progress(progress_callback, 0.75, "Exporting rigged mesh...")

            # Export rigged mesh
            output_path = output_dir / "rigged.glb"
            await asyncio.get_event_loop().run_in_executor(
                self._executor,
                lambda: self._export_rigged_mesh(mesh, skeleton, skinning, output_path)
            )

            self._report_progress(progress_callback, 1.0, "Complete")

            processing_time = time.time() - start_time
            logger.info(f"Rigging completed in {processing_time:.2f}s")

            return RiggingResult(
                success=True,
                skeleton=skeleton.to_skeleton_data(),
                skinning=skinning,
                rigged_mesh_path=str(output_path),
                detected_type=character_type,
                processor_used=self.name,
                processing_time=processing_time,
                vertex_count=vertex_count,
            )

        except Exception as e:
            logger.error(f"UniRig processing failed: {e}", exc_info=True)
            return RiggingResult(
                success=False,
                error=str(e),
                processing_time=time.time() - start_time,
            )

    async def cleanup(self) -> None:
        """Clean up resources."""
        self._executor.shutdown(wait=False)
        self._initialized = False

    async def detect_character_type(
        self,
        mesh_path: Path,
    ) -> tuple[CharacterType, float]:
        """
        Detect character type from mesh using geometry analysis.

        Overrides base implementation to use actual mesh analysis.

        Args:
            mesh_path: Path to mesh file

        Returns:
            Tuple of (detected_type, confidence)
        """
        if not self._initialized:
            await self.initialize()

        try:
            # Load mesh
            mesh = await asyncio.get_event_loop().run_in_executor(
                self._executor,
                lambda: trimesh.load(str(mesh_path))
            )

            # Handle scene vs single mesh
            if isinstance(mesh, trimesh.Scene):
                geometries = list(mesh.geometry.values())
                if not geometries:
                    logger.warning("No geometry found in mesh for detection")
                    return CharacterType.HUMANOID, 0.5
                mesh = trimesh.util.concatenate(geometries)

            # Analyze mesh geometry
            analysis = await self._analyze_mesh(mesh)

            # Log the analysis for debugging
            logger.info(f"Mesh analysis: dimensions={analysis.dimensions}, height/horizontal={analysis.height_to_width_ratio:.2f}")
            logger.info(f"Detection: humanoid_likely={analysis.is_humanoid_likely}, quadruped_likely={analysis.is_quadruped_likely}")

            # Determine character type from analysis
            if analysis.is_quadruped_likely:
                return CharacterType.QUADRUPED, analysis.confidence
            elif analysis.is_humanoid_likely:
                return CharacterType.HUMANOID, analysis.confidence
            else:
                # Default to humanoid with low confidence
                return CharacterType.HUMANOID, 0.3

        except Exception as e:
            logger.error(f"Character detection failed: {e}", exc_info=True)
            return CharacterType.HUMANOID, 0.5

    async def _analyze_mesh(self, mesh: "trimesh.Trimesh") -> CharacterAnalysis:
        """Analyze mesh geometry to determine character type."""
        bounds = mesh.bounds
        bbox_min = bounds[0]
        bbox_max = bounds[1]
        dimensions = bbox_max - bbox_min

        width = dimensions[0]  # X (side-to-side)
        height = dimensions[1]  # Y (up)
        depth = dimensions[2]  # Z (front-to-back)

        # Use height vs longest horizontal dimension for better quadruped detection
        # Quadrupeds are longer/wider than tall, humanoids are taller than wide
        horizontal_extent = max(width, depth)
        height_to_horizontal = height / max(horizontal_extent, 0.001)

        # Log both ratios for debugging
        height_to_width = height / max(width, 0.001)
        logger.debug(f"Mesh ratios: h/w={height_to_width:.2f}, h/horizontal={height_to_horizontal:.2f}")

        # Heuristics for character type using height vs horizontal extent
        is_humanoid = (
            rigging_settings.HUMANOID_HEIGHT_RATIO_MIN <= height_to_horizontal <= rigging_settings.HUMANOID_HEIGHT_RATIO_MAX
        )
        is_quadruped = height_to_horizontal < rigging_settings.QUADRUPED_HEIGHT_RATIO_MAX

        # Calculate confidence based on how clearly the ratio indicates type
        if is_humanoid:
            # Higher confidence the taller/narrower it is (ratio > 1.5)
            confidence = min(1.0, (height_to_horizontal - 1.0) / 2.0)
        elif is_quadruped:
            # Higher confidence the longer/flatter it is (ratio < 1.5)
            confidence = min(1.0, 1.0 - height_to_horizontal / 1.5)
        else:
            confidence = 0.3

        return CharacterAnalysis(
            bounding_box=(tuple(bbox_min), tuple(bbox_max)),
            dimensions=(width, height, depth),
            height_to_width_ratio=height_to_horizontal,  # Store the ratio used for detection
            center_of_mass=tuple(mesh.center_mass),
            vertex_count=len(mesh.vertices),
            is_humanoid_likely=is_humanoid,
            is_quadruped_likely=is_quadruped and not is_humanoid,
            confidence=confidence,
        )

    def _create_fitted_skeleton(
        self,
        mesh: "trimesh.Trimesh",
        character_type: CharacterType,
        analysis: CharacterAnalysis,
    ) -> Skeleton:
        """Create skeleton fitted to mesh dimensions with mesh-aware arm placement."""
        from ..skeleton import create_humanoid_skeleton, create_quadruped_skeleton

        # Create base skeleton from template
        if character_type == CharacterType.QUADRUPED:
            skeleton = create_quadruped_skeleton()
        else:
            skeleton = create_humanoid_skeleton()

        # Use bounding box center instead of center of mass for better positioning
        bbox_min = mesh.bounds[0]
        bbox_max = mesh.bounds[1]
        bbox_center = (bbox_min + bbox_max) / 2

        # For quadrupeds, use mesh-aware fitting
        if character_type == CharacterType.QUADRUPED:
            # Detect orientation first to know which end is head
            try:
                needs_flip = self._detect_quadruped_orientation(mesh)
            except Exception as e:
                logger.warning(f"Could not detect quadruped orientation: {e}")
                needs_flip = False

            # Fit skeleton to actual mesh geometry
            try:
                self._fit_quadruped_to_mesh(skeleton, mesh, needs_flip)
                logger.info("Fitted quadruped skeleton to mesh geometry")
            except Exception as e:
                logger.warning(f"Could not fit quadruped to mesh, using basic scaling: {e}")
                # Fall back to basic scaling
                self._scale_quadruped_skeleton(skeleton, mesh.bounds, bbox_center)
                if needs_flip:
                    self._flip_skeleton_z(skeleton, bbox_center)
        else:
            # For humanoids, scale by height
            mesh_height = analysis.dimensions[1]
            skeleton.scale_to_mesh(mesh_height, bbox_center)

        # For humanoid characters, fit arm bones to actual mesh geometry
        # This handles T-pose, A-pose, and other arm positions
        if character_type == CharacterType.HUMANOID:
            try:
                mesh_bounds = (mesh.bounds[0], mesh.bounds[1])
                skeleton.fit_arms_to_mesh(mesh.vertices, mesh_bounds)
                logger.info("Fitted arm bones to mesh geometry")
            except Exception as e:
                logger.warning(f"Could not fit arms to mesh: {e}")
                # Fall back to default template positions (already scaled)

        return skeleton

    def _scale_quadruped_skeleton(
        self,
        skeleton: "Skeleton",
        mesh_bounds: np.ndarray,
        mesh_center: np.ndarray,
    ) -> None:
        """
        Scale and position quadruped skeleton to fit inside the mesh.

        Uses uniform scaling based on the best fit to ensure skeleton
        fits inside the mesh proportionally.

        Args:
            skeleton: The skeleton to scale
            mesh_bounds: Mesh bounding box [min, max]
            mesh_center: Center of mesh bounding box
        """
        all_bones = skeleton.get_all_bones()
        if not all_bones:
            return

        # Get skeleton bounds
        all_positions = []
        for bone in all_bones:
            all_positions.append(bone.head)
            all_positions.append(bone.tail)

        positions = np.array(all_positions)
        skel_min = positions.min(axis=0)
        skel_max = positions.max(axis=0)
        skel_size = skel_max - skel_min
        skel_center = (skel_min + skel_max) / 2

        # Get mesh size
        mesh_min, mesh_max = mesh_bounds[0], mesh_bounds[1]
        mesh_size = mesh_max - mesh_min

        # Calculate scale factors for each dimension
        # Use 90% of mesh size to keep skeleton slightly inside
        scale_factors = (mesh_size * 0.9) / np.maximum(skel_size, 0.001)

        # Use uniform scaling (smallest factor to ensure skeleton fits)
        scale_factor = min(scale_factors)

        logger.info(f"Quadruped skeleton scaling: factor={scale_factor:.2f}, skel_size={skel_size}, mesh_size={mesh_size}")

        # Scale around skeleton center, then translate to mesh center
        for bone in all_bones:
            # Scale relative to skeleton center
            bone.head = (bone.head - skel_center) * scale_factor + mesh_center
            bone.tail = (bone.tail - skel_center) * scale_factor + mesh_center

    def _fit_quadruped_to_mesh(
        self,
        skeleton: "Skeleton",
        mesh: "trimesh.Trimesh",
        flip_z: bool,
    ) -> None:
        """
        Fit quadruped skeleton to actual mesh geometry.

        Finds leg positions, spine alignment, and head/tail positions
        from the mesh vertices. Handles both X-oriented and Z-oriented meshes.

        Args:
            skeleton: Skeleton to fit
            mesh: Target mesh
            flip_z: Whether skeleton faces opposite direction from default
        """
        vertices = mesh.vertices
        bounds = mesh.bounds
        bbox_min, bbox_max = bounds[0], bounds[1]
        bbox_center = (bbox_min + bbox_max) / 2

        # Mesh dimensions
        dim_x = bbox_max[0] - bbox_min[0]
        dim_y = bbox_max[1] - bbox_min[1]  # Height (always Y)
        dim_z = bbox_max[2] - bbox_min[2]

        # Determine primary axis using multiple heuristics
        # 1. Basic dimension comparison (longest axis is usually front-back)
        # 2. Head detection (which end has more vertical spread)
        # 3. Leg cluster analysis (legs should be on opposite ends of front-back axis)
        x_oriented, orientation_confidence = self._detect_primary_axis(mesh, dim_x, dim_y, dim_z)

        logger.info(f"Mesh dimensions: X={dim_x:.3f}, Y={dim_y:.3f}, Z={dim_z:.3f}")
        logger.info(f"Detected orientation: {'X-oriented' if x_oriented else 'Z-oriented'} (confidence={orientation_confidence:.2f})")

        # Set up axis mapping based on orientation
        if x_oriented:
            # Dog faces along X axis
            # front_back_axis = 0 (X), left_right_axis = 2 (Z)
            front_back_idx = 0
            left_right_idx = 2
            mesh_length = dim_x  # Front-back length
            mesh_width = dim_z   # Left-right width
        else:
            # Dog faces along Z axis (original assumption)
            # front_back_axis = 2 (Z), left_right_axis = 0 (X)
            front_back_idx = 2
            left_right_idx = 0
            mesh_length = dim_z
            mesh_width = dim_x

        mesh_height = dim_y
        fb_center = bbox_center[front_back_idx]
        lr_center = bbox_center[left_right_idx]
        y_center = bbox_center[1]

        # Detect head direction along the front-back axis
        # Head end typically has more vertical extent (neck going up)
        fb_min = bbox_min[front_back_idx]
        fb_max = bbox_max[front_back_idx]
        fb_range = fb_max - fb_min

        # Check which end has the head by looking at vertex distribution
        front_threshold = fb_min + fb_range * 0.3
        back_threshold = fb_max - fb_range * 0.3

        front_verts = vertices[vertices[:, front_back_idx] < front_threshold]
        back_verts = vertices[vertices[:, front_back_idx] > back_threshold]

        # Head end has more Y range (neck/head sticking up)
        front_y_range = front_verts[:, 1].max() - front_verts[:, 1].min() if len(front_verts) > 5 else 0
        back_y_range = back_verts[:, 1].max() - back_verts[:, 1].min() if len(back_verts) > 5 else 0

        # Determine head/tail positions
        head_at_min = front_y_range > back_y_range  # Head is at min end of front-back axis

        logger.info(f"Head detection: front_y_range={front_y_range:.3f}, back_y_range={back_y_range:.3f}, head_at_min={head_at_min}")

        if head_at_min:
            head_fb = fb_min
            tail_fb = fb_max
        else:
            head_fb = fb_max
            tail_fb = fb_min

        # Find leg positions (lowest vertices in each quadrant)
        ground_y = bbox_min[1]
        leg_region_height = mesh_height * 0.4

        leg_vertices = vertices[vertices[:, 1] < ground_y + leg_region_height]

        if len(leg_vertices) < 20:
            raise ValueError("Not enough leg vertices for mesh-aware fitting")

        # Determine front/back quadrants based on detected orientation
        def is_front(v):
            if head_at_min:
                return v[:, front_back_idx] < fb_center
            else:
                return v[:, front_back_idx] > fb_center

        def is_back(v):
            if head_at_min:
                return v[:, front_back_idx] > fb_center
            else:
                return v[:, front_back_idx] < fb_center

        def is_left(v):
            return v[:, left_right_idx] > lr_center

        def is_right(v):
            return v[:, left_right_idx] < lr_center

        # Find foot positions (lowest vertices in each quadrant)
        foot_positions = {}
        quadrants = [
            ("front_left", is_front, is_left),
            ("front_right", is_front, is_right),
            ("back_left", is_back, is_left),
            ("back_right", is_back, is_right),
        ]

        for name, fb_filter, lr_filter in quadrants:
            fb_mask = fb_filter(leg_vertices)
            lr_mask = lr_filter(leg_vertices)
            quadrant_verts = leg_vertices[fb_mask & lr_mask]

            if len(quadrant_verts) > 5:
                # Find lowest vertices (feet)
                lowest_y = quadrant_verts[:, 1].min()
                foot_verts = quadrant_verts[quadrant_verts[:, 1] < lowest_y + leg_region_height * 0.2]
                foot_positions[name] = np.mean(foot_verts, axis=0) if len(foot_verts) > 0 else quadrant_verts[quadrant_verts[:, 1].argmin()]

        if len(foot_positions) < 4:
            raise ValueError(f"Could not find all four feet, found: {list(foot_positions.keys())}")

        logger.info(f"Found feet at: {[(k, v.tolist()) for k, v in foot_positions.items()]}")

        # Find shoulder/hip positions (higher up, above legs)
        shoulder_hip_y = bbox_min[1] + mesh_height * 0.6  # 60% up

        # Calculate spine positions along front-back axis
        spine_y = shoulder_hip_y
        spine_front_fb = (foot_positions["front_left"][front_back_idx] + foot_positions["front_right"][front_back_idx]) / 2
        spine_back_fb = (foot_positions["back_left"][front_back_idx] + foot_positions["back_right"][front_back_idx]) / 2

        # Head position - find actual head protrusion on the mesh
        # Look for vertices in the head direction beyond the front legs
        if head_at_min:
            head_region_mask = vertices[:, front_back_idx] < spine_front_fb
            tail_region_mask = vertices[:, front_back_idx] > spine_back_fb
        else:
            head_region_mask = vertices[:, front_back_idx] > spine_front_fb
            tail_region_mask = vertices[:, front_back_idx] < spine_back_fb

        # Find actual head position from mesh vertices
        head_region_verts = vertices[head_region_mask]
        if len(head_region_verts) > 10:
            # Head is where mesh extends furthest in head direction
            if head_at_min:
                head_fb_pos = np.percentile(head_region_verts[:, front_back_idx], 10)  # 10th percentile (min end)
            else:
                head_fb_pos = np.percentile(head_region_verts[:, front_back_idx], 90)  # 90th percentile (max end)
        else:
            # Fallback: slight offset from spine front
            head_fb_offset = mesh_length * 0.1
            head_fb_pos = spine_front_fb - head_fb_offset if head_at_min else spine_front_fb + head_fb_offset

        # Find actual tail position from mesh vertices
        tail_region_verts = vertices[tail_region_mask]
        if len(tail_region_verts) > 10:
            # Tail is where mesh extends furthest in tail direction
            if head_at_min:
                tail_fb_pos = np.percentile(tail_region_verts[:, front_back_idx], 90)  # 90th percentile (max end)
            else:
                tail_fb_pos = np.percentile(tail_region_verts[:, front_back_idx], 10)  # 10th percentile (min end)
        else:
            # Fallback: slight offset from spine back
            tail_fb_offset = mesh_length * 0.1
            tail_fb_pos = spine_back_fb + tail_fb_offset if head_at_min else spine_back_fb - tail_fb_offset

        # STRICT CLAMPING: Keep bones within actual mesh bounds
        head_fb_pos = np.clip(head_fb_pos, bbox_min[front_back_idx], bbox_max[front_back_idx])
        tail_fb_pos = np.clip(tail_fb_pos, bbox_min[front_back_idx], bbox_max[front_back_idx])

        # Head Y position - find highest point in front area
        if head_at_min:
            front_mask = vertices[:, front_back_idx] < fb_center
        else:
            front_mask = vertices[:, front_back_idx] > fb_center
        front_head_verts = vertices[front_mask]

        if len(front_head_verts) > 5:
            head_y = np.percentile(front_head_verts[:, 1], 85)  # 85th percentile height in front region
        else:
            head_y = spine_y + mesh_height * 0.15

        head_y = np.clip(head_y, bbox_min[1], bbox_max[1])

        # Tail Y position - at body height or slightly lower
        tail_y = spine_y - mesh_height * 0.05

        logger.info(f"Quadruped fitting: x_oriented={x_oriented}, head_at_min={head_at_min}")
        logger.info(f"  head_fb={head_fb_pos:.3f}, tail_fb={tail_fb_pos:.3f}, head_y={head_y:.3f}, spine_y={spine_y:.3f}")
        logger.info(f"  spine_front_fb={spine_front_fb:.3f}, spine_back_fb={spine_back_fb:.3f}")

        # Helper function to create position array with correct axis mapping
        def make_pos(fb_val, y_val, lr_val=None):
            """Create position array with correct axis mapping."""
            if lr_val is None:
                lr_val = lr_center
            pos = np.zeros(3)
            pos[front_back_idx] = fb_val
            pos[1] = y_val  # Y is always vertical
            pos[left_right_idx] = lr_val
            return pos

        # Now position all skeleton bones
        # Hips (root) - at the back, above back legs
        hips = skeleton.get_bone("Hips")
        if hips:
            hips.head = make_pos(spine_back_fb, spine_y)
            hips.tail = make_pos((spine_back_fb + spine_front_fb) / 2, spine_y)

        # Spine bones - along the back from hips toward head
        spine_names = ["Spine", "Spine1", "Spine2"]
        spine_fb_positions = np.linspace(spine_back_fb, spine_front_fb, len(spine_names) + 1)
        for i, name in enumerate(spine_names):
            bone = skeleton.get_bone(name)
            if bone:
                bone.head = make_pos(spine_fb_positions[i], spine_y)
                bone.tail = make_pos(spine_fb_positions[i + 1], spine_y)

        # Neck and head - position along the line from front spine to head
        neck = skeleton.get_bone("Neck")
        head_bone = skeleton.get_bone("Head")

        # Neck starts at front of spine
        neck_start_fb = spine_front_fb
        neck_start_y = spine_y

        # Neck goes 1/3 of the way towards head
        t_neck = 0.33
        neck_end_fb = spine_front_fb + (head_fb_pos - spine_front_fb) * t_neck
        neck_end_y = spine_y + (head_y - spine_y) * t_neck

        # Head goes from neck end to head position
        t_head = 0.66
        head_end_fb = spine_front_fb + (head_fb_pos - spine_front_fb) * t_head
        head_end_y = spine_y + (head_y - spine_y) * t_head

        logger.info(f"Neck: fb={neck_start_fb:.3f}->{neck_end_fb:.3f}, y={neck_start_y:.3f}->{neck_end_y:.3f}")
        logger.info(f"Head: fb={neck_end_fb:.3f}->{head_end_fb:.3f}, y={neck_end_y:.3f}->{head_end_y:.3f}")

        if neck:
            neck.head = make_pos(neck_start_fb, neck_start_y)
            neck.tail = make_pos(neck_end_fb, neck_end_y)
        if head_bone:
            head_bone.head = neck.tail.copy() if neck else make_pos(neck_end_fb, neck_end_y)
            head_bone.tail = make_pos(head_end_fb, head_end_y)

        # Tail bones - extend from back of hips WITHIN the mesh
        tail_names = ["Tail", "Tail1", "Tail2", "Tail3"]

        # Calculate tail extent - from spine_back towards tail_fb_pos but clamped
        if head_at_min:
            tail_direction = 1  # Tail extends in positive direction
            tail_end = min(tail_fb_pos, spine_back_fb + mesh_length * 0.25)  # Max 25% of body length
        else:
            tail_direction = -1  # Tail extends in negative direction
            tail_end = max(tail_fb_pos, spine_back_fb - mesh_length * 0.25)

        # Ensure tail_end is within mesh bounds
        tail_end = np.clip(tail_end, bbox_min[front_back_idx], bbox_max[front_back_idx])

        tail_fb_positions = np.linspace(spine_back_fb, tail_end, len(tail_names) + 1)

        logger.info(f"Tail positions from {spine_back_fb:.3f} to {tail_end:.3f} (direction={tail_direction})")

        # Find tail Y position from actual mesh vertices in tail region
        if head_at_min:
            tail_y_mask = vertices[:, front_back_idx] > spine_back_fb
        else:
            tail_y_mask = vertices[:, front_back_idx] < spine_back_fb
        tail_verts = vertices[tail_y_mask]
        if len(tail_verts) > 10:
            tail_y = np.percentile(tail_verts[:, 1], 70)  # 70th percentile height
        else:
            tail_y = spine_y - mesh_height * 0.05

        # Clamp tail Y to mesh bounds
        tail_y = np.clip(tail_y, bbox_min[1] + mesh_height * 0.2, bbox_max[1] - mesh_height * 0.1)

        for i, name in enumerate(tail_names):
            bone = skeleton.get_bone(name)
            if bone:
                tail_drop = i * mesh_height * 0.02  # Gentle drop
                bone_y = tail_y - tail_drop
                # Clamp each tail bone Y to mesh bounds
                bone_y = np.clip(bone_y, bbox_min[1], bbox_max[1])
                bone.head = make_pos(tail_fb_positions[i], bone_y)
                next_y = bone_y - mesh_height * 0.01
                next_y = np.clip(next_y, bbox_min[1], bbox_max[1])
                bone.tail = make_pos(tail_fb_positions[i + 1], next_y)

        # Position legs - use foot positions directly and interpolate towards spine
        leg_configs = [
            ("LeftFront", foot_positions["front_left"], True),
            ("RightFront", foot_positions["front_right"], True),
            ("LeftBack", foot_positions["back_left"], False),
            ("RightBack", foot_positions["back_right"], False),
        ]

        for prefix, foot_pos, is_front in leg_configs:
            # Shoulder/hip is at spine height, above the foot position
            # Use foot's left-right position but spine's front-back position for appropriate region
            foot_lr = foot_pos[left_right_idx]
            foot_fb = foot_pos[front_back_idx]

            # Shoulder/hip should be slightly towards center from foot
            shoulder_lr = foot_lr * 0.8 + lr_center * 0.2
            shoulder_fb = spine_front_fb if is_front else spine_back_fb

            shoulder_pos = make_pos(shoulder_fb, shoulder_hip_y, shoulder_lr)

            if is_front:
                bone_names = [f"{prefix}Shoulder", f"{prefix}UpperArm", f"{prefix}LowerArm", f"{prefix}Paw"]
            else:
                bone_names = [f"{prefix}Hip", f"{prefix}UpperLeg", f"{prefix}LowerLeg", f"{prefix}Paw"]

            # Calculate joint positions along the leg
            leg_length = shoulder_pos[1] - foot_pos[1]
            joint_heights = [
                shoulder_pos[1],  # Shoulder/hip
                shoulder_pos[1] - leg_length * 0.4,  # Upper joint
                shoulder_pos[1] - leg_length * 0.7,  # Lower joint
                foot_pos[1],  # Paw
            ]

            # Interpolate left-right position from shoulder towards foot
            lr_positions = [
                shoulder_lr,
                shoulder_lr * 0.7 + foot_lr * 0.3,
                shoulder_lr * 0.3 + foot_lr * 0.7,
                foot_lr,
            ]

            for i, name in enumerate(bone_names):
                bone = skeleton.get_bone(name)
                if bone:
                    # All leg bones stay at the foot's front-back position
                    bone_fb = foot_fb
                    if i < len(bone_names) - 1:
                        bone.head = make_pos(bone_fb, joint_heights[i], lr_positions[i])
                        bone.tail = make_pos(bone_fb, joint_heights[i + 1], lr_positions[i + 1])
                    else:
                        # Paw
                        bone.head = make_pos(bone_fb, foot_pos[1] + leg_length * 0.05, foot_lr)
                        bone.tail = make_pos(bone_fb, foot_pos[1], foot_lr)

        logger.info(f"Fitted quadruped skeleton to mesh: feet at {list(foot_positions.keys())}")

        # FINAL SAFETY PASS: Clamp all bones to mesh bounding box
        margin = mesh_height * 0.05  # 5% margin
        bbox_min_safe = bbox_min - margin
        bbox_max_safe = bbox_max + margin

        bones_clamped = 0
        for bone in skeleton.bones:
            orig_head = bone.head.copy()
            orig_tail = bone.tail.copy()

            # Clamp head and tail positions
            bone.head = np.clip(bone.head, bbox_min_safe, bbox_max_safe)
            bone.tail = np.clip(bone.tail, bbox_min_safe, bbox_max_safe)

            if not np.allclose(orig_head, bone.head) or not np.allclose(orig_tail, bone.tail):
                bones_clamped += 1
                logger.warning(f"Clamped bone {bone.name}: head {orig_head} -> {bone.head}, tail {orig_tail} -> {bone.tail}")

        if bones_clamped > 0:
            logger.info(f"Clamped {bones_clamped} bones to mesh bounds")

    def _detect_primary_axis(
        self,
        mesh: "trimesh.Trimesh",
        dim_x: float,
        dim_y: float,
        dim_z: float,
    ) -> tuple[bool, float]:
        """
        Detect the primary (front-back) axis of a quadruped mesh.

        Uses multiple heuristics:
        1. Dimension ratio (longer axis is usually front-back)
        2. Head/neck detection (vertical spread at one end indicates head)
        3. Leg cluster analysis (four feet should spread along both axes)

        Args:
            mesh: The quadruped mesh
            dim_x, dim_y, dim_z: Mesh dimensions

        Returns:
            Tuple of (x_oriented, confidence)
            x_oriented=True means front-back is along X axis
        """
        vertices = mesh.vertices
        bounds = mesh.bounds
        bbox_min, bbox_max = bounds[0], bounds[1]

        # Score for each axis being the front-back axis
        x_score = 0.0
        z_score = 0.0

        # Heuristic 1: Dimension ratio (longer axis is more likely front-back)
        # Quadrupeds are typically 1.5-3x longer than wide
        dim_ratio = dim_x / max(dim_z, 0.001)
        if dim_ratio > 1.1:  # X is longer
            x_score += min(1.5, dim_ratio - 1.0)  # Cap at 1.5
        elif dim_ratio < 0.9:  # Z is longer
            z_score += min(1.5, 1.0 / dim_ratio - 1.0)

        logger.debug(f"Dimension ratio X/Z={dim_ratio:.2f}, scores: X={x_score:.2f}, Z={z_score:.2f}")

        # Heuristic 2: Head detection via vertical extent at ends
        # The head end has more vertical spread (neck going up)
        for axis_idx, axis_name in [(0, "X"), (2, "Z")]:
            axis_min = bbox_min[axis_idx]
            axis_max = bbox_max[axis_idx]
            axis_range = axis_max - axis_min

            # Get vertices at each end (front 25% and back 25%)
            front_threshold = axis_min + axis_range * 0.25
            back_threshold = axis_max - axis_range * 0.25

            front_verts = vertices[vertices[:, axis_idx] < front_threshold]
            back_verts = vertices[vertices[:, axis_idx] > back_threshold]

            if len(front_verts) > 10 and len(back_verts) > 10:
                front_y_range = front_verts[:, 1].max() - front_verts[:, 1].min()
                back_y_range = back_verts[:, 1].max() - back_verts[:, 1].min()

                # If there's significant difference in Y range between ends,
                # this axis is likely the front-back axis
                y_diff = abs(front_y_range - back_y_range) / max(dim_y, 0.001)

                if y_diff > 0.15:  # At least 15% difference in Y range
                    if axis_idx == 0:
                        x_score += y_diff * 2
                    else:
                        z_score += y_diff * 2

                    logger.debug(f"Axis {axis_name} Y-range diff: front={front_y_range:.3f}, back={back_y_range:.3f}, diff={y_diff:.2f}")

        # Heuristic 3: Leg cluster analysis
        # Find lowest vertices (legs) and check their distribution
        ground_y = bbox_min[1]
        leg_region = dim_y * 0.3
        leg_verts = vertices[vertices[:, 1] < ground_y + leg_region]

        if len(leg_verts) > 50:
            # Check spread of leg vertices along each axis
            x_spread = leg_verts[:, 0].std()
            z_spread = leg_verts[:, 2].std()

            # The left-right axis should have less spread than front-back
            spread_ratio = x_spread / max(z_spread, 0.001)

            if spread_ratio > 1.3:  # X has more spread -> X is front-back
                x_score += 0.5
            elif spread_ratio < 0.7:  # Z has more spread -> Z is front-back
                z_score += 0.5

            logger.debug(f"Leg spread: X={x_spread:.3f}, Z={z_spread:.3f}, ratio={spread_ratio:.2f}")

        # Heuristic 4: Check for bilateral symmetry
        # Quadrupeds should be symmetric along the left-right axis
        # The axis with more symmetric vertex distribution is likely left-right
        x_symmetry = self._check_axis_symmetry(vertices, 0, bbox_center[0])
        z_symmetry = self._check_axis_symmetry(vertices, 2, bbox_center[2])

        if x_symmetry > z_symmetry * 1.2:  # X is more symmetric -> X is left-right
            z_score += 0.5
        elif z_symmetry > x_symmetry * 1.2:  # Z is more symmetric -> Z is left-right
            x_score += 0.5

        logger.debug(f"Symmetry: X={x_symmetry:.3f}, Z={z_symmetry:.3f}")

        # Final decision
        x_oriented = x_score > z_score
        total_score = x_score + z_score
        confidence = abs(x_score - z_score) / max(total_score, 0.001) if total_score > 0 else 0.5

        logger.info(f"Primary axis detection: X_score={x_score:.2f}, Z_score={z_score:.2f}, result={'X' if x_oriented else 'Z'}-oriented")

        return x_oriented, confidence

    def _check_axis_symmetry(self, vertices: np.ndarray, axis_idx: int, center: float) -> float:
        """
        Check how symmetric the mesh is along a given axis.

        Args:
            vertices: Mesh vertices
            axis_idx: Axis index (0=X, 2=Z)
            center: Center coordinate along the axis

        Returns:
            Symmetry score (higher = more symmetric)
        """
        # Split vertices into two halves
        left_verts = vertices[vertices[:, axis_idx] < center]
        right_verts = vertices[vertices[:, axis_idx] > center]

        if len(left_verts) < 10 or len(right_verts) < 10:
            return 0.5

        # Mirror the right side and compare distributions
        right_mirrored = right_verts.copy()
        right_mirrored[:, axis_idx] = 2 * center - right_mirrored[:, axis_idx]

        # Compare point cloud distributions using their bounding boxes
        left_bounds = np.array([left_verts.min(axis=0), left_verts.max(axis=0)])
        right_bounds = np.array([right_mirrored.min(axis=0), right_mirrored.max(axis=0)])

        # Calculate overlap between bounding boxes
        overlap = np.minimum(left_bounds[1], right_bounds[1]) - np.maximum(left_bounds[0], right_bounds[0])
        overlap = np.maximum(overlap, 0)
        overlap_volume = np.prod(overlap)

        left_volume = np.prod(left_bounds[1] - left_bounds[0] + 0.001)
        right_volume = np.prod(right_bounds[1] - right_bounds[0] + 0.001)

        # Symmetry score based on overlap relative to volumes
        symmetry = 2 * overlap_volume / (left_volume + right_volume)

        return symmetry

    def _detect_quadruped_orientation(self, mesh: "trimesh.Trimesh") -> bool:
        """
        Detect if the quadruped mesh is facing positive or negative Z.

        The skeleton template has head at negative Z. If the mesh head is at
        positive Z, we need to flip the skeleton.

        Args:
            mesh: The quadruped mesh

        Returns:
            True if skeleton needs to be flipped (head is at positive Z)
        """
        vertices = mesh.vertices
        bounds = mesh.bounds
        z_min, z_max = bounds[0][2], bounds[1][2]
        z_center = (z_min + z_max) / 2
        z_range = z_max - z_min

        # Get vertices at each end (front 20% and back 20%)
        front_threshold = z_min + z_range * 0.2
        back_threshold = z_max - z_range * 0.2

        front_vertices = vertices[vertices[:, 2] < front_threshold]
        back_vertices = vertices[vertices[:, 2] > back_threshold]

        if len(front_vertices) < 5 or len(back_vertices) < 5:
            return False

        # The head end typically has:
        # 1. More vertical extent (neck going up)
        # 2. More spread in the Y direction
        front_y_range = front_vertices[:, 1].max() - front_vertices[:, 1].min()
        back_y_range = back_vertices[:, 1].max() - back_vertices[:, 1].min()

        # Also check Y centroid - head/neck region is typically higher
        front_y_avg = front_vertices[:, 1].mean()
        back_y_avg = back_vertices[:, 1].mean()

        # Score each end (higher score = more likely to be head)
        front_score = front_y_range + (front_y_avg - back_y_avg)
        back_score = back_y_range + (back_y_avg - front_y_avg)

        logger.debug(f"Orientation detection: front_score={front_score:.3f}, back_score={back_score:.3f}")

        # If back has higher score, head is at positive Z, need to flip
        # (skeleton template has head at negative Z)
        return back_score > front_score

    def _flip_skeleton_z(self, skeleton: "Skeleton", center: np.ndarray) -> None:
        """
        Flip the skeleton along the Z axis around the center point.

        Args:
            skeleton: The skeleton to flip
            center: Center point to flip around
        """
        for bone in skeleton.get_all_bones():
            # Flip Z coordinate around center
            bone.head[2] = 2 * center[2] - bone.head[2]
            bone.tail[2] = 2 * center[2] - bone.tail[2]

    def _compute_skinning_weights(
        self,
        mesh: "trimesh.Trimesh",
        skeleton: Skeleton,
    ) -> SkinningData:
        """
        Compute skinning weights using proximity-based algorithm.

        This is a simplified implementation. Production would use:
        - Bounded Biharmonic Weights (BBW)
        - Heat diffusion
        - Machine learning (UniRig neural network)
        """
        vertices = mesh.vertices
        bones = skeleton.get_all_bones()

        # Only use deforming bones
        deform_bones = [b for b in bones if b.deform]

        weights_list = []

        for vi, vertex in enumerate(vertices):
            bone_weights = {}

            # Calculate distance to each bone
            distances = []
            for bone in deform_bones:
                # Distance from vertex to bone segment
                dist = self._point_to_segment_distance(
                    vertex,
                    bone.head,
                    bone.tail,
                )
                distances.append((bone.name, dist))

            # Sort by distance
            distances.sort(key=lambda x: x[1])

            # Take top 4 closest bones (standard for game engines)
            max_influences = 4
            closest = distances[:max_influences]

            # Convert distances to weights using inverse distance weighting
            if closest:
                total_inv_dist = sum(1.0 / max(d, 0.001) for _, d in closest)

                for bone_name, dist in closest:
                    weight = (1.0 / max(dist, 0.001)) / total_inv_dist
                    if weight > 0.01:  # Threshold small weights
                        bone_weights[bone_name] = weight

                # Normalize weights
                total = sum(bone_weights.values())
                if total > 0:
                    bone_weights = {k: v / total for k, v in bone_weights.items()}

            weights_list.append(WeightData(
                vertex_index=vi,
                bone_weights=bone_weights,
            ))

        return SkinningData(
            vertex_count=len(vertices),
            weights=weights_list,
            max_influences=4,
        )

    def _point_to_segment_distance(
        self,
        point: np.ndarray,
        seg_start: np.ndarray,
        seg_end: np.ndarray,
    ) -> float:
        """Calculate distance from point to line segment."""
        segment = seg_end - seg_start
        segment_length_sq = np.dot(segment, segment)

        if segment_length_sq < 1e-10:
            # Degenerate segment
            return float(np.linalg.norm(point - seg_start))

        # Project point onto segment
        t = max(0, min(1, np.dot(point - seg_start, segment) / segment_length_sq))
        projection = seg_start + t * segment

        return float(np.linalg.norm(point - projection))

    def _export_rigged_mesh(
        self,
        mesh: "trimesh.Trimesh",
        skeleton: Skeleton,
        skinning: SkinningData,
        output_path: Path,
    ) -> None:
        """
        Export mesh with skeleton and weights as GLB.

        Note: Full GLTF skeleton export requires pygltflib or similar.
        For now, we export the mesh and store skeleton data separately.
        """
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Export base mesh
        mesh.export(str(output_path))

        # Store skeleton data alongside
        skeleton_path = output_path.with_suffix(".skeleton.json")
        skeleton_data = skeleton.to_skeleton_data()

        import json
        with open(skeleton_path, "w") as f:
            json.dump(skeleton_data.model_dump(), f, indent=2)

        logger.info(f"Exported rigged mesh to {output_path}")
        logger.info(f"Exported skeleton data to {skeleton_path}")
