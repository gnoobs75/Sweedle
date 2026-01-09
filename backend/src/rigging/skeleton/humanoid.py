"""
Humanoid skeleton template.

Standard humanoid rig compatible with Mixamo, Unity Humanoid, and Unreal Mannequin.
Bone naming follows industry conventions for maximum compatibility.
"""

from ..schemas import CharacterType
from .types import Skeleton, create_skeleton_from_template

# Humanoid skeleton template with 65 bones
# Positions are normalized (0-2 units height, centered at origin)
HUMANOID_TEMPLATE = {
    "name": "Humanoid",
    "description": "Standard humanoid skeleton for bipedal characters",
    "bone_count": 65,
    "bones": [
        # Root/Hips
        {"name": "Hips", "parent": None, "head": (0, 1.0, 0), "tail": (0, 1.05, 0), "deform": True},

        # Spine chain
        {"name": "Spine", "parent": "Hips", "head": (0, 1.05, 0), "tail": (0, 1.2, 0), "connected": True},
        {"name": "Spine1", "parent": "Spine", "head": (0, 1.2, 0), "tail": (0, 1.35, 0), "connected": True},
        {"name": "Spine2", "parent": "Spine1", "head": (0, 1.35, 0), "tail": (0, 1.5, 0), "connected": True},

        # Neck and Head
        {"name": "Neck", "parent": "Spine2", "head": (0, 1.5, 0), "tail": (0, 1.6, 0), "connected": True},
        {"name": "Head", "parent": "Neck", "head": (0, 1.6, 0), "tail": (0, 1.8, 0), "connected": True},

        # Left Arm
        {"name": "LeftShoulder", "parent": "Spine2", "head": (0.05, 1.48, 0), "tail": (0.15, 1.48, 0)},
        {"name": "LeftArm", "parent": "LeftShoulder", "head": (0.15, 1.48, 0), "tail": (0.4, 1.48, 0), "connected": True},
        {"name": "LeftForeArm", "parent": "LeftArm", "head": (0.4, 1.48, 0), "tail": (0.65, 1.48, 0), "connected": True},
        {"name": "LeftHand", "parent": "LeftForeArm", "head": (0.65, 1.48, 0), "tail": (0.75, 1.48, 0), "connected": True},

        # Left Hand Fingers
        {"name": "LeftHandThumb1", "parent": "LeftHand", "head": (0.68, 1.48, 0.02), "tail": (0.71, 1.48, 0.04)},
        {"name": "LeftHandThumb2", "parent": "LeftHandThumb1", "head": (0.71, 1.48, 0.04), "tail": (0.74, 1.48, 0.05), "connected": True},
        {"name": "LeftHandThumb3", "parent": "LeftHandThumb2", "head": (0.74, 1.48, 0.05), "tail": (0.76, 1.48, 0.06), "connected": True},

        {"name": "LeftHandIndex1", "parent": "LeftHand", "head": (0.75, 1.48, 0.015), "tail": (0.80, 1.48, 0.015), "connected": True},
        {"name": "LeftHandIndex2", "parent": "LeftHandIndex1", "head": (0.80, 1.48, 0.015), "tail": (0.84, 1.48, 0.015), "connected": True},
        {"name": "LeftHandIndex3", "parent": "LeftHandIndex2", "head": (0.84, 1.48, 0.015), "tail": (0.87, 1.48, 0.015), "connected": True},

        {"name": "LeftHandMiddle1", "parent": "LeftHand", "head": (0.75, 1.48, 0), "tail": (0.81, 1.48, 0), "connected": True},
        {"name": "LeftHandMiddle2", "parent": "LeftHandMiddle1", "head": (0.81, 1.48, 0), "tail": (0.86, 1.48, 0), "connected": True},
        {"name": "LeftHandMiddle3", "parent": "LeftHandMiddle2", "head": (0.86, 1.48, 0), "tail": (0.89, 1.48, 0), "connected": True},

        {"name": "LeftHandRing1", "parent": "LeftHand", "head": (0.75, 1.48, -0.015), "tail": (0.80, 1.48, -0.015), "connected": True},
        {"name": "LeftHandRing2", "parent": "LeftHandRing1", "head": (0.80, 1.48, -0.015), "tail": (0.84, 1.48, -0.015), "connected": True},
        {"name": "LeftHandRing3", "parent": "LeftHandRing2", "head": (0.84, 1.48, -0.015), "tail": (0.87, 1.48, -0.015), "connected": True},

        {"name": "LeftHandPinky1", "parent": "LeftHand", "head": (0.75, 1.48, -0.03), "tail": (0.78, 1.48, -0.03), "connected": True},
        {"name": "LeftHandPinky2", "parent": "LeftHandPinky1", "head": (0.78, 1.48, -0.03), "tail": (0.81, 1.48, -0.03), "connected": True},
        {"name": "LeftHandPinky3", "parent": "LeftHandPinky2", "head": (0.81, 1.48, -0.03), "tail": (0.83, 1.48, -0.03), "connected": True},

        # Right Arm
        {"name": "RightShoulder", "parent": "Spine2", "head": (-0.05, 1.48, 0), "tail": (-0.15, 1.48, 0)},
        {"name": "RightArm", "parent": "RightShoulder", "head": (-0.15, 1.48, 0), "tail": (-0.4, 1.48, 0), "connected": True},
        {"name": "RightForeArm", "parent": "RightArm", "head": (-0.4, 1.48, 0), "tail": (-0.65, 1.48, 0), "connected": True},
        {"name": "RightHand", "parent": "RightForeArm", "head": (-0.65, 1.48, 0), "tail": (-0.75, 1.48, 0), "connected": True},

        # Right Hand Fingers
        {"name": "RightHandThumb1", "parent": "RightHand", "head": (-0.68, 1.48, 0.02), "tail": (-0.71, 1.48, 0.04)},
        {"name": "RightHandThumb2", "parent": "RightHandThumb1", "head": (-0.71, 1.48, 0.04), "tail": (-0.74, 1.48, 0.05), "connected": True},
        {"name": "RightHandThumb3", "parent": "RightHandThumb2", "head": (-0.74, 1.48, 0.05), "tail": (-0.76, 1.48, 0.06), "connected": True},

        {"name": "RightHandIndex1", "parent": "RightHand", "head": (-0.75, 1.48, 0.015), "tail": (-0.80, 1.48, 0.015), "connected": True},
        {"name": "RightHandIndex2", "parent": "RightHandIndex1", "head": (-0.80, 1.48, 0.015), "tail": (-0.84, 1.48, 0.015), "connected": True},
        {"name": "RightHandIndex3", "parent": "RightHandIndex2", "head": (-0.84, 1.48, 0.015), "tail": (-0.87, 1.48, 0.015), "connected": True},

        {"name": "RightHandMiddle1", "parent": "RightHand", "head": (-0.75, 1.48, 0), "tail": (-0.81, 1.48, 0), "connected": True},
        {"name": "RightHandMiddle2", "parent": "RightHandMiddle1", "head": (-0.81, 1.48, 0), "tail": (-0.86, 1.48, 0), "connected": True},
        {"name": "RightHandMiddle3", "parent": "RightHandMiddle2", "head": (-0.86, 1.48, 0), "tail": (-0.89, 1.48, 0), "connected": True},

        {"name": "RightHandRing1", "parent": "RightHand", "head": (-0.75, 1.48, -0.015), "tail": (-0.80, 1.48, -0.015), "connected": True},
        {"name": "RightHandRing2", "parent": "RightHandRing1", "head": (-0.80, 1.48, -0.015), "tail": (-0.84, 1.48, -0.015), "connected": True},
        {"name": "RightHandRing3", "parent": "RightHandRing2", "head": (-0.84, 1.48, -0.015), "tail": (-0.87, 1.48, -0.015), "connected": True},

        {"name": "RightHandPinky1", "parent": "RightHand", "head": (-0.75, 1.48, -0.03), "tail": (-0.78, 1.48, -0.03), "connected": True},
        {"name": "RightHandPinky2", "parent": "RightHandPinky1", "head": (-0.78, 1.48, -0.03), "tail": (-0.81, 1.48, -0.03), "connected": True},
        {"name": "RightHandPinky3", "parent": "RightHandPinky2", "head": (-0.81, 1.48, -0.03), "tail": (-0.83, 1.48, -0.03), "connected": True},

        # Left Leg
        {"name": "LeftUpLeg", "parent": "Hips", "head": (0.1, 1.0, 0), "tail": (0.1, 0.55, 0)},
        {"name": "LeftLeg", "parent": "LeftUpLeg", "head": (0.1, 0.55, 0), "tail": (0.1, 0.1, 0), "connected": True},
        {"name": "LeftFoot", "parent": "LeftLeg", "head": (0.1, 0.1, 0), "tail": (0.1, 0.05, 0.1), "connected": True},
        {"name": "LeftToeBase", "parent": "LeftFoot", "head": (0.1, 0.05, 0.1), "tail": (0.1, 0.02, 0.18), "connected": True},

        # Right Leg
        {"name": "RightUpLeg", "parent": "Hips", "head": (-0.1, 1.0, 0), "tail": (-0.1, 0.55, 0)},
        {"name": "RightLeg", "parent": "RightUpLeg", "head": (-0.1, 0.55, 0), "tail": (-0.1, 0.1, 0), "connected": True},
        {"name": "RightFoot", "parent": "RightLeg", "head": (-0.1, 0.1, 0), "tail": (-0.1, 0.05, 0.1), "connected": True},
        {"name": "RightToeBase", "parent": "RightFoot", "head": (-0.1, 0.05, 0.1), "tail": (-0.1, 0.02, 0.18), "connected": True},
    ],
}


