"""
Rigging service - business logic for rigging operations.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional, Callable

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .config import rigging_settings
from .schemas import (
    CharacterType,
    RiggingProcessor,
    RiggingResult,
    SkeletonData,
    CharacterAnalysis,
    SkeletonTemplateInfo,
)
from .processors import UniRigProcessor, BlenderProcessor
from .skeleton import (
    HUMANOID_TEMPLATE,
    QUADRUPED_TEMPLATE,
)

logger = logging.getLogger(__name__)


class RiggingService:
    """
    Service for rigging operations.

    Handles processor selection, character detection, and rigging workflow.
    """

    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db
        self._unirig = UniRigProcessor()
        self._blender = BlenderProcessor()
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize processors."""
        if self._initialized:
            return

        # Initialize processors (they handle their own errors)
        try:
            if rigging_settings.UNIRIG_ENABLED:
                await self._unirig.initialize()
        except Exception as e:
            logger.warning(f"UniRig initialization failed: {e}")

        try:
            if rigging_settings.BLENDER_ENABLED:
                await self._blender.initialize()
        except Exception as e:
            logger.warning(f"Blender initialization failed: {e}")

        self._initialized = True

    async def auto_rig(
        self,
        asset_id: str,
        mesh_path: Path,
        output_dir: Path,
        character_type: CharacterType = CharacterType.AUTO,
        processor: RiggingProcessor = RiggingProcessor.AUTO,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> RiggingResult:
        """
        Auto-rig an asset.

        Args:
            asset_id: Asset ID being rigged
            mesh_path: Path to mesh file
            output_dir: Output directory for rigged files
            character_type: Character type (or AUTO to detect)
            processor: Processor to use (or AUTO to select)
            progress_callback: Progress callback

        Returns:
            RiggingResult with skeleton and output path
        """
        await self.initialize()

        logger.info(f"Starting auto-rig for asset {asset_id}")
        logger.info(f"Mesh: {mesh_path}, Type: {character_type}, Processor: {processor}")

        # Detect character type if auto
        if character_type == CharacterType.AUTO:
            detected_type, confidence = await self.detect_character_type(mesh_path)
            character_type = detected_type
            logger.info(f"Detected character type: {character_type} (confidence: {confidence:.2f})")

        # Select processor
        selected_processor = await self._select_processor(character_type, processor)
        logger.info(f"Selected processor: {selected_processor.name}")

        # Run rigging
        result = await selected_processor.process(
            mesh_path=mesh_path,
            character_type=character_type,
            output_dir=output_dir,
            progress_callback=progress_callback,
        )

        return result

    async def detect_character_type(
        self,
        mesh_path: Path,
    ) -> tuple[CharacterType, float]:
        """
        Detect character type from mesh.

        Args:
            mesh_path: Path to mesh file

        Returns:
            Tuple of (detected_type, confidence)
        """
        await self.initialize()

        # Use UniRig for detection (it has the analysis logic)
        try:
            return await self._unirig.detect_character_type(mesh_path)
        except Exception as e:
            logger.warning(f"Character detection failed: {e}")
            return CharacterType.HUMANOID, 0.5

    async def _select_processor(
        self,
        character_type: CharacterType,
        requested: RiggingProcessor,
    ) -> "BaseRiggingProcessor":
        """
        Select appropriate processor.

        Args:
            character_type: Character type being rigged
            requested: Requested processor

        Returns:
            Selected processor instance
        """
        if requested == RiggingProcessor.UNIRIG:
            return self._unirig
        elif requested == RiggingProcessor.BLENDER:
            return self._blender
        else:
            # Auto-select based on character type and availability
            if character_type == CharacterType.QUADRUPED:
                # Blender is better for quadrupeds
                if rigging_settings.BLENDER_ENABLED:
                    return self._blender
                return self._unirig
            else:
                # UniRig is faster for humanoids
                if rigging_settings.UNIRIG_ENABLED:
                    return self._unirig
                return self._blender

    async def get_skeleton(self, asset_id: str) -> Optional[SkeletonData]:
        """
        Get skeleton data for a rigged asset.

        Args:
            asset_id: Asset ID

        Returns:
            SkeletonData if asset is rigged, None otherwise
        """
        if self.db is None:
            return None

        from ..generation.models import Asset

        result = await self.db.execute(
            select(Asset).where(Asset.id == asset_id)
        )
        asset = result.scalar_one_or_none()

        if asset is None or not asset.is_rigged:
            return None

        if asset.rigging_data:
            return SkeletonData(**asset.rigging_data)

        return None

    def get_templates(self) -> list[SkeletonTemplateInfo]:
        """Get list of available skeleton templates."""
        return [
            SkeletonTemplateInfo(
                name=HUMANOID_TEMPLATE["name"],
                character_type=CharacterType.HUMANOID,
                bone_count=HUMANOID_TEMPLATE["bone_count"],
                description=HUMANOID_TEMPLATE["description"],
            ),
            SkeletonTemplateInfo(
                name=QUADRUPED_TEMPLATE["name"],
                character_type=CharacterType.QUADRUPED,
                bone_count=QUADRUPED_TEMPLATE["bone_count"],
                description=QUADRUPED_TEMPLATE["description"],
            ),
        ]

    async def export_fbx(
        self,
        asset_id: str,
        input_path: Path,
        output_path: Path,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> Path:
        """
        Export rigged asset to FBX format.

        Args:
            asset_id: Asset ID
            input_path: Path to rigged GLB
            output_path: Output FBX path
            progress_callback: Progress callback

        Returns:
            Path to exported FBX file
        """
        await self.initialize()

        if not rigging_settings.BLENDER_ENABLED:
            raise RuntimeError("FBX export requires Blender")

        return await self._blender.export_fbx(
            input_path=input_path,
            output_path=output_path,
            progress_callback=progress_callback,
        )


# Global service instance
_rigging_service: Optional[RiggingService] = None


def get_rigging_service(db: Optional[AsyncSession] = None) -> RiggingService:
    """Get or create rigging service instance."""
    global _rigging_service
    if _rigging_service is None:
        _rigging_service = RiggingService(db)
    elif db is not None:
        _rigging_service.db = db
    return _rigging_service
