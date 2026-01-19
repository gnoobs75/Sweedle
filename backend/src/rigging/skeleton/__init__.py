"""
Skeleton data structures and templates.
"""

from .types import (
    Bone,
    Skeleton,
    create_bone,
    create_skeleton_from_template,
)
from .humanoid import HUMANOID_TEMPLATE, create_humanoid_skeleton
from .quadruped import QUADRUPED_TEMPLATE, create_quadruped_skeleton
from .landmarks import (
    get_default_landmarks,
    get_landmark_info,
    generate_skeleton_from_landmarks,
    fit_landmarks_to_mesh,
)

__all__ = [
    "Bone",
    "Skeleton",
    "create_bone",
    "create_skeleton_from_template",
    "HUMANOID_TEMPLATE",
    "create_humanoid_skeleton",
    "QUADRUPED_TEMPLATE",
    "create_quadruped_skeleton",
    # Landmark-based generation
    "get_default_landmarks",
    "get_landmark_info",
    "generate_skeleton_from_landmarks",
    "fit_landmarks_to_mesh",
]
