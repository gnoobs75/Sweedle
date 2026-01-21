"""
Animation service for generating and managing animation clips.
"""

import logging
from typing import Optional
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .schemas import (
    AnimationType,
    AnimationParameters,
    AnimationData,
    AnimationPreset,
    CreateAnimationRequest,
    LoopMode,
)
from .generators import (
    # Humanoid generators
    IdleGenerator,
    WalkGenerator,
    RunGenerator,
    AttackGenerator,
    DieGenerator,
    SitGenerator,
    CrouchGenerator,
    JumpGenerator,
    DodgeGenerator,
    WaveGenerator,
    CheerGenerator,
    PickupGenerator,
    # Quadruped generators
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
from .bone_validator import validate_skeleton_for_animation, ValidationResult
from ..generation.models import Asset, AnimationClip
from ..rigging.schemas import SkeletonData

logger = logging.getLogger(__name__)


# Pre-defined animation presets
ANIMATION_PRESETS: dict[str, AnimationPreset] = {
    # ==================== HUMANOID PRESETS ====================
    "humanoid_idle": AnimationPreset(
        id="humanoid_idle",
        name="Idle (Breathing)",
        description="Subtle breathing and weight shift animation",
        animation_type=AnimationType.IDLE,
        character_type="humanoid",
        default_parameters=AnimationParameters(speed=1.0, intensity=1.0),
        duration=4.0,
        tags=["idle", "subtle", "loop"],
    ),
    "humanoid_walk": AnimationPreset(
        id="humanoid_walk",
        name="Walk Cycle",
        description="Standard walking animation with arm swing",
        animation_type=AnimationType.WALK,
        character_type="humanoid",
        default_parameters=AnimationParameters(speed=1.0, intensity=1.0),
        duration=1.0,
        tags=["locomotion", "loop"],
    ),
    "humanoid_run": AnimationPreset(
        id="humanoid_run",
        name="Run Cycle",
        description="Running animation with forward lean",
        animation_type=AnimationType.RUN,
        character_type="humanoid",
        default_parameters=AnimationParameters(speed=1.0, intensity=1.0),
        duration=0.6,
        tags=["locomotion", "loop"],
    ),
    "humanoid_jump": AnimationPreset(
        id="humanoid_jump",
        name="Jump",
        description="Jump with crouch, leap, and land phases",
        animation_type=AnimationType.JUMP,
        character_type="humanoid",
        default_parameters=AnimationParameters(speed=1.0, intensity=1.0),
        duration=0.8,
        tags=["movement", "once"],
    ),
    "humanoid_attack": AnimationPreset(
        id="humanoid_attack",
        name="Attack (Slash)",
        description="Overhead slash attack animation",
        animation_type=AnimationType.ATTACK,
        character_type="humanoid",
        default_parameters=AnimationParameters(speed=1.0, intensity=1.0),
        duration=0.8,
        tags=["combat", "once"],
    ),
    "humanoid_die": AnimationPreset(
        id="humanoid_die",
        name="Die",
        description="Death collapse animation",
        animation_type=AnimationType.DIE,
        character_type="humanoid",
        default_parameters=AnimationParameters(speed=1.0, intensity=1.0),
        duration=1.5,
        tags=["combat", "once"],
    ),
    "humanoid_sit": AnimationPreset(
        id="humanoid_sit",
        name="Sit Down",
        description="Transition to sitting position",
        animation_type=AnimationType.SIT,
        character_type="humanoid",
        default_parameters=AnimationParameters(speed=1.0, intensity=1.0),
        duration=1.2,
        tags=["idle", "once"],
    ),
    "humanoid_crouch": AnimationPreset(
        id="humanoid_crouch",
        name="Crouch",
        description="Crouching/sneaking stance",
        animation_type=AnimationType.CROUCH,
        character_type="humanoid",
        default_parameters=AnimationParameters(speed=1.0, intensity=1.0),
        duration=0.6,
        tags=["movement", "once"],
    ),
    "humanoid_dodge": AnimationPreset(
        id="humanoid_dodge",
        name="Dodge Roll",
        description="Side dodge roll animation",
        animation_type=AnimationType.DODGE,
        character_type="humanoid",
        default_parameters=AnimationParameters(speed=1.0, intensity=1.0),
        duration=0.8,
        tags=["combat", "once"],
    ),
    "humanoid_wave": AnimationPreset(
        id="humanoid_wave",
        name="Wave",
        description="Friendly waving gesture",
        animation_type=AnimationType.WAVE,
        character_type="humanoid",
        default_parameters=AnimationParameters(speed=1.0, intensity=1.0),
        duration=2.0,
        tags=["social", "once"],
    ),
    "humanoid_cheer": AnimationPreset(
        id="humanoid_cheer",
        name="Cheer",
        description="Celebration with arms raised",
        animation_type=AnimationType.CHEER,
        character_type="humanoid",
        default_parameters=AnimationParameters(speed=1.0, intensity=1.0),
        duration=2.0,
        tags=["social", "once"],
    ),
    "humanoid_pickup": AnimationPreset(
        id="humanoid_pickup",
        name="Pick Up",
        description="Bend down to pick something up",
        animation_type=AnimationType.PICKUP,
        character_type="humanoid",
        default_parameters=AnimationParameters(speed=1.0, intensity=1.0),
        duration=1.5,
        tags=["interaction", "once"],
    ),

    # ==================== QUADRUPED PRESETS ====================
    "quadruped_idle": AnimationPreset(
        id="quadruped_idle",
        name="Idle (Breathing)",
        description="Breathing with subtle tail and ear movement",
        animation_type=AnimationType.IDLE,
        character_type="quadruped",
        default_parameters=AnimationParameters(speed=1.0, intensity=1.0),
        duration=4.0,
        tags=["idle", "subtle", "loop"],
    ),
    "quadruped_trot": AnimationPreset(
        id="quadruped_trot",
        name="Trot",
        description="Diagonal gait trotting animation",
        animation_type=AnimationType.TROT,
        character_type="quadruped",
        default_parameters=AnimationParameters(speed=1.0, intensity=1.0),
        duration=0.8,
        tags=["locomotion", "loop"],
    ),
    "quadruped_gallop": AnimationPreset(
        id="quadruped_gallop",
        name="Gallop (Run)",
        description="Fast galloping run animation",
        animation_type=AnimationType.GALLOP,
        character_type="quadruped",
        default_parameters=AnimationParameters(speed=1.0, intensity=1.0),
        duration=0.5,
        tags=["locomotion", "loop"],
    ),
    "quadruped_jump": AnimationPreset(
        id="quadruped_jump",
        name="Jump",
        description="Leap with crouch and land phases",
        animation_type=AnimationType.JUMP,
        character_type="quadruped",
        default_parameters=AnimationParameters(speed=1.0, intensity=1.0),
        duration=0.8,
        tags=["movement", "once"],
    ),
    "quadruped_sit": AnimationPreset(
        id="quadruped_sit",
        name="Sit",
        description="Transition to sitting position",
        animation_type=AnimationType.SIT,
        character_type="quadruped",
        default_parameters=AnimationParameters(speed=1.0, intensity=1.0),
        duration=1.0,
        tags=["idle", "once"],
    ),
    "quadruped_lie_down": AnimationPreset(
        id="quadruped_lie_down",
        name="Lie Down",
        description="Transition to lying down position",
        animation_type=AnimationType.LIE_DOWN,
        character_type="quadruped",
        default_parameters=AnimationParameters(speed=1.0, intensity=1.0),
        duration=1.5,
        tags=["idle", "once"],
    ),
    "quadruped_tail_wag": AnimationPreset(
        id="quadruped_tail_wag",
        name="Tail Wag",
        description="Happy tail wagging animation",
        animation_type=AnimationType.TAIL_WAG,
        character_type="quadruped",
        default_parameters=AnimationParameters(speed=1.0, intensity=1.0),
        duration=1.0,
        tags=["behavior", "loop"],
    ),
    "quadruped_shake": AnimationPreset(
        id="quadruped_shake",
        name="Shake",
        description="Full body shake (shaking off water)",
        animation_type=AnimationType.SHAKE,
        character_type="quadruped",
        default_parameters=AnimationParameters(speed=1.0, intensity=1.0),
        duration=1.2,
        tags=["behavior", "once"],
    ),
    "quadruped_howl": AnimationPreset(
        id="quadruped_howl",
        name="Howl / Bark",
        description="Head up howling or barking animation",
        animation_type=AnimationType.HOWL,
        character_type="quadruped",
        default_parameters=AnimationParameters(speed=1.0, intensity=1.0),
        duration=2.0,
        tags=["behavior", "once"],
    ),
    "quadruped_bite": AnimationPreset(
        id="quadruped_bite",
        name="Attack (Bite)",
        description="Lunge forward with bite attack",
        animation_type=AnimationType.BITE,
        character_type="quadruped",
        default_parameters=AnimationParameters(speed=1.0, intensity=1.0),
        duration=0.6,
        tags=["combat", "once"],
    ),
    "quadruped_pounce": AnimationPreset(
        id="quadruped_pounce",
        name="Pounce",
        description="Crouch and spring forward attack",
        animation_type=AnimationType.POUNCE,
        character_type="quadruped",
        default_parameters=AnimationParameters(speed=1.0, intensity=1.0),
        duration=0.7,
        tags=["combat", "once"],
    ),
    "quadruped_roll_over": AnimationPreset(
        id="quadruped_roll_over",
        name="Roll Over",
        description="Roll onto back with paws in air",
        animation_type=AnimationType.ROLL_OVER,
        character_type="quadruped",
        default_parameters=AnimationParameters(speed=1.0, intensity=1.0),
        duration=2.0,
        tags=["behavior", "once"],
    ),
    "quadruped_play_dead": AnimationPreset(
        id="quadruped_play_dead",
        name="Play Dead / Die",
        description="Collapse and lie still animation",
        animation_type=AnimationType.PLAY_DEAD,
        character_type="quadruped",
        default_parameters=AnimationParameters(speed=1.0, intensity=1.0),
        duration=1.5,
        tags=["combat", "once"],
    ),
}


# Generator mapping
GENERATORS = {
    # ==================== HUMANOID ====================
    ("humanoid", AnimationType.IDLE): IdleGenerator,
    ("humanoid", AnimationType.WALK): WalkGenerator,
    ("humanoid", AnimationType.RUN): RunGenerator,
    ("humanoid", AnimationType.JUMP): JumpGenerator,
    ("humanoid", AnimationType.ATTACK): AttackGenerator,
    ("humanoid", AnimationType.DIE): DieGenerator,
    ("humanoid", AnimationType.SIT): SitGenerator,
    ("humanoid", AnimationType.CROUCH): CrouchGenerator,
    ("humanoid", AnimationType.DODGE): DodgeGenerator,
    ("humanoid", AnimationType.WAVE): WaveGenerator,
    ("humanoid", AnimationType.CHEER): CheerGenerator,
    ("humanoid", AnimationType.PICKUP): PickupGenerator,

    # ==================== QUADRUPED ====================
    ("quadruped", AnimationType.IDLE): QuadrupedIdleGenerator,
    ("quadruped", AnimationType.TROT): TrotGenerator,
    ("quadruped", AnimationType.GALLOP): GallopGenerator,
    ("quadruped", AnimationType.JUMP): QuadrupedJumpGenerator,
    ("quadruped", AnimationType.SIT): QuadrupedSitGenerator,
    ("quadruped", AnimationType.LIE_DOWN): QuadrupedLieDownGenerator,
    ("quadruped", AnimationType.TAIL_WAG): TailWagGenerator,
    ("quadruped", AnimationType.SHAKE): ShakeGenerator,
    ("quadruped", AnimationType.HOWL): HowlGenerator,
    ("quadruped", AnimationType.BITE): BiteGenerator,
    ("quadruped", AnimationType.POUNCE): PounceGenerator,
    ("quadruped", AnimationType.ROLL_OVER): RollOverGenerator,
    ("quadruped", AnimationType.PLAY_DEAD): PlayDeadGenerator,
}


class AnimationService:
    """Service for animation generation and management."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def get_presets(self, character_type: Optional[str] = None) -> list[AnimationPreset]:
        """
        Get available animation presets.

        Args:
            character_type: Filter by character type (humanoid/quadruped)

        Returns:
            List of animation presets
        """
        presets = list(ANIMATION_PRESETS.values())
        if character_type:
            presets = [p for p in presets if p.character_type == character_type]
        return presets

    def get_preset(self, preset_id: str) -> Optional[AnimationPreset]:
        """Get a specific preset by ID."""
        return ANIMATION_PRESETS.get(preset_id)

    async def validate_animation(
        self,
        asset_id: str,
        preset_id: str,
    ) -> ValidationResult:
        """
        Validate that a skeleton can support an animation preset.

        Args:
            asset_id: Asset to validate
            preset_id: Animation preset to check against

        Returns:
            ValidationResult with warnings about missing bones
        """
        # Get asset
        result = await self.db.execute(
            select(Asset).where(Asset.id == asset_id)
        )
        asset = result.scalar_one_or_none()

        if not asset:
            raise ValueError(f"Asset not found: {asset_id}")
        if not asset.is_rigged or not asset.rigging_data:
            raise ValueError("Asset must be rigged before validating animations")

        # Get preset
        preset = ANIMATION_PRESETS.get(preset_id)
        if not preset:
            raise ValueError(f"Unknown preset: {preset_id}")

        # Parse skeleton and validate
        skeleton = SkeletonData(**asset.rigging_data)
        return validate_skeleton_for_animation(
            skeleton,
            preset.animation_type,
            preset.character_type,
        )

    async def create_animation(
        self,
        request: CreateAnimationRequest,
    ) -> AnimationClip:
        """
        Create an animation clip from a preset.

        Args:
            request: Animation creation request

        Returns:
            Created AnimationClip database record

        Raises:
            ValueError: If asset not found, not rigged, or preset incompatible
        """
        # Get asset and verify it's rigged
        result = await self.db.execute(
            select(Asset).where(Asset.id == request.asset_id)
        )
        asset = result.scalar_one_or_none()

        if not asset:
            raise ValueError(f"Asset not found: {request.asset_id}")
        if not asset.is_rigged or not asset.rigging_data:
            raise ValueError("Asset must be rigged before adding animations")

        # Get preset
        preset = ANIMATION_PRESETS.get(request.preset_id)
        if not preset:
            raise ValueError(f"Unknown preset: {request.preset_id}")

        # Verify character type matches
        if asset.character_type != preset.character_type:
            raise ValueError(
                f"Preset '{preset.id}' is for {preset.character_type}, "
                f"but asset is {asset.character_type}"
            )

        # Parse skeleton data
        skeleton = SkeletonData(**asset.rigging_data)

        # Validate bones before generation
        validation = validate_skeleton_for_animation(
            skeleton,
            preset.animation_type,
            preset.character_type,
        )

        if not validation.is_valid:
            raise ValueError(
                f"Cannot create animation: missing required bones: {validation.missing_required}. "
                f"Warnings: {'; '.join(validation.warnings[:3])}"
            )

        if validation.warnings:
            logger.warning(
                f"Creating animation with warnings for asset {asset.id}: "
                f"{'; '.join(validation.warnings)}"
            )

        # Get generator
        generator_key = (preset.character_type, preset.animation_type)
        generator_class = GENERATORS.get(generator_key)
        if not generator_class:
            raise ValueError(f"No generator for {preset.character_type}/{preset.animation_type}")

        # Generate animation data
        generator = generator_class(skeleton)
        params = request.parameters or preset.default_parameters
        animation_data = generator.generate(preset.duration, params)

        # Create clip record
        clip = AnimationClip(
            id=str(uuid4()),
            asset_id=request.asset_id,
            name=request.name or preset.name,
            description=preset.description,
            animation_type=preset.animation_type.value,
            character_type=preset.character_type,
            parameters=params.model_dump(),
            duration_seconds=animation_data.duration,
            frame_rate=animation_data.frame_rate,
            loop_mode=request.loop_mode.value,
            keyframe_data={"tracks": [t.model_dump() for t in animation_data.tracks]},
        )

        self.db.add(clip)

        # Update asset flags
        asset.has_animations = True

        await self.db.commit()
        await self.db.refresh(clip)

        logger.info(
            f"Created animation clip '{clip.name}' ({clip.id}) for asset {request.asset_id}"
        )

        return clip

    async def _get_asset(self, asset_id: str) -> Optional[Asset]:
        """Get an asset by ID."""
        result = await self.db.execute(
            select(Asset).where(Asset.id == asset_id)
        )
        return result.scalar_one_or_none()

    async def get_asset_animations(self, asset_id: str) -> list[AnimationClip]:
        """Get all animation clips for an asset."""
        result = await self.db.execute(
            select(AnimationClip).where(AnimationClip.asset_id == asset_id)
        )
        return list(result.scalars().all())

    async def get_animation(self, clip_id: str) -> Optional[AnimationClip]:
        """Get a specific animation clip."""
        result = await self.db.execute(
            select(AnimationClip).where(AnimationClip.id == clip_id)
        )
        return result.scalar_one_or_none()

    async def delete_animation(self, clip_id: str) -> bool:
        """
        Delete an animation clip.

        Returns:
            True if deleted, False if not found
        """
        result = await self.db.execute(
            select(AnimationClip).where(AnimationClip.id == clip_id)
        )
        clip = result.scalar_one_or_none()

        if not clip:
            return False

        asset_id = clip.asset_id
        await self.db.delete(clip)

        # Check if asset still has animations
        remaining = await self.db.execute(
            select(AnimationClip).where(AnimationClip.asset_id == asset_id)
        )
        if not remaining.scalars().first():
            # No more animations, update asset flag
            asset_result = await self.db.execute(
                select(Asset).where(Asset.id == asset_id)
            )
            asset = asset_result.scalar_one_or_none()
            if asset:
                asset.has_animations = False

        await self.db.commit()

        logger.info(f"Deleted animation clip {clip_id}")
        return True

    async def get_animation_data(self, clip_id: str) -> Optional[AnimationData]:
        """
        Get the animation keyframe data for playback.

        Args:
            clip_id: Animation clip ID

        Returns:
            AnimationData for playback, or None if not found
        """
        clip = await self.get_animation(clip_id)
        if not clip or not clip.keyframe_data:
            return None

        from .schemas import KeyframeTrack

        tracks = [
            KeyframeTrack(**t)
            for t in clip.keyframe_data.get("tracks", [])
        ]

        return AnimationData(
            name=clip.name,
            duration=clip.duration_seconds,
            frame_rate=clip.frame_rate,
            tracks=tracks,
        )

    async def regenerate_animation(
        self,
        clip_id: str,
        parameters: AnimationParameters,
    ) -> Optional[AnimationClip]:
        """
        Regenerate an animation with new parameters.

        Args:
            clip_id: Existing clip ID
            parameters: New animation parameters

        Returns:
            Updated AnimationClip, or None if not found
        """
        clip = await self.get_animation(clip_id)
        if not clip:
            return None

        # Get asset and skeleton
        result = await self.db.execute(
            select(Asset).where(Asset.id == clip.asset_id)
        )
        asset = result.scalar_one_or_none()
        if not asset or not asset.rigging_data:
            return None

        skeleton = SkeletonData(**asset.rigging_data)

        # Get generator
        anim_type = AnimationType(clip.animation_type)
        generator_key = (clip.character_type, anim_type)
        generator_class = GENERATORS.get(generator_key)
        if not generator_class:
            return None

        # Regenerate
        generator = generator_class(skeleton)
        preset = ANIMATION_PRESETS.get(f"{clip.character_type}_{clip.animation_type}")
        duration = preset.duration if preset else clip.duration_seconds

        animation_data = generator.generate(duration, parameters)

        # Update clip
        clip.parameters = parameters.model_dump()
        clip.duration_seconds = animation_data.duration
        clip.keyframe_data = {"tracks": [t.model_dump() for t in animation_data.tracks]}

        await self.db.commit()
        await self.db.refresh(clip)

        logger.info(f"Regenerated animation clip {clip_id} with new parameters")
        return clip
