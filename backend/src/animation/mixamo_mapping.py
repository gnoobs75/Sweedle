"""Mixamo to Sweedle bone name mapping.

This module provides comprehensive bone name mapping between Mixamo's
naming convention and Sweedle's internal skeleton structure.

Mixamo uses the "mixamorig:" prefix for all bones. This mapping handles
the translation for animation retargeting.
"""

from typing import Optional


# Complete Mixamo to Sweedle bone mapping for humanoid skeleton
MIXAMO_TO_SWEEDLE_HUMANOID: dict[str, str] = {
    # Root / Hips
    "mixamorig:Hips": "Hips",

    # Spine chain
    "mixamorig:Spine": "Spine",
    "mixamorig:Spine1": "Spine1",
    "mixamorig:Spine2": "Spine2",

    # Neck and Head
    "mixamorig:Neck": "Neck",
    "mixamorig:Head": "Head",
    "mixamorig:HeadTop_End": "HeadTop",

    # Left Arm
    "mixamorig:LeftShoulder": "LeftShoulder",
    "mixamorig:LeftArm": "LeftUpperArm",
    "mixamorig:LeftForeArm": "LeftLowerArm",
    "mixamorig:LeftHand": "LeftHand",

    # Left Hand Fingers
    "mixamorig:LeftHandThumb1": "LeftThumb1",
    "mixamorig:LeftHandThumb2": "LeftThumb2",
    "mixamorig:LeftHandThumb3": "LeftThumb3",
    "mixamorig:LeftHandThumb4": "LeftThumb4",
    "mixamorig:LeftHandIndex1": "LeftIndex1",
    "mixamorig:LeftHandIndex2": "LeftIndex2",
    "mixamorig:LeftHandIndex3": "LeftIndex3",
    "mixamorig:LeftHandIndex4": "LeftIndex4",
    "mixamorig:LeftHandMiddle1": "LeftMiddle1",
    "mixamorig:LeftHandMiddle2": "LeftMiddle2",
    "mixamorig:LeftHandMiddle3": "LeftMiddle3",
    "mixamorig:LeftHandMiddle4": "LeftMiddle4",
    "mixamorig:LeftHandRing1": "LeftRing1",
    "mixamorig:LeftHandRing2": "LeftRing2",
    "mixamorig:LeftHandRing3": "LeftRing3",
    "mixamorig:LeftHandRing4": "LeftRing4",
    "mixamorig:LeftHandPinky1": "LeftPinky1",
    "mixamorig:LeftHandPinky2": "LeftPinky2",
    "mixamorig:LeftHandPinky3": "LeftPinky3",
    "mixamorig:LeftHandPinky4": "LeftPinky4",

    # Right Arm
    "mixamorig:RightShoulder": "RightShoulder",
    "mixamorig:RightArm": "RightUpperArm",
    "mixamorig:RightForeArm": "RightLowerArm",
    "mixamorig:RightHand": "RightHand",

    # Right Hand Fingers
    "mixamorig:RightHandThumb1": "RightThumb1",
    "mixamorig:RightHandThumb2": "RightThumb2",
    "mixamorig:RightHandThumb3": "RightThumb3",
    "mixamorig:RightHandThumb4": "RightThumb4",
    "mixamorig:RightHandIndex1": "RightIndex1",
    "mixamorig:RightHandIndex2": "RightIndex2",
    "mixamorig:RightHandIndex3": "RightIndex3",
    "mixamorig:RightHandIndex4": "RightIndex4",
    "mixamorig:RightHandMiddle1": "RightMiddle1",
    "mixamorig:RightHandMiddle2": "RightMiddle2",
    "mixamorig:RightHandMiddle3": "RightMiddle3",
    "mixamorig:RightHandMiddle4": "RightMiddle4",
    "mixamorig:RightHandRing1": "RightRing1",
    "mixamorig:RightHandRing2": "RightRing2",
    "mixamorig:RightHandRing3": "RightRing3",
    "mixamorig:RightHandRing4": "RightRing4",
    "mixamorig:RightHandPinky1": "RightPinky1",
    "mixamorig:RightHandPinky2": "RightPinky2",
    "mixamorig:RightHandPinky3": "RightPinky3",
    "mixamorig:RightHandPinky4": "RightPinky4",

    # Left Leg
    "mixamorig:LeftUpLeg": "LeftUpperLeg",
    "mixamorig:LeftLeg": "LeftLowerLeg",
    "mixamorig:LeftFoot": "LeftFoot",
    "mixamorig:LeftToeBase": "LeftToe",
    "mixamorig:LeftToe_End": "LeftToeEnd",

    # Right Leg
    "mixamorig:RightUpLeg": "RightUpperLeg",
    "mixamorig:RightLeg": "RightLowerLeg",
    "mixamorig:RightFoot": "RightFoot",
    "mixamorig:RightToeBase": "RightToe",
    "mixamorig:RightToe_End": "RightToeEnd",
}

