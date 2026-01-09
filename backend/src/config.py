"""Application configuration using Pydantic settings."""

import logging
from pathlib import Path
from typing import Optional, Literal
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


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

    # === GPU Performance Settings (RTX 30/40 series optimizations) ===
    # These settings significantly improve performance on modern NVIDIA GPUs

    # Enable TF32 for matrix operations (8x faster on RTX 30/40 series)
    # TF32 uses 19 bits of precision (vs 32 for FP32) - negligible quality difference
    ENABLE_TF32: bool = True

    # Enable cuDNN autotuning (finds fastest algorithms for your specific GPU)
    ENABLE_CUDNN_BENCHMARK: bool = True

    # Use FP16/BF16 for inference (2x faster, 50% less VRAM)
    # Options: "fp32", "fp16", "bf16" (bf16 best for RTX 40 series)
    INFERENCE_DTYPE: Literal["fp32", "fp16", "bf16"] = "bf16"

    # Enable Flash Attention for transformer models (faster, less memory)
    ENABLE_FLASH_ATTENTION: bool = True

    # CUDA memory settings
    CUDA_MEMORY_FRACTION: float = 0.95  # Use up to 95% of VRAM (default: unlimited)
    ENABLE_MEMORY_EFFICIENT_ATTENTION: bool = True

    # Model loading settings
    ENABLE_TEXTURE_PIPELINE: bool = True  # Load texture generation (18GB extra VRAM)
    LAZY_MODEL_LOADING: bool = False  # If True, load models on first job instead of startup

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


def apply_gpu_optimizations() -> dict:
    """Apply PyTorch GPU optimizations based on settings.

    Should be called once at application startup, before loading models.
    Returns a dict with the applied optimizations for logging.

    These optimizations can provide 2-8x speedup on modern NVIDIA GPUs.
    """
    applied = {}

    try:
        import torch

        if not torch.cuda.is_available():
            logger.info("CUDA not available, skipping GPU optimizations")
            return {"cuda_available": False}

        # Get GPU info
        gpu_name = torch.cuda.get_device_name(0)
        compute_cap = torch.cuda.get_device_capability(0)
        applied["gpu"] = gpu_name
        applied["compute_capability"] = f"{compute_cap[0]}.{compute_cap[1]}"

        # Enable TF32 for Ampere+ GPUs (compute capability >= 8.0)
        if settings.ENABLE_TF32 and compute_cap[0] >= 8:
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True
            applied["tf32"] = True
            logger.info("Enabled TF32 tensor operations (8x faster matmul)")
        else:
            applied["tf32"] = False

        # Enable cuDNN benchmark (autotuning)
        if settings.ENABLE_CUDNN_BENCHMARK:
            torch.backends.cudnn.benchmark = True
            torch.backends.cudnn.enabled = True
            applied["cudnn_benchmark"] = True
            logger.info("Enabled cuDNN benchmark (autotuning)")

        # Set deterministic mode off for performance
        torch.backends.cudnn.deterministic = False
        applied["deterministic"] = False

        # Set default dtype for inference
        dtype_map = {
            "fp32": torch.float32,
            "fp16": torch.float16,
            "bf16": torch.bfloat16,
        }
        inference_dtype = dtype_map.get(settings.INFERENCE_DTYPE, torch.float32)

        # Check BF16 support (Ampere+ GPUs)
        if settings.INFERENCE_DTYPE == "bf16":
            if torch.cuda.is_bf16_supported():
                applied["dtype"] = "bf16"
                logger.info("Using BFloat16 for inference (optimal for RTX 40 series)")
            else:
                inference_dtype = torch.float16
                applied["dtype"] = "fp16 (bf16 not supported)"
                logger.warning("BF16 not supported, falling back to FP16")
        else:
            applied["dtype"] = settings.INFERENCE_DTYPE

        # Store dtype for pipeline use
        applied["torch_dtype"] = inference_dtype

        # Set memory fraction if specified
        if settings.CUDA_MEMORY_FRACTION < 1.0:
            torch.cuda.set_per_process_memory_fraction(
                settings.CUDA_MEMORY_FRACTION, device=0
            )
            applied["memory_fraction"] = settings.CUDA_MEMORY_FRACTION
            logger.info(f"Set CUDA memory fraction to {settings.CUDA_MEMORY_FRACTION:.0%}")

        # Enable memory-efficient attention if available
        if settings.ENABLE_MEMORY_EFFICIENT_ATTENTION:
            try:
                # This is handled by diffusers/transformers when loading models
                applied["memory_efficient_attention"] = True
            except Exception:
                applied["memory_efficient_attention"] = False

        # Log VRAM info
        props = torch.cuda.get_device_properties(0)
        vram_gb = props.total_memory / (1024**3)
        applied["vram_gb"] = round(vram_gb, 1)
        logger.info(f"GPU: {gpu_name} with {vram_gb:.1f}GB VRAM")

        return applied

    except ImportError:
        logger.warning("PyTorch not installed, GPU optimizations skipped")
        return {"error": "PyTorch not installed"}
    except Exception as e:
        logger.error(f"Failed to apply GPU optimizations: {e}")
        return {"error": str(e)}


def get_inference_dtype():
    """Get the torch dtype for model inference based on settings."""
    try:
        import torch

        if settings.INFERENCE_DTYPE == "bf16" and torch.cuda.is_bf16_supported():
            return torch.bfloat16
        elif settings.INFERENCE_DTYPE == "fp16":
            return torch.float16
        else:
            return torch.float32
    except ImportError:
        return None


# Global settings instance
settings = Settings()
