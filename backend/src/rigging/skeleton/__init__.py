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

__all__ = [
    "Bone",
    "Skeleton",
    "create_bone",
    "create_skeleton_from_template",
    "HUMANOID_TEMPLATE",
    "create_humanoid_skeleton",
    "QUADRUPED_TEMPLATE",
    "create_quadruped_skeleton",
]