def create_humanoid_skeleton() -> Skeleton:
    """
    Create a standard humanoid skeleton from template.

    Returns:
        Skeleton configured for humanoid characters
    """
    return create_skeleton_from_template(HUMANOID_TEMPLATE, CharacterType.HUMANOID)


# Bone groups for easier manipulation
HUMANOID_BONE_GROUPS = {
    "spine": ["Hips", "Spine", "Spine1", "Spine2", "Neck", "Head"],
    "left_arm": ["LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand"],
    "right_arm": ["RightShoulder", "RightArm", "RightForeArm", "RightHand"],
    "left_hand": [
        "LeftHandThumb1", "LeftHandThumb2", "LeftHandThumb3",
        "LeftHandIndex1", "LeftHandIndex2", "LeftHandIndex3",
        "LeftHandMiddle1", "LeftHandMiddle2", "LeftHandMiddle3",
        "LeftHandRing1", "LeftHandRing2", "LeftHandRing3",
        "LeftHandPinky1", "LeftHandPinky2", "LeftHandPinky3",
    ],
    "right_hand": [
        "RightHandThumb1", "RightHandThumb2", "RightHandThumb3",
        "RightHandIndex1", "RightHandIndex2", "RightHandIndex3",
        "RightHandMiddle1", "RightHandMiddle2", "RightHandMiddle3",
        "RightHandRing1", "RightHandRing2", "RightHandRing3",
        "RightHandPinky1", "RightHandPinky2", "RightHandPinky3",
    ],
    "left_leg": ["LeftUpLeg", "LeftLeg", "LeftFoot", "LeftToeBase"],
    "right_leg": ["RightUpLeg", "RightLeg", "RightFoot", "RightToeBase"],
}

# Key bones for fitting skeleton to mesh
HUMANOID_LANDMARK_BONES = {
    "root": "Hips",
    "head_top": "Head",
    "left_hand": "LeftHand",
    "right_hand": "RightHand",
    "left_foot": "LeftFoot",
    "right_foot": "RightFoot",
}
