"""
Procedural animation generators.
"""

from .base import BaseAnimationGenerator

# Humanoid generators
from .idle import IdleGenerator
from .locomotion import WalkGenerator, RunGenerator
from .combat import AttackGenerator
from .humanoid import (
    DieGenerator,
    SitGenerator,
    CrouchGenerator,
    JumpGenerator,
    DodgeGenerator,
    WaveGenerator,
    CheerGenerator,
    PickupGenerator,
)

# Quadruped generators
from .quadruped import (
    QuadrupedIdleGenerator,
    TrotGenerator,
    TailWagGenerator,
    BiteGenerator,
    GallopGenerator,
    QuadrupedSitGenerator,
    QuadrupedLieDownGenerator,
    QuadrupedJumpGenerator,
    ShakeGenerator,
    PounceGenerator,
    HowlGenerator,
    RollOverGenerator,
    PlayDeadGenerator,
)

__all__ = [
    # Base
    "BaseAnimationGenerator",
    # Humanoid
    "IdleGenerator",
    "WalkGenerator",
    "RunGenerator",
    "AttackGenerator",
    "DieGenerator",
    "SitGenerator",
    "CrouchGenerator",
    "JumpGenerator",
    "DodgeGenerator",
    "WaveGenerator",
    "CheerGenerator",
    "PickupGenerator",
    # Quadruped
    "QuadrupedIdleGenerator",
    "TrotGenerator",
    "TailWagGenerator",
    "BiteGenerator",
    "GallopGenerator",
    "QuadrupedSitGenerator",
    "QuadrupedLieDownGenerator",
    "QuadrupedJumpGenerator",
    "ShakeGenerator",
    "PounceGenerator",
    "HowlGenerator",
    "RollOverGenerator",
    "PlayDeadGenerator",
]
