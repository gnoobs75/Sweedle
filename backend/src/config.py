"""Application configuration using Pydantic settings."""

from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


def _get_default_device() -> str:
    """Auto-detect the best available compute device.

    Priority: CUDA (NVIDIA) → MPS (Apple Silicon) → CPU

    Returns:
        Device string: "cuda", "mps", or "cpu"
    """
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
        else:
            return "cpu"
    except ImportError:
        return "cpu"
    except Exception:
        return "cpu"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    APP_NAME: str = "Sweedle"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/sweedle.db"

    # Storage paths (relative to backend directory)
    STORAGE_ROOT: Path = Path("./storage")
    UPLOAD_DIR: Path = Path("./storage/uploads")
    GENERATED_DIR: Path = Path("./storage/generated")
    EXPORT_DIR: Path = Path("./storage/exports")

    # Hunyuan3D settings
    HUNYUAN_MODEL_PATH: str = "tencent/Hunyuan3D-2.1"
    HUNYUAN_SUBFOLDER: str = "hunyuan3d-dit-v2-1"
    LOW_VRAM_MODE: bool = False
    DEVICE: str = "auto"  # "auto", "cuda", "mps", or "cpu"

    # Performance settings
    ENABLE_MODEL_WARMUP: bool = True  # Warmup model on startup to avoid cold start
    PREPROCESSING_WORKERS: int = 4  # Parallel preprocessing threads
    ENABLE_PREPROCESSING_OVERLAP: bool = True  # Preprocess next job during GPU work

    @property
    def compute_device(self) -> str:
        """Get the actual compute device to use.

        If DEVICE is "auto", auto-detect the best available device.
        Otherwise, use the specified device.
        """
        if self.DEVICE == "auto":
            return _get_default_device()
        return self.DEVICE

    # Default generation parameters
    DEFAULT_INFERENCE_STEPS: int = 30
    DEFAULT_GUIDANCE_SCALE: float = 5.5
    DEFAULT_OCTREE_RESOLUTION: int = 256

    # Queue settings
    MAX_QUEUE_SIZE: int = 100
    JOB_TIMEOUT_SECONDS: int = 600  # 10 minutes

    # LOD settings
    LOD_LEVELS: list[float] = [1.0, 0.5, 0.25, 0.1]

    # Engine export paths (user configurable)
    UNITY_PROJECT_PATH: Optional[Path] = None
    UNREAL_PROJECT_PATH: Optional[Path] = None
    GODOT_PROJECT_PATH: Optional[Path] = None

    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        self.STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self.GENERATED_DIR.mkdir(parents=True, exist_ok=True)
        self.EXPORT_DIR.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
