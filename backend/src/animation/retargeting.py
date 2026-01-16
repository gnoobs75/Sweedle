"""Animation retargeting from Mixamo to Sweedle skeletons.

This module handles converting Mixamo animation data to work with
Sweedle's skeleton structure, including bone name mapping and
optional bind pose compensation.
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Optional

from .fbx_parser import MixamoAnimationData, AnimationTrack
from .mixamo_mapping import (
    get_sweedle_bone_name,
    validate_bone_mapping,
    REQUIRED_BONES,
)
from .schemas import AnimationData, KeyframeTrack
from ..rigging.schemas import SkeletonData, BoneData

logger = logging.getLogger(__name__)


@dataclass
class RetargetingConfig:
    """Configuration for animation retargeting."""
    # Scale root motion to target skeleton height
    scale_root_motion: bool = True
    # Skip bones that don't exist in target skeleton
    skip_unmapped_bones: bool = True
    # Apply bind pose compensation
    compensate_bind_pose: bool = False
    # Minimum bone coverage required (0.0 to 1.0)
    min_coverage: float = 0.5
    # Clamp rotation values to prevent gimbal issues
    clamp_rotations: bool = True


@dataclass
class RetargetingResult:
    """Result of animation retargeting."""
    success: bool
    animation_data: Optional[AnimationData] = None
    error: Optional[str] = None
    warnings: list[str] = field(default_factory=list)
    mapped_bones: int = 0
    total_bones: int = 0
    coverage_percent: float = 0.0


def quaternion_multiply(q1: tuple, q2: tuple) -> tuple:
    """Multiply two quaternions (x, y, z, w format)."""
    x1, y1, z1, w1 = q1
    x2, y2, z2, w2 = q2
    return (
        w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
        w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
        w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
        w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
    )


def quaternion_inverse(q: tuple) -> tuple:
    """Compute inverse of quaternion (x, y, z, w format)."""
    x, y, z, w = q
    norm_sq = x * x + y * y + z * z + w * w
    if norm_sq < 1e-10:
        return (0.0, 0.0, 0.0, 1.0)
    inv_norm = 1.0 / norm_sq
    return (-x * inv_norm, -y * inv_norm, -z * inv_norm, w * inv_norm)


def normalize_quaternion(q: tuple) -> tuple:
    """Normalize a quaternion to unit length."""
    x, y, z, w = q
    norm = math.sqrt(x * x + y * y + z * z + w * w)
    if norm < 1e-10:
        return (0.0, 0.0, 0.0, 1.0)
    return (x / norm, y / norm, z / norm, w / norm)


class AnimationRetargeter:
    """Retarget animations from Mixamo to Sweedle skeleton."""

    def __init__(self, config: Optional[RetargetingConfig] = None):
        self.config = config or RetargetingConfig()

    def retarget(
        self,
        source_animation: MixamoAnimationData,
        target_skeleton: SkeletonData,
        animation_name: Optional[str] = None,
    ) -> RetargetingResult:
        """Retarget a Mixamo animation to the target skeleton.

        Args:
            source_animation: Parsed Mixamo animation data
            target_skeleton: Target Sweedle skeleton
            animation_name: Optional custom name for the animation

        Returns:
            RetargetingResult with the retargeted animation data
        """
        warnings = []

        # Validate bone mapping
        source_bone_names = list(source_animation.bones.keys())
        mapping_result = validate_bone_mapping(source_bone_names)

        coverage = mapping_result["coverage_percent"] / 100.0
        if coverage < self.config.min_coverage:
            return RetargetingResult(
                success=False,
                error=f"Insufficient bone coverage: {coverage:.1%} (minimum: {self.config.min_coverage:.1%})",
                mapped_bones=mapping_result["mapped_bones"],
                total_bones=mapping_result["total_bones"],
                coverage_percent=mapping_result["coverage_percent"],
            )

        if not mapping_result["has_all_required"]:
            warnings.append(
                f"Missing required bones: {', '.join(mapping_result['missing_required'])}"
            )

        # Build target bone lookup
        target_bones = {bone.name: bone for bone in target_skeleton.bones}

        # Calculate scale factor for root motion
        scale_factor = 1.0
        if self.config.scale_root_motion:
            scale_factor = self._calculate_scale_factor(
                source_animation, target_skeleton
            )
            if scale_factor != 1.0:
                logger.info(f"Applying root motion scale: {scale_factor:.3f}")

        # Group source tracks by bone
        bone_tracks: dict[str, list[AnimationTrack]] = {}
        for track in source_animation.tracks:
            if track.bone_name not in bone_tracks:
                bone_tracks[track.bone_name] = []
            bone_tracks[track.bone_name].append(track)

        # Convert tracks
        output_tracks: list[KeyframeTrack] = []
        mapped_count = 0

        for mixamo_bone, tracks in bone_tracks.items():
            sweedle_bone = get_sweedle_bone_name(mixamo_bone)

            if sweedle_bone is None:
                if not self.config.skip_unmapped_bones:
                    warnings.append(f"Unmapped bone: {mixamo_bone}")
                continue

            if sweedle_bone not in target_bones:
                warnings.append(
                    f"Bone '{sweedle_bone}' not in target skeleton"
                )
                continue

            # Convert this bone's tracks
            keyframe_track = self._convert_bone_tracks(
                tracks,
                sweedle_bone,
                target_bones[sweedle_bone],
                scale_factor,
            )

            if keyframe_track:
                output_tracks.append(keyframe_track)
                mapped_count += 1

        if not output_tracks:
            return RetargetingResult(
                success=False,
                error="No animation tracks could be converted",
                warnings=warnings,
                mapped_bones=mapping_result["mapped_bones"],
                total_bones=mapping_result["total_bones"],
                coverage_percent=mapping_result["coverage_percent"],
            )

        # Create animation data
        animation_data = AnimationData(
            name=animation_name or source_animation.name,
            duration=source_animation.duration_seconds,
            frame_rate=source_animation.fps,
            tracks=output_tracks,
        )

        return RetargetingResult(
            success=True,
            animation_data=animation_data,
            warnings=warnings,
            mapped_bones=mapped_count,
            total_bones=len(bone_tracks),
            coverage_percent=mapped_count / len(bone_tracks) * 100 if bone_tracks else 0,
        )

    def _calculate_scale_factor(
        self,
        source: MixamoAnimationData,
        target: SkeletonData,
    ) -> float:
        """Calculate scale factor between source and target skeletons.

        Uses hip height as reference.
        """
        # Find hip bone in source
        source_hip = None
        for name, bone in source.bones.items():
            sweedle_name = get_sweedle_bone_name(name)
            if sweedle_name == "Hips":
                source_hip = bone
                break

        if source_hip is None:
            return 1.0

        # Find hip bone in target
        target_hip = None
        for bone in target.bones:
            if bone.name == "Hips":
                target_hip = bone
                break

        if target_hip is None:
            return 1.0

        # Calculate heights (Y coordinate of hip)
        source_height = source_hip.head[1]
        target_height = target_hip.head_position[1]

        if abs(source_height) < 0.001:
            return 1.0

        return target_height / source_height

    def _convert_bone_tracks(
        self,
        source_tracks: list[AnimationTrack],
        bone_name: str,
        target_bone: BoneData,
        scale_factor: float,
    ) -> Optional[KeyframeTrack]:
        """Convert Mixamo animation tracks for a single bone.

        Args:
            source_tracks: List of FCurve tracks for this bone
            bone_name: Target bone name
            target_bone: Target bone data
            scale_factor: Scale factor for positions

        Returns:
            KeyframeTrack with converted animation data
        """
        # Organize tracks by channel
        channels: dict[str, dict[int, list[tuple[float, float]]]] = {
            "rotation_quaternion": {},
            "location": {},
            "scale": {},
        }

        for track in source_tracks:
            if track.channel in channels:
                channels[track.channel][track.index] = track.keyframes

        # Get keyframe times from rotation (most common)
        times = []
        if channels["rotation_quaternion"]:
            first_channel = list(channels["rotation_quaternion"].values())[0]
            times = [kf[0] for kf in first_channel]
        elif channels["location"]:
            first_channel = list(channels["location"].values())[0]
            times = [kf[0] for kf in first_channel]

        if not times:
            return None

        # Convert times from frames to seconds
        # Assume 30fps if not specified (Mixamo default)
        times_seconds = [t / 30.0 for t in times]

        # Extract rotation keyframes
        rotations: Optional[list[list[float]]] = None
        if all(i in channels["rotation_quaternion"] for i in range(4)):
            rotations = []
            for frame_idx in range(len(times)):
                quat = [
                    channels["rotation_quaternion"][i][frame_idx][1]
                    for i in range(4)
                ]
                # Normalize and optionally clamp
                quat = list(normalize_quaternion(tuple(quat)))
                rotations.append(quat)

        # Extract position keyframes
        positions: Optional[list[list[float]]] = None
        if all(i in channels["location"] for i in range(3)):
            positions = []
            for frame_idx in range(len(times)):
                pos = [
                    channels["location"][i][frame_idx][1] * scale_factor
                    for i in range(3)
                ]
                positions.append(pos)

        # Extract scale keyframes (usually not animated in Mixamo)
        scales: Optional[list[list[float]]] = None
        if all(i in channels["scale"] for i in range(3)):
            scales = []
            for frame_idx in range(len(times)):
                scale = [
                    channels["scale"][i][frame_idx][1]
                    for i in range(3)
                ]
                scales.append(scale)

        # Skip if no useful data
        if rotations is None and positions is None and scales is None:
            return None

        return KeyframeTrack(
            bone_name=bone_name,
            times=times_seconds,
            positions=positions,
            rotations=rotations,
            scales=scales,
        )


def retarget_mixamo_animation(
    source_animation: MixamoAnimationData,
    target_skeleton: SkeletonData,
    animation_name: Optional[str] = None,
    config: Optional[RetargetingConfig] = None,
) -> RetargetingResult:
    """Convenience function to retarget a Mixamo animation.

    Args:
        source_animation: Parsed Mixamo animation from FBX
        target_skeleton: Target Sweedle skeleton
        animation_name: Optional custom name
        config: Optional retargeting configuration

    Returns:
        RetargetingResult with retargeted animation or error
    """
    retargeter = AnimationRetargeter(config)
    return retargeter.retarget(source_animation, target_skeleton, animation_name)


async def validate_mixamo_for_skeleton(
    animation: MixamoAnimationData,
    skeleton: SkeletonData,
) -> dict:
    """Validate if a Mixamo animation can be applied to a skeleton.

    Returns validation info without actually performing retargeting.
    """
    source_bones = list(animation.bones.keys())
    mapping_result = validate_bone_mapping(source_bones)

    # Check which target bones are available
    target_bone_names = {bone.name for bone in skeleton.bones}
    mapped_to_target = 0
    missing_in_target = []

    for mixamo_name, sweedle_name in mapping_result["mapping"].items():
        if sweedle_name in target_bone_names:
            mapped_to_target += 1
        else:
            missing_in_target.append(sweedle_name)

    return {
        "is_compatible": mapping_result["is_valid"] and mapped_to_target > 0,
        "source_bones": len(source_bones),
        "mapped_bones": mapping_result["mapped_bones"],
        "target_bones": len(target_bone_names),
        "bones_available_in_target": mapped_to_target,
        "missing_in_target": missing_in_target,
        "coverage_percent": mapping_result["coverage_percent"],
        "has_all_required": mapping_result["has_all_required"],
        "missing_required": mapping_result["missing_required"],
        "warnings": mapping_result["warnings"],
        "animation_info": {
            "name": animation.name,
            "duration_seconds": animation.duration_seconds,
            "fps": animation.fps,
            "track_count": len(animation.tracks),
        },
    }