# Alternative Mixamo bone names (some animations use slightly different names)
MIXAMO_ALTERNATIVES: dict[str, str] = {
    # Alternative arm names
    "mixamorig:LeftArm": "LeftUpperArm",
    "mixamorig:RightArm": "RightUpperArm",
    "mixamorig:LeftForeArm": "LeftLowerArm",
    "mixamorig:RightForeArm": "RightLowerArm",

    # Alternative leg names
    "mixamorig:LeftUpLeg": "LeftUpperLeg",
    "mixamorig:RightUpLeg": "RightUpperLeg",
    "mixamorig:LeftLeg": "LeftLowerLeg",
    "mixamorig:RightLeg": "RightLowerLeg",

    # Without prefix (some exports don't have mixamorig:)
    "Hips": "Hips",
    "Spine": "Spine",
    "Spine1": "Spine1",
    "Spine2": "Spine2",
    "Neck": "Neck",
    "Head": "Head",
}

# Reverse mapping (Sweedle to Mixamo)
SWEEDLE_TO_MIXAMO_HUMANOID: dict[str, str] = {
    v: k for k, v in MIXAMO_TO_SWEEDLE_HUMANOID.items()
}


# Core bones that MUST be mapped for basic animation
REQUIRED_BONES = {
    "Hips",
    "Spine",
    "Spine1",
    "Spine2",
    "Neck",
    "Head",
    "LeftShoulder",
    "LeftUpperArm",
    "LeftLowerArm",
    "LeftHand",
    "RightShoulder",
    "RightUpperArm",
    "RightLowerArm",
    "RightHand",
    "LeftUpperLeg",
    "LeftLowerLeg",
    "LeftFoot",
    "RightUpperLeg",
    "RightLowerLeg",
    "RightFoot",
}


def get_sweedle_bone_name(mixamo_name: str) -> Optional[str]:
    """Convert a Mixamo bone name to Sweedle bone name.

    Args:
        mixamo_name: The Mixamo bone name (with or without prefix)

    Returns:
        The corresponding Sweedle bone name, or None if not mapped
    """
    # Try direct mapping first
    if mixamo_name in MIXAMO_TO_SWEEDLE_HUMANOID:
        return MIXAMO_TO_SWEEDLE_HUMANOID[mixamo_name]

    # Try alternatives
    if mixamo_name in MIXAMO_ALTERNATIVES:
        return MIXAMO_ALTERNATIVES[mixamo_name]

    # Try without prefix
    if mixamo_name.startswith("mixamorig:"):
        base_name = mixamo_name.replace("mixamorig:", "")
        if base_name in MIXAMO_ALTERNATIVES:
            return MIXAMO_ALTERNATIVES[base_name]

    # Try adding prefix
    prefixed = f"mixamorig:{mixamo_name}"
    if prefixed in MIXAMO_TO_SWEEDLE_HUMANOID:
        return MIXAMO_TO_SWEEDLE_HUMANOID[prefixed]

    return None


def get_mixamo_bone_name(sweedle_name: str) -> Optional[str]:
    """Convert a Sweedle bone name to Mixamo bone name.

    Args:
        sweedle_name: The Sweedle bone name

    Returns:
        The corresponding Mixamo bone name, or None if not mapped
    """
    return SWEEDLE_TO_MIXAMO_HUMANOID.get(sweedle_name)


def validate_bone_mapping(
    source_bones: list[str],
    require_all: bool = False,
) -> dict:
    """Validate how well source bones map to Sweedle skeleton.

    Args:
        source_bones: List of bone names from the source animation
        require_all: If True, require all REQUIRED_BONES to be present

    Returns:
        Dict with mapping statistics and warnings
    """
    mapped = []
    unmapped = []
    mapped_names = {}

    for bone in source_bones:
        sweedle_name = get_sweedle_bone_name(bone)
        if sweedle_name:
            mapped.append(bone)
            mapped_names[bone] = sweedle_name
        else:
            unmapped.append(bone)

    # Check required bones
    mapped_sweedle = set(mapped_names.values())
    missing_required = REQUIRED_BONES - mapped_sweedle
    has_all_required = len(missing_required) == 0

    coverage = len(mapped) / len(source_bones) if source_bones else 0

    warnings = []
    if not has_all_required:
        warnings.append(f"Missing required bones: {', '.join(sorted(missing_required))}")
    if unmapped:
        # Only warn about first few unmapped
        preview = unmapped[:5]
        if len(unmapped) > 5:
            preview.append(f"...and {len(unmapped) - 5} more")
        warnings.append(f"Unmapped bones: {', '.join(preview)}")

    return {
        "total_bones": len(source_bones),
        "mapped_bones": len(mapped),
        "unmapped_bones": len(unmapped),
        "coverage_percent": round(coverage * 100, 1),
        "has_all_required": has_all_required,
        "missing_required": list(missing_required),
        "mapping": mapped_names,
        "unmapped_list": unmapped,
        "warnings": warnings,
        "is_valid": has_all_required or coverage >= 0.5,
    }
