"""
Landmark-based skeleton generation.

Instead of positioning individual bones, users place key landmark markers
and the system generates the full bone chain between them.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np
import logging

from .types import Skeleton, Bone
from ..schemas import CharacterType

logger = logging.getLogger(__name__)


@dataclass
class Landmark:
    """A key position marker for skeleton generation."""
    name: str
    position: np.ndarray  # [x, y, z]
    description: str
    color: str  # For visualization


# Quadruped landmarks - only 8 key points to position
QUADRUPED_LANDMARKS = {
    "Hips": Landmark("Hips", np.array([0, 0.6, 0]), "Center of body/pelvis", "#ff4080"),
    "Chest": Landmark("Chest", np.array([0, 0.7, -0.6]), "Front of body where front legs attach", "#ff8040"),
    "Head": Landmark("Head", np.array([0, 0.9, -1.0]), "Top/front of head", "#40ff80"),
    "TailTip": Landmark("TailTip", np.array([0, 0.35, 0.7]), "End of tail", "#8040ff"),
    "FrontLeftPaw": Landmark("FrontLeftPaw", np.array([0.15, 0.02, -0.65]), "Front left foot", "#40ffff"),
    "FrontRightPaw": Landmark("FrontRightPaw", np.array([-0.15, 0.02, -0.65]), "Front right foot", "#40ffff"),
    "BackLeftPaw": Landmark("BackLeftPaw", np.array([0.15, 0.02, 0.05]), "Back left foot", "#ffff40"),
    "BackRightPaw": Landmark("BackRightPaw", np.array([-0.15, 0.02, 0.05]), "Back right foot", "#ffff40"),
}

# Humanoid landmarks - 10 key points
HUMANOID_LANDMARKS = {
    "Hips": Landmark("Hips", np.array([0, 1.0, 0]), "Center of pelvis", "#ff4080"),
    "Chest": Landmark("Chest", np.array([0, 1.4, 0]), "Center of chest", "#ff8040"),
    "Head": Landmark("Head", np.array([0, 1.75, 0]), "Top of head", "#40ff80"),
    "LeftHand": Landmark("LeftHand", np.array([0.6, 1.2, 0]), "Left hand/wrist", "#40ffff"),
    "RightHand": Landmark("RightHand", np.array([-0.6, 1.2, 0]), "Right hand/wrist", "#40ffff"),
    "LeftFoot": Landmark("LeftFoot", np.array([0.1, 0.05, 0]), "Left foot/ankle", "#ffff40"),
    "RightFoot": Landmark("RightFoot", np.array([-0.1, 0.05, 0]), "Right foot/ankle", "#ffff40"),
}


def get_default_landmarks(character_type: CharacterType) -> Dict[str, List[float]]:
    """Get default landmark positions for a character type."""
    if character_type == CharacterType.QUADRUPED:
        return {name: lm.position.tolist() for name, lm in QUADRUPED_LANDMARKS.items()}
    else:
        return {name: lm.position.tolist() for name, lm in HUMANOID_LANDMARKS.items()}


def get_landmark_info(character_type: CharacterType) -> List[dict]:
    """Get landmark metadata for UI."""
    landmarks = QUADRUPED_LANDMARKS if character_type == CharacterType.QUADRUPED else HUMANOID_LANDMARKS
    return [
        {
            "name": lm.name,
            "description": lm.description,
            "color": lm.color,
            "defaultPosition": lm.position.tolist(),
        }
        for lm in landmarks.values()
    ]


def generate_skeleton_from_landmarks(
    landmarks: Dict[str, List[float]],
    character_type: CharacterType,
) -> Skeleton:
    """
    Generate a full skeleton from landmark positions.

    Args:
        landmarks: Dict mapping landmark names to [x, y, z] positions
        character_type: Type of character (quadruped or humanoid)

    Returns:
        Complete Skeleton with all bones generated from landmarks
    """
    # Convert to numpy arrays
    lm = {name: np.array(pos) for name, pos in landmarks.items()}

    if character_type == CharacterType.QUADRUPED:
        return _generate_quadruped_skeleton(lm)
    else:
        return _generate_humanoid_skeleton(lm)


def _create_bone(
    name: str,
    parent_name: Optional[str],
    head: np.ndarray,
    tail: np.ndarray,
    bones_by_name: Dict[str, Bone],
    connected: bool = False,
    deform: bool = True,
) -> Bone:
    """Helper to create a bone and register it."""
    bone = Bone(
        name=name,
        head=head.copy(),
        tail=tail.copy(),
        connected=connected,
        deform=deform,
    )
    bones_by_name[name] = bone

    # Set up parent relationship
    if parent_name and parent_name in bones_by_name:
        parent = bones_by_name[parent_name]
        parent.add_child(bone)

    return bone


def _generate_quadruped_skeleton(lm: Dict[str, np.ndarray]) -> Skeleton:
    """Generate quadruped skeleton from landmarks."""
    bones_by_name: Dict[str, Bone] = {}

    # Ensure all required landmarks exist
    required = ["Hips", "Chest", "Head", "TailTip", "FrontLeftPaw", "FrontRightPaw", "BackLeftPaw", "BackRightPaw"]
    for name in required:
        if name not in lm:
            raise ValueError(f"Missing required landmark: {name}")

    hips_pos = lm["Hips"]
    chest_pos = lm["Chest"]
    head_pos = lm["Head"]
    tail_tip = lm["TailTip"]

    # === SPINE (Hips -> Chest) ===
    spine_positions = _interpolate_chain(hips_pos, chest_pos, 4)
    root_bone = _create_bone("Hips", None, spine_positions[0], spine_positions[1], bones_by_name)
    _create_bone("Spine", "Hips", spine_positions[1], spine_positions[2], bones_by_name, connected=True)
    _create_bone("Spine1", "Spine", spine_positions[2], spine_positions[3], bones_by_name, connected=True)

    # === NECK & HEAD (Chest -> Head) ===
    neck_positions = _interpolate_chain(chest_pos, head_pos, 4)
    _create_bone("Neck", "Spine1", neck_positions[0], neck_positions[1], bones_by_name, connected=True)
    _create_bone("Neck1", "Neck", neck_positions[1], neck_positions[2], bones_by_name, connected=True)
    _create_bone("Head", "Neck1", neck_positions[2], neck_positions[3], bones_by_name, connected=True)

    # Jaw
    head_dir = (head_pos - neck_positions[2])
    head_dir = head_dir / (np.linalg.norm(head_dir) + 0.001)
    jaw_head = head_pos - np.array([0, 0.05, 0])
    jaw_tail = jaw_head + head_dir * 0.15
    _create_bone("Jaw", "Head", jaw_head, jaw_tail, bones_by_name)

    # Ears
    ear_offset = 0.05
    ear_height = 0.1
    _create_bone("LeftEar", "Head", head_pos + np.array([ear_offset, 0, 0]), head_pos + np.array([ear_offset * 1.5, ear_height, 0]), bones_by_name)
    _create_bone("RightEar", "Head", head_pos + np.array([-ear_offset, 0, 0]), head_pos + np.array([-ear_offset * 1.5, ear_height, 0]), bones_by_name)

    # === TAIL (Hips -> TailTip) ===
    tail_positions = _interpolate_chain(hips_pos, tail_tip, 6)
    _create_bone("Tail", "Hips", tail_positions[0], tail_positions[1], bones_by_name)
    _create_bone("Tail1", "Tail", tail_positions[1], tail_positions[2], bones_by_name, connected=True)
    _create_bone("Tail2", "Tail1", tail_positions[2], tail_positions[3], bones_by_name, connected=True)
    _create_bone("Tail3", "Tail2", tail_positions[3], tail_positions[4], bones_by_name, connected=True)
    _create_bone("Tail4", "Tail3", tail_positions[4], tail_positions[5], bones_by_name, connected=True)

    # === FRONT LEFT LEG ===
    _add_quadruped_leg_v2(bones_by_name, "LeftFront", chest_pos, lm["FrontLeftPaw"], is_front=True, side_offset=0.1)

    # === FRONT RIGHT LEG ===
    _add_quadruped_leg_v2(bones_by_name, "RightFront", chest_pos, lm["FrontRightPaw"], is_front=True, side_offset=-0.1)

    # === BACK LEFT LEG ===
    _add_quadruped_leg_v2(bones_by_name, "LeftBack", hips_pos, lm["BackLeftPaw"], is_front=False, side_offset=0.1)

    # === BACK RIGHT LEG ===
    _add_quadruped_leg_v2(bones_by_name, "RightBack", hips_pos, lm["BackRightPaw"], is_front=False, side_offset=-0.1)

    # Create skeleton with proper structure
    skeleton = Skeleton(root=root_bone, bones=bones_by_name, character_type=CharacterType.QUADRUPED)

    logger.info(f"Generated quadruped skeleton with {len(bones_by_name)} bones from 8 landmarks")
    return skeleton


def _add_quadruped_leg_v2(
    bones_by_name: Dict[str, Bone],
    prefix: str,
    body_pos: np.ndarray,
    paw_pos: np.ndarray,
    is_front: bool,
    side_offset: float,
) -> None:
    """
    Add a quadruped leg bone chain from body to paw.

    The leg has: Shoulder/Hip -> UpperArm/UpperLeg -> LowerArm/LowerLeg -> Paw -> Toes
    """
    # Calculate shoulder/hip position (slightly offset from body center)
    shoulder_pos = body_pos.copy()
    shoulder_pos[0] = side_offset  # X offset for left/right

    # Leg segments with proper joint positions
    leg_vector = paw_pos - shoulder_pos
    leg_length = np.linalg.norm(leg_vector)

    # Joint positions as fractions of leg length
    upper_pos = shoulder_pos + leg_vector * 0.35
    lower_pos = shoulder_pos + leg_vector * 0.65
    paw_top = shoulder_pos + leg_vector * 0.92

    # Add slight forward/backward bend to joints for natural pose
    if is_front:
        lower_pos[2] += leg_length * 0.05
        parent = "Spine1"
        bone_names = [f"{prefix}Shoulder", f"{prefix}UpperArm", f"{prefix}LowerArm", f"{prefix}Paw", f"{prefix}Toes"]
    else:
        lower_pos[2] -= leg_length * 0.05
        parent = "Hips"
        bone_names = [f"{prefix}Hip", f"{prefix}UpperLeg", f"{prefix}LowerLeg", f"{prefix}Paw", f"{prefix}Toes"]

    # Toes extend forward from paw
    toes_end = paw_pos.copy()
    toes_end[2] -= 0.08
    toes_end[1] = paw_pos[1]

    _create_bone(bone_names[0], parent, shoulder_pos, upper_pos, bones_by_name)
    _create_bone(bone_names[1], bone_names[0], upper_pos, lower_pos, bones_by_name, connected=True)
    _create_bone(bone_names[2], bone_names[1], lower_pos, paw_top, bones_by_name, connected=True)
    _create_bone(bone_names[3], bone_names[2], paw_top, paw_pos, bones_by_name, connected=True)
    _create_bone(bone_names[4], bone_names[3], paw_pos, toes_end, bones_by_name, connected=True)


def _generate_humanoid_skeleton(lm: Dict[str, np.ndarray]) -> Skeleton:
    """Generate humanoid skeleton from landmarks."""
    bones_by_name: Dict[str, Bone] = {}

    # Ensure all required landmarks exist
    required = ["Hips", "Chest", "Head", "LeftHand", "RightHand", "LeftFoot", "RightFoot"]
    for name in required:
        if name not in lm:
            raise ValueError(f"Missing required landmark: {name}")

    hips_pos = lm["Hips"]
    chest_pos = lm["Chest"]
    head_pos = lm["Head"]

    # === SPINE (Hips -> Chest -> Head) ===
    spine_mid = (hips_pos + chest_pos) / 2
    neck_pos = chest_pos + (head_pos - chest_pos) * 0.3

    root_bone = _create_bone("Hips", None, hips_pos, spine_mid, bones_by_name)
    _create_bone("Spine", "Hips", spine_mid, chest_pos, bones_by_name, connected=True)
    _create_bone("Chest", "Spine", chest_pos, neck_pos, bones_by_name, connected=True)
    _create_bone("Neck", "Chest", neck_pos, neck_pos + (head_pos - neck_pos) * 0.5, bones_by_name, connected=True)
    _create_bone("Head", "Neck", neck_pos + (head_pos - neck_pos) * 0.5, head_pos, bones_by_name, connected=True)

    # === LEFT ARM (Chest -> LeftHand) ===
    _add_humanoid_arm_v2(bones_by_name, "Left", chest_pos, lm["LeftHand"], side_offset=0.15)

    # === RIGHT ARM (Chest -> RightHand) ===
    _add_humanoid_arm_v2(bones_by_name, "Right", chest_pos, lm["RightHand"], side_offset=-0.15)

    # === LEFT LEG (Hips -> LeftFoot) ===
    _add_humanoid_leg_v2(bones_by_name, "Left", hips_pos, lm["LeftFoot"], side_offset=0.1)

    # === RIGHT LEG (Hips -> RightFoot) ===
    _add_humanoid_leg_v2(bones_by_name, "Right", hips_pos, lm["RightFoot"], side_offset=-0.1)

    skeleton = Skeleton(root=root_bone, bones=bones_by_name, character_type=CharacterType.HUMANOID)

    logger.info(f"Generated humanoid skeleton with {len(bones_by_name)} bones from 7 landmarks")
    return skeleton


def _add_humanoid_arm_v2(
    bones_by_name: Dict[str, Bone],
    side: str,
    chest: np.ndarray,
    hand: np.ndarray,
    side_offset: float,
) -> None:
    """Add humanoid arm bone chain."""
    shoulder = chest.copy()
    shoulder[0] = side_offset
    shoulder[1] = chest[1] - 0.05

    arm_vector = hand - shoulder
    upper_arm_end = shoulder + arm_vector * 0.45
    forearm_end = shoulder + arm_vector * 0.85

    _create_bone(f"{side}Shoulder", "Chest", shoulder - np.array([side_offset * 0.5, 0, 0]), shoulder, bones_by_name)
    _create_bone(f"{side}Arm", f"{side}Shoulder", shoulder, upper_arm_end, bones_by_name, connected=True)
    _create_bone(f"{side}ForeArm", f"{side}Arm", upper_arm_end, forearm_end, bones_by_name, connected=True)
    _create_bone(f"{side}Hand", f"{side}ForeArm", forearm_end, hand, bones_by_name, connected=True)


def _add_humanoid_leg_v2(
    bones_by_name: Dict[str, Bone],
    side: str,
    hips: np.ndarray,
    foot: np.ndarray,
    side_offset: float,
) -> None:
    """Add humanoid leg bone chain."""
    hip_joint = hips.copy()
    hip_joint[0] = side_offset

    leg_vector = foot - hip_joint
    upper_leg_end = hip_joint + leg_vector * 0.45
    lower_leg_end = hip_joint + leg_vector * 0.9

    upper_leg_end[2] += 0.02

    _create_bone(f"{side}UpLeg", "Hips", hip_joint, upper_leg_end, bones_by_name)
    _create_bone(f"{side}Leg", f"{side}UpLeg", upper_leg_end, lower_leg_end, bones_by_name, connected=True)
    _create_bone(f"{side}Foot", f"{side}Leg", lower_leg_end, foot, bones_by_name, connected=True)

    toes_end = foot.copy()
    toes_end[2] -= 0.1
    toes_end[1] = foot[1]
    _create_bone(f"{side}ToeBase", f"{side}Foot", foot, toes_end, bones_by_name, connected=True)


def _interpolate_chain(start: np.ndarray, end: np.ndarray, num_points: int) -> List[np.ndarray]:
    """
    Interpolate positions along a chain from start to end.

    Args:
        start: Starting position
        end: Ending position
        num_points: Number of points (including start and end)

    Returns:
        List of interpolated positions
    """
    positions = []
    for i in range(num_points):
        t = i / (num_points - 1)
        pos = start * (1 - t) + end * t
        positions.append(pos)
    return positions


def fit_landmarks_to_mesh(
    mesh_bounds: Tuple[np.ndarray, np.ndarray],
    character_type: CharacterType,
) -> Dict[str, List[float]]:
    """
    Fit default landmarks to mesh bounding box.

    Args:
        mesh_bounds: Tuple of (min, max) bounds
        character_type: Type of character

    Returns:
        Dict of landmark positions fitted to mesh
    """
    bbox_min, bbox_max = mesh_bounds
    bbox_center = (bbox_min + bbox_max) / 2
    bbox_size = bbox_max - bbox_min

    # Get default landmarks
    default_lm = get_default_landmarks(character_type)

    # Calculate scale factor based on mesh size
    if character_type == CharacterType.QUADRUPED:
        # Quadruped: scale based on length (Z or X, whichever is longer)
        mesh_length = max(bbox_size[0], bbox_size[2])
        default_length = 1.8  # Default quadruped is about 1.8 units long
        scale = mesh_length / default_length * 0.9  # 90% to keep inside mesh
    else:
        # Humanoid: scale based on height (Y)
        mesh_height = bbox_size[1]
        default_height = 1.8  # Default humanoid is 1.8 units tall
        scale = mesh_height / default_height * 0.9

    # Scale and translate landmarks
    fitted = {}
    for name, pos in default_lm.items():
        pos_array = np.array(pos)
        # Scale around origin, then translate to mesh center
        scaled = pos_array * scale
        # Adjust Y to sit on ground
        if character_type == CharacterType.QUADRUPED:
            scaled[1] = bbox_min[1] + (pos_array[1] * scale)
        else:
            scaled[1] = bbox_min[1] + (pos_array[1] * scale)
        # Center X and Z
        scaled[0] += bbox_center[0]
        scaled[2] += bbox_center[2]
        fitted[name] = scaled.tolist()

    return fitted
