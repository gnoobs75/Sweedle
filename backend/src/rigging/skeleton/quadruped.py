"""
Quadruped skeleton template.

Standard quadruped rig for four-legged creatures (dogs, cats, horses, etc.).
"""

from ..schemas import CharacterType
from .types import Skeleton, create_skeleton_from_template

# Quadruped skeleton template with 45 bones
# Positions are normalized for a medium-sized quadruped
QUADRUPED_TEMPLATE = {
    "name": "Quadruped",
    "description": "Standard quadruped skeleton for four-legged creatures",
    "bone_count": 45,
    "bones": [
        # Root/Hips (center of body)
        {"name": "Hips", "parent": None, "head": (0, 0.6, 0), "tail": (0, 0.6, -0.1), "deform": True},

        # Spine chain (horizontal)
        {"name": "Spine", "parent": "Hips", "head": (0, 0.6, -0.1), "tail": (0, 0.65, -0.3), "connected": True},
        {"name": "Spine1", "parent": "Spine", "head": (0, 0.65, -0.3), "tail": (0, 0.7, -0.5), "connected": True},
        {"name": "Spine2", "parent": "Spine1", "head": (0, 0.7, -0.5), "tail": (0, 0.75, -0.7), "connected": True},

        # Neck and Head
        {"name": "Neck", "parent": "Spine2", "head": (0, 0.75, -0.7), "tail": (0, 0.85, -0.85), "connected": True},
        {"name": "Neck1", "parent": "Neck", "head": (0, 0.85, -0.85), "tail": (0, 0.9, -1.0), "connected": True},
        {"name": "Head", "parent": "Neck1", "head": (0, 0.9, -1.0), "tail": (0, 0.9, -1.2), "connected": True},

        # Jaw
        {"name": "Jaw", "parent": "Head", "head": (0, 0.85, -1.1), "tail": (0, 0.82, -1.25)},

        # Ears
        {"name": "LeftEar", "parent": "Head", "head": (0.05, 0.95, -1.0), "tail": (0.08, 1.05, -1.0)},
        {"name": "RightEar", "parent": "Head", "head": (-0.05, 0.95, -1.0), "tail": (-0.08, 1.05, -1.0)},

        # Tail chain
        {"name": "Tail", "parent": "Hips", "head": (0, 0.55, 0.05), "tail": (0, 0.5, 0.2)},
        {"name": "Tail1", "parent": "Tail", "head": (0, 0.5, 0.2), "tail": (0, 0.45, 0.35), "connected": True},
        {"name": "Tail2", "parent": "Tail1", "head": (0, 0.45, 0.35), "tail": (0, 0.4, 0.5), "connected": True},
        {"name": "Tail3", "parent": "Tail2", "head": (0, 0.4, 0.5), "tail": (0, 0.35, 0.65), "connected": True},
        {"name": "Tail4", "parent": "Tail3", "head": (0, 0.35, 0.65), "tail": (0, 0.3, 0.8), "connected": True},

        # Front Left Leg
        {"name": "LeftFrontShoulder", "parent": "Spine2", "head": (0.1, 0.7, -0.65), "tail": (0.15, 0.6, -0.65)},
        {"name": "LeftFrontUpperArm", "parent": "LeftFrontShoulder", "head": (0.15, 0.6, -0.65), "tail": (0.15, 0.35, -0.65), "connected": True},
        {"name": "LeftFrontLowerArm", "parent": "LeftFrontUpperArm", "head": (0.15, 0.35, -0.65), "tail": (0.15, 0.1, -0.65), "connected": True},
        {"name": "LeftFrontPaw", "parent": "LeftFrontLowerArm", "head": (0.15, 0.1, -0.65), "tail": (0.15, 0.02, -0.7), "connected": True},
        {"name": "LeftFrontToes", "parent": "LeftFrontPaw", "head": (0.15, 0.02, -0.7), "tail": (0.15, 0, -0.78), "connected": True},

        # Front Right Leg
        {"name": "RightFrontShoulder", "parent": "Spine2", "head": (-0.1, 0.7, -0.65), "tail": (-0.15, 0.6, -0.65)},
        {"name": "RightFrontUpperArm", "parent": "RightFrontShoulder", "head": (-0.15, 0.6, -0.65), "tail": (-0.15, 0.35, -0.65), "connected": True},
        {"name": "RightFrontLowerArm", "parent": "RightFrontUpperArm", "head": (-0.15, 0.35, -0.65), "tail": (-0.15, 0.1, -0.65), "connected": True},
        {"name": "RightFrontPaw", "parent": "RightFrontLowerArm", "head": (-0.15, 0.1, -0.65), "tail": (-0.15, 0.02, -0.7), "connected": True},
        {"name": "RightFrontToes", "parent": "RightFrontPaw", "head": (-0.15, 0.02, -0.7), "tail": (-0.15, 0, -0.78), "connected": True},

        # Back Left Leg
        {"name": "LeftBackHip", "parent": "Hips", "head": (0.1, 0.55, 0), "tail": (0.15, 0.45, 0.05)},
        {"name": "LeftBackUpperLeg", "parent": "LeftBackHip", "head": (0.15, 0.45, 0.05), "tail": (0.15, 0.25, 0), "connected": True},
        {"name": "LeftBackLowerLeg", "parent": "LeftBackUpperLeg", "head": (0.15, 0.25, 0), "tail": (0.15, 0.1, 0.05), "connected": True},
        {"name": "LeftBackPaw", "parent": "LeftBackLowerLeg", "head": (0.15, 0.1, 0.05), "tail": (0.15, 0.02, 0), "connected": True},
        {"name": "LeftBackToes", "parent": "LeftBackPaw", "head": (0.15, 0.02, 0), "tail": (0.15, 0, -0.08), "connected": True},

        # Back Right Leg
        {"name": "RightBackHip", "parent": "Hips", "head": (-0.1, 0.55, 0), "tail": (-0.15, 0.45, 0.05)},
        {"name": "RightBackUpperLeg", "parent": "RightBackHip", "head": (-0.15, 0.45, 0.05), "tail": (-0.15, 0.25, 0), "connected": True},
        {"name": "RightBackLowerLeg", "parent": "RightBackUpperLeg", "head": (-0.15, 0.25, 0), "tail": (-0.15, 0.1, 0.05), "connected": True},
        {"name": "RightBackPaw", "parent": "RightBackLowerLeg", "head": (-0.15, 0.1, 0.05), "tail": (-0.15, 0.02, 0), "connected": True},
        {"name": "RightBackToes", "parent": "RightBackPaw", "head": (-0.15, 0.02, 0), "tail": (-0.15, 0, -0.08), "connected": True},
    ],
}


