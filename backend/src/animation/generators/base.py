"""
Base class for procedural animation generators.
"""

from abc import ABC, abstractmethod
from typing import Optional
import math
import logging

from ..schemas import AnimationParameters, AnimationData, KeyframeTrack
from ..bone_validator import BoneValidator
from ...rigging.schemas import SkeletonData, BoneData

logger = logging.getLogger(__name__)


class BaseAnimationGenerator(ABC):
    """Base class for procedural animation generators."""

    def __init__(self, skeleton: SkeletonData, fps: int = 30):
        """
        Initialize generator with skeleton data.

        Args:
            skeleton: Skeleton data from rigged asset
            fps: Frames per second for animation
        """
        self.skeleton = skeleton
        self.fps = fps
        self.bone_map: dict[str, BoneData] = {
            b.name: b for b in skeleton.bones
        }
        self.bone_names: set[str] = set(self.bone_map.keys())
        # Cache resolved bone names: canonical -> actual
        self._resolved_bones: dict[str, str] = {}

    @abstractmethod
    def generate(
        self,
        duration: float,
        params: AnimationParameters,
    ) -> AnimationData:
        """
        Generate animation data.

        Args:
            duration: Animation duration in seconds
            params: Animation parameters (speed, intensity, etc.)

        Returns:
            AnimationData with keyframe tracks
        """
        pass

    def _resolve_bone_name(self, canonical_name: str) -> Optional[str]:
        """
        Resolve a canonical bone name to the actual bone name in the skeleton.

        Uses aliasing to support different naming conventions (Mixamo, Blender, etc.)

        Args:
            canonical_name: Standard bone name (e.g., "Hips", "LeftArm")

        Returns:
            Actual bone name in skeleton, or None if not found
        """
        # Check cache first
        if canonical_name in self._resolved_bones:
            return self._resolved_bones[canonical_name]

        # Direct match
        if canonical_name in self.bone_names:
            self._resolved_bones[canonical_name] = canonical_name
            return canonical_name

        # Check aliases
        aliases = BoneValidator.BONE_ALIASES.get(canonical_name, [])
        for alias in aliases:
            if alias in self.bone_names:
                logger.debug(f"Resolved bone '{canonical_name}' -> '{alias}'")
                self._resolved_bones[canonical_name] = alias
                return alias

        # Not found
        self._resolved_bones[canonical_name] = None
        return None

    def _get_bone(self, name: str) -> Optional[BoneData]:
        """Get bone by canonical name, resolving aliases."""
        actual_name = self._resolve_bone_name(name)
        if actual_name:
            return self.bone_map.get(actual_name)
        return None

    def _has_bone(self, name: str) -> bool:
        """Check if bone exists in skeleton (with alias resolution)."""
        return self._resolve_bone_name(name) is not None

    def _get_actual_bone_name(self, canonical_name: str) -> str:
        """
        Get the actual bone name for use in keyframe tracks.

        Returns the resolved name, or the canonical name if not found
        (for cases where we want to try anyway).
        """
        return self._resolve_bone_name(canonical_name) or canonical_name

    def _create_times(self, duration: float, params: AnimationParameters) -> list[float]:
        """Create time array for keyframes."""
        adjusted_duration = duration / params.speed
        frame_count = int(adjusted_duration * self.fps)
        return [i / self.fps for i in range(frame_count)]

    def _euler_to_quaternion(
        self,
        x: float,
        y: float,
        z: float,
    ) -> list[float]:
        """
        Convert Euler angles (radians) to quaternion [x, y, z, w].

        Uses XYZ rotation order.
        """
        # Half angles
        cx = math.cos(x / 2)
        sx = math.sin(x / 2)
        cy = math.cos(y / 2)
        sy = math.sin(y / 2)
        cz = math.cos(z / 2)
        sz = math.sin(z / 2)

        # XYZ rotation order
        qw = cx * cy * cz + sx * sy * sz
        qx = sx * cy * cz - cx * sy * sz
        qy = cx * sy * cz + sx * cy * sz
        qz = cx * cy * sz - sx * sy * cz

        return [qx, qy, qz, qw]

    def _identity_quaternion(self) -> list[float]:
        """Return identity quaternion [x, y, z, w]."""
        return [0.0, 0.0, 0.0, 1.0]

    def _slerp_quaternion(
        self,
        q1: list[float],
        q2: list[float],
        t: float,
    ) -> list[float]:
        """
        Spherical linear interpolation between quaternions.

        Args:
            q1: Start quaternion [x, y, z, w]
            q2: End quaternion [x, y, z, w]
            t: Interpolation factor (0-1)

        Returns:
            Interpolated quaternion [x, y, z, w]
        """
        # Dot product
        dot = sum(a * b for a, b in zip(q1, q2))

        # If negative, negate one quaternion to take shorter path
        if dot < 0:
            q2 = [-v for v in q2]
            dot = -dot

        # Clamp dot product
        dot = min(1.0, max(-1.0, dot))

        # If very close, use linear interpolation
        if dot > 0.9995:
            result = [a + t * (b - a) for a, b in zip(q1, q2)]
            # Normalize
            length = math.sqrt(sum(v * v for v in result))
            return [v / length for v in result]

        # Spherical interpolation
        theta_0 = math.acos(dot)
        theta = theta_0 * t
        sin_theta = math.sin(theta)
        sin_theta_0 = math.sin(theta_0)

        s0 = math.cos(theta) - dot * sin_theta / sin_theta_0
        s1 = sin_theta / sin_theta_0

        return [s0 * a + s1 * b for a, b in zip(q1, q2)]

    def _create_rotation_track(
        self,
        bone_name: str,
        times: list[float],
        rotations: list[list[float]],
    ) -> KeyframeTrack:
        """Create a rotation keyframe track with resolved bone name."""
        actual_name = self._get_actual_bone_name(bone_name)
        return KeyframeTrack(
            bone_name=actual_name,
            times=times,
            rotations=rotations,
        )

    def _create_position_track(
        self,
        bone_name: str,
        times: list[float],
        positions: list[list[float]],
    ) -> KeyframeTrack:
        """Create a position keyframe track with resolved bone name."""
        actual_name = self._get_actual_bone_name(bone_name)
        return KeyframeTrack(
            bone_name=actual_name,
            times=times,
            positions=positions,
        )
