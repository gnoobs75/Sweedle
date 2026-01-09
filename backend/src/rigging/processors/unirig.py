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

    async def _analyze_mesh(self, mesh: "trimesh.Trimesh") -> CharacterAnalysis:
        """Analyze mesh geometry to determine character type."""
        bounds = mesh.bounds
        bbox_min = bounds[0]
        bbox_max = bounds[1]
        dimensions = bbox_max - bbox_min

        width = dimensions[0]  # X
        height = dimensions[1]  # Y (up)
        depth = dimensions[2]  # Z

        height_to_width = height / max(width, 0.001)

        # Heuristics for character type
        is_humanoid = (
            rigging_settings.HUMANOID_HEIGHT_RATIO_MIN <= height_to_width <= rigging_settings.HUMANOID_HEIGHT_RATIO_MAX
        )
        is_quadruped = height_to_width < rigging_settings.QUADRUPED_HEIGHT_RATIO_MAX

        # Calculate confidence
        if is_humanoid:
            confidence = min(1.0, (height_to_width - 1.0) / 2.0)
        elif is_quadruped:
            confidence = min(1.0, 1.0 - height_to_width / 1.5)
        else:
            confidence = 0.3

        return CharacterAnalysis(
            bounding_box=(tuple(bbox_min), tuple(bbox_max)),
            dimensions=(width, height, depth),
            height_to_width_ratio=height_to_width,
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
        """Create skeleton fitted to mesh dimensions."""
        from ..skeleton import create_humanoid_skeleton, create_quadruped_skeleton

        # Create base skeleton from template
        if character_type == CharacterType.QUADRUPED:
            skeleton = create_quadruped_skeleton()
        else:
            skeleton = create_humanoid_skeleton()

        # Scale skeleton to mesh
        mesh_height = analysis.dimensions[1]
        mesh_center = np.array(analysis.center_of_mass)

        skeleton.scale_to_mesh(mesh_height, mesh_center)

        return skeleton

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