def create_quadruped_skeleton() -> Skeleton:
    """
    Create a standard quadruped skeleton from template.

    Returns:
        Skeleton configured for quadruped creatures
    """
    return create_skeleton_from_template(QUADRUPED_TEMPLATE, CharacterType.QUADRUPED)


# Bone groups for easier manipulation
QUADRUPED_BONE_GROUPS = {
    "spine": ["Hips", "Spine", "Spine1", "Spine2"],
    "neck_head": ["Neck", "Neck1", "Head", "Jaw"],
    "ears": ["LeftEar", "RightEar"],
    "tail": ["Tail", "Tail1", "Tail2", "Tail3", "Tail4"],
    "front_left_leg": ["LeftFrontShoulder", "LeftFrontUpperArm", "LeftFrontLowerArm", "LeftFrontPaw", "LeftFrontToes"],
    "front_right_leg": ["RightFrontShoulder", "RightFrontUpperArm", "RightFrontLowerArm", "RightFrontPaw", "RightFrontToes"],
    "back_left_leg": ["LeftBackHip", "LeftBackUpperLeg", "LeftBackLowerLeg", "LeftBackPaw", "LeftBackToes"],
    "back_right_leg": ["RightBackHip", "RightBackUpperLeg", "RightBackLowerLeg", "RightBackPaw", "RightBackToes"],
}

# Key bones for fitting skeleton to mesh
QUADRUPED_LANDMARK_BONES = {
    "root": "Hips",
    "head": "Head",
    "tail_tip": "Tail4",
    "front_left_paw": "LeftFrontPaw",
    "front_right_paw": "RightFrontPaw",
    "back_left_paw": "LeftBackPaw",
    "back_right_paw": "RightBackPaw",
}
