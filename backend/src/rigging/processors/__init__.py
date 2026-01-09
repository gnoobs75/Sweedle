"""
Rigging processors for different backends.
"""

from .base import BaseRiggingProcessor
from .unirig import UniRigProcessor
from .blender import BlenderProcessor

__all__ = [
    "BaseRiggingProcessor",
    "UniRigProcessor",
    "BlenderProcessor",
]
