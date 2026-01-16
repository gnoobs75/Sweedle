"""
Procedural animation generators.
"""

from .base import BaseAnimationGenerator
from .idle import IdleGenerator
from .locomotion import WalkGenerator, RunGenerator
from .combat import AttackGenerator
from .quadruped import QuadrupedIdleGenerator, TrotGenerator, TailWagGenerator, BiteGenerator

__all__ = [
    "BaseAnimationGenerator",
    "IdleGenerator",
    "WalkGenerator",
    "RunGenerator",
    "AttackGenerator",
    "QuadrupedIdleGenerator",
    "TrotGenerator",
    "TailWagGenerator",
    "BiteGenerator",
]
