"""
Base class for rigging processors.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable, Optional

from ..schemas import (
    CharacterType,
    RiggingResult,
    SkeletonData,
    SkinningData,
)


class BaseRiggingProcessor(ABC):
    """Abstract base class for rigging processors."""

    name: str = "base"
    supported_types: list[CharacterType] = []

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the processor (load models, etc.)."""
        pass

    @abstractmethod
    async def process(
        self,
        mesh_path: Path,
        character_type: CharacterType,
        output_dir: Path,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> RiggingResult:
        """
        Process a mesh and generate rigging.

        Args:
            mesh_path: Path to input mesh file (GLB/OBJ)
            character_type: Type of character to rig
            output_dir: Directory for output files
            progress_callback: Optional callback for progress updates (progress, stage)

        Returns:
            RiggingResult with skeleton, weights, and output path
        """
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up resources."""
        pass

    def supports_type(self, character_type: CharacterType) -> bool:
        """Check if processor supports the given character type."""
        return character_type in self.supported_types

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
        # Default implementation - subclasses can override
        return CharacterType.HUMANOID, 0.5

    def _report_progress(
        self,
        callback: Optional[Callable[[float, str], None]],
        progress: float,
        stage: str,
    ) -> None:
        """Helper to safely call progress callback."""
        if callback:
            try:
                callback(progress, stage)
            except Exception:
                pass  # Don't let callback errors break processing
