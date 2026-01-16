"""
Bone validation for animation compatibility.

Validates that a skeleton has the required bones for specific animation types,
and provides warnings for missing bones.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from .schemas import AnimationType
from ..rigging.schemas import SkeletonData

logger = logging.getLogger(__name__)


@dataclass
class BoneRequirement:
    """Bone requirement specification."""
    name: str
    required: bool = False  # If True, animation will fail without it
    description: str = ""


@dataclass
class ValidationResult:
    """Result of bone validation."""
    is_valid: bool
    animation_type: AnimationType
    character_type: str
    missing_required: list[str] = field(default_factory=list)
    missing_optional: list[str] = field(default_factory=list)
    found_bones: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def coverage_percent(self) -> float:
        """Percentage of bones found vs total expected."""
        total = len(self.found_bones) + len(self.missing_required) + len(self.missing_optional)
        if total == 0:
            return 100.0
        return (len(self.found_bones) / total) * 100


# Required bones for each animation type
HUMANOID_BONE_REQUIREMENTS: dict[AnimationType, list[BoneRequirement]] = {
    AnimationType.IDLE: [
        BoneRequirement("Spine", required=True, description="Core breathing animation"),
        BoneRequirement("Hips", required=True, description="Weight shift movement"),
        BoneRequirement("Head", required=False, description="Head micro-movements"),
        BoneRequirement("LeftShoulder", required=False, description="Shoulder breathing"),
        BoneRequirement("RightShoulder", required=False, description="Shoulder breathing"),
    ],
    AnimationType.WALK: [
        BoneRequirement("Hips", required=True, description="Hip bounce and sway"),
        BoneRequirement("LeftUpLeg", required=True, description="Left thigh rotation"),
        BoneRequirement("RightUpLeg", required=True, description="Right thigh rotation"),
        BoneRequirement("LeftLeg", required=False, description="Left knee rotation"),
        BoneRequirement("RightLeg", required=False, description="Right knee rotation"),
        BoneRequirement("LeftArm", required=False, description="Left arm swing"),
        BoneRequirement("RightArm", required=False, description="Right arm swing"),
        BoneRequirement("Spine1", required=False, description="Spine twist"),
    ],
    AnimationType.RUN: [
        BoneRequirement("Hips", required=True, description="Hip movement"),
        BoneRequirement("LeftUpLeg", required=True, description="Left thigh rotation"),
        BoneRequirement("RightUpLeg", required=True, description="Right thigh rotation"),
        BoneRequirement("LeftLeg", required=False, description="Left knee rotation"),
        BoneRequirement("RightLeg", required=False, description="Right knee rotation"),
        BoneRequirement("LeftArm", required=False, description="Left arm pump"),
        BoneRequirement("RightArm", required=False, description="Right arm pump"),
        BoneRequirement("Spine", required=False, description="Spine lean"),
    ],
    AnimationType.ATTACK: [
        BoneRequirement("Spine", required=True, description="Torso rotation"),
        BoneRequirement("RightArm", required=True, description="Attack arm movement"),
        BoneRequirement("RightForeArm", required=False, description="Forearm rotation"),
        BoneRequirement("RightHand", required=False, description="Hand rotation"),
        BoneRequirement("LeftArm", required=False, description="Balance arm"),
        BoneRequirement("Hips", required=False, description="Hip rotation"),
    ],
}

QUADRUPED_BONE_REQUIREMENTS: dict[AnimationType, list[BoneRequirement]] = {
    AnimationType.IDLE: [
        BoneRequirement("Spine", required=True, description="Breathing animation"),
        BoneRequirement("Tail", required=False, description="Tail sway"),
        BoneRequirement("Head", required=False, description="Head movement"),
    ],
    AnimationType.TROT: [
        BoneRequirement("Hips", required=True, description="Body movement"),
        BoneRequirement("FrontLeftLeg", required=True, description="Front left leg"),
        BoneRequirement("FrontRightLeg", required=True, description="Front right leg"),
        BoneRequirement("BackLeftLeg", required=True, description="Back left leg"),
        BoneRequirement("BackRightLeg", required=True, description="Back right leg"),
        BoneRequirement("Spine", required=False, description="Spine flex"),
    ],
    AnimationType.TAIL_WAG: [
        BoneRequirement("Tail", required=True, description="Tail bone"),
        BoneRequirement("Tail1", required=False, description="Second tail segment"),
        BoneRequirement("Tail2", required=False, description="Third tail segment"),
    ],
    AnimationType.BITE: [
        BoneRequirement("Head", required=True, description="Head movement"),
        BoneRequirement("Jaw", required=False, description="Jaw opening"),
        BoneRequirement("Neck", required=False, description="Neck lunge"),
    ],
}


class BoneValidator:
    """Validates skeleton bones against animation requirements."""

    # Common bone name aliases for mapping
    BONE_ALIASES: dict[str, list[str]] = {
        # Humanoid
        "Hips": ["Hips", "hips", "pelvis", "Pelvis", "Root", "root", "mixamorig:Hips"],
        "Spine": ["Spine", "spine", "Spine_01", "spine_01", "mixamorig:Spine"],
        "Spine1": ["Spine1", "spine1", "Spine_02", "spine_02", "Chest", "chest", "mixamorig:Spine1"],
        "Head": ["Head", "head", "mixamorig:Head"],
        "Neck": ["Neck", "neck", "mixamorig:Neck"],
        "LeftShoulder": ["LeftShoulder", "shoulder_l", "Shoulder.L", "mixamorig:LeftShoulder"],
        "RightShoulder": ["RightShoulder", "shoulder_r", "Shoulder.R", "mixamorig:RightShoulder"],
        "LeftArm": ["LeftArm", "arm_l", "UpperArm.L", "mixamorig:LeftArm"],
        "RightArm": ["RightArm", "arm_r", "UpperArm.R", "mixamorig:RightArm"],
        "LeftForeArm": ["LeftForeArm", "forearm_l", "LowerArm.L", "mixamorig:LeftForeArm"],
        "RightForeArm": ["RightForeArm", "forearm_r", "LowerArm.R", "mixamorig:RightForeArm"],
        "LeftHand": ["LeftHand", "hand_l", "Hand.L", "mixamorig:LeftHand"],
        "RightHand": ["RightHand", "hand_r", "Hand.R", "mixamorig:RightHand"],
        "LeftUpLeg": ["LeftUpLeg", "thigh_l", "UpperLeg.L", "mixamorig:LeftUpLeg"],
        "RightUpLeg": ["RightUpLeg", "thigh_r", "UpperLeg.R", "mixamorig:RightUpLeg"],
        "LeftLeg": ["LeftLeg", "shin_l", "LowerLeg.L", "mixamorig:LeftLeg"],
        "RightLeg": ["RightLeg", "shin_r", "LowerLeg.R", "mixamorig:RightLeg"],
        "LeftFoot": ["LeftFoot", "foot_l", "Foot.L", "mixamorig:LeftFoot"],
        "RightFoot": ["RightFoot", "foot_r", "Foot.R", "mixamorig:RightFoot"],
        # Quadruped
        "Tail": ["Tail", "tail", "Tail_01", "tail_01"],
        "Tail1": ["Tail1", "Tail_02", "tail_02"],
        "Tail2": ["Tail2", "Tail_03", "tail_03"],
        "Jaw": ["Jaw", "jaw", "Mouth", "mouth"],
        "FrontLeftLeg": ["FrontLeftLeg", "Front_Left_Leg", "leg_front_l", "FrontLeftUpperArm"],
        "FrontRightLeg": ["FrontRightLeg", "Front_Right_Leg", "leg_front_r", "FrontRightUpperArm"],
        "BackLeftLeg": ["BackLeftLeg", "Back_Left_Leg", "leg_back_l", "BackLeftUpperLeg"],
        "BackRightLeg": ["BackRightLeg", "Back_Right_Leg", "leg_back_r", "BackRightUpperLeg"],
    }

    def __init__(self, skeleton: SkeletonData):
        """Initialize validator with skeleton data."""
        self.skeleton = skeleton
        self.bone_names = {bone.name for bone in skeleton.bones}

    def _find_bone(self, canonical_name: str) -> Optional[str]:
        """
        Find a bone by canonical name, checking aliases.

        Returns the actual bone name if found, None otherwise.
        """
        # Direct match
        if canonical_name in self.bone_names:
            return canonical_name

        # Check aliases
        aliases = self.BONE_ALIASES.get(canonical_name, [])
        for alias in aliases:
            if alias in self.bone_names:
                return alias

        return None

    def validate(
        self,
        animation_type: AnimationType,
        character_type: str,
    ) -> ValidationResult:
        """
        Validate skeleton against animation requirements.

        Args:
            animation_type: Type of animation to validate for
            character_type: "humanoid" or "quadruped"

        Returns:
            ValidationResult with missing bones and warnings
        """
        # Get requirements for this animation type
        if character_type == "humanoid":
            requirements = HUMANOID_BONE_REQUIREMENTS.get(animation_type, [])
        else:
            requirements = QUADRUPED_BONE_REQUIREMENTS.get(animation_type, [])

        missing_required = []
        missing_optional = []
        found_bones = []
        warnings = []

        for req in requirements:
            actual_bone = self._find_bone(req.name)
            if actual_bone:
                found_bones.append(actual_bone)
                if actual_bone != req.name:
                    logger.debug(f"Mapped bone '{req.name}' -> '{actual_bone}'")
            else:
                if req.required:
                    missing_required.append(req.name)
                    warnings.append(
                        f"Missing required bone '{req.name}': {req.description}. "
                        "Animation may not work correctly."
                    )
                else:
                    missing_optional.append(req.name)
                    warnings.append(
                        f"Missing optional bone '{req.name}': {req.description}. "
                        "This feature will be skipped."
                    )

        is_valid = len(missing_required) == 0

        result = ValidationResult(
            is_valid=is_valid,
            animation_type=animation_type,
            character_type=character_type,
            missing_required=missing_required,
            missing_optional=missing_optional,
            found_bones=found_bones,
            warnings=warnings,
        )

        # Log summary
        if not is_valid:
            logger.warning(
                f"Skeleton validation failed for {animation_type.value} "
                f"({character_type}): missing required bones: {missing_required}"
            )
        elif missing_optional:
            logger.info(
                f"Skeleton validation passed with warnings for {animation_type.value}: "
                f"missing optional bones: {missing_optional}"
            )

        return result


def validate_skeleton_for_animation(
    skeleton: SkeletonData,
    animation_type: AnimationType,
    character_type: str,
) -> ValidationResult:
    """
    Convenience function to validate a skeleton for an animation type.

    Args:
        skeleton: Skeleton data from rigging
        animation_type: Animation to validate for
        character_type: "humanoid" or "quadruped"

    Returns:
        ValidationResult with missing bones and warnings
    """
    validator = BoneValidator(skeleton)
    return validator.validate(animation_type, character_type)
