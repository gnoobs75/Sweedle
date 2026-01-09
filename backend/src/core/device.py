"""Device detection and management for cross-platform GPU support.

Provides unified interface for CUDA (NVIDIA), MPS (Apple Silicon), and CPU backends.
"""

import logging
import threading
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class DeviceType(str, Enum):
    """Supported compute device types."""
    CUDA = "cuda"
    MPS = "mps"
    CPU = "cpu"


# Thread lock for singleton initialization
_instance_lock = threading.Lock()


class DeviceManager:
    """Manages device detection and provides device-specific utilities.

    Supports:
    - NVIDIA CUDA (Windows/Linux)
    - Apple Silicon MPS (macOS)
    - CPU fallback (all platforms)
    """

    _instance: Optional["DeviceManager"] = None
    _detected_device: Optional[str] = None

    def __new__(cls):
        """Thread-safe singleton pattern for consistent device detection."""
        if cls._instance is None:
            with _instance_lock:
                # Double-check locking for thread safety
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._detected_device = cls._detect_device()
        return cls._instance

    @staticmethod
    def _detect_device() -> str:
        """Auto-detect the best available compute device.

        Priority: CUDA (NVIDIA) → MPS (Apple Silicon) → CPU

        Returns:
            Device string: "cuda", "mps", or "cpu"
        """
        try:
            import torch

            # Check for NVIDIA CUDA first (most common for ML workloads)
            if torch.cuda.is_available():
                device_name = torch.cuda.get_device_name(0)
                logger.info(f"CUDA device detected: {device_name}")
                return DeviceType.CUDA.value

            # Check for Apple Silicon MPS
            if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                logger.info("Apple Silicon MPS device detected")
                return DeviceType.MPS.value

            # Fallback to CPU
            logger.info("No GPU detected, using CPU")
            return DeviceType.CPU.value

        except ImportError:
            logger.warning("PyTorch not installed, defaulting to CPU")
            return DeviceType.CPU.value
        except Exception as e:
            logger.warning(f"Device detection failed: {e}, defaulting to CPU")
            return DeviceType.CPU.value

    @property
    def device(self) -> str:
        """Get the detected device."""
        return self._detected_device

    @property
    def is_gpu(self) -> bool:
        """Check if a GPU device is available."""
        return self._detected_device in (DeviceType.CUDA.value, DeviceType.MPS.value)

    @property
    def is_cuda(self) -> bool:
        """Check if CUDA is available."""
        return self._detected_device == DeviceType.CUDA.value

    @property
    def is_mps(self) -> bool:
        """Check if MPS is available."""
        return self._detected_device == DeviceType.MPS.value

    def get_torch_device(self):
        """Get torch.device object for the detected device.

        Returns:
            torch.device instance
        """
        import torch
        return torch.device(self._detected_device)

    def get_dtype(self, low_vram: bool = False):
        """Get recommended dtype for the device.

        Args:
            low_vram: Use float16 for memory efficiency

        Returns:
            torch.dtype
        """
        import torch

        if low_vram and self._detected_device == DeviceType.CUDA.value:
            return torch.float16
        elif self._detected_device == DeviceType.MPS.value:
            # MPS works better with float32 in PyTorch 2.x
            return torch.float32
        else:
            return torch.float32

    def empty_cache(self) -> None:
        """Clear GPU memory cache for the detected device."""
        try:
            import torch

            if self._detected_device == DeviceType.CUDA.value and torch.cuda.is_available():
                torch.cuda.empty_cache()
                logger.debug("CUDA cache cleared")
            elif self._detected_device == DeviceType.MPS.value:
                # Check both torch.mps existence and empty_cache availability
                if hasattr(torch, "mps") and hasattr(torch.mps, "empty_cache"):
                    torch.mps.empty_cache()
                    logger.debug("MPS cache cleared")
        except Exception as e:
            logger.debug(f"Cache clearing skipped: {e}")

    def get_memory_info(self) -> dict:
        """Get memory information for the detected device.

        Returns:
            Dictionary with memory statistics
        """
        try:
            import torch

            if self._detected_device == DeviceType.CUDA.value and torch.cuda.is_available():
                props = torch.cuda.get_device_properties(0)
                return {
                    "device_type": "cuda",
                    "device_name": props.name,
                    "total_memory_gb": round(props.total_memory / 1e9, 2),
                    "allocated_gb": round(torch.cuda.memory_allocated(0) / 1e9, 2),
                    "reserved_gb": round(torch.cuda.memory_reserved(0) / 1e9, 2),
                }
            elif self._detected_device == DeviceType.MPS.value:
                return {
                    "device_type": "mps",
                    "device_name": "Apple Silicon (Metal Performance Shaders)",
                    "note": "Detailed memory stats not available for MPS",
                }
            else:
                return {
                    "device_type": "cpu",
                    "device_name": "CPU",
                }
        except Exception as e:
            return {
                "device_type": self._detected_device,
                "error": str(e),
            }

    def get_generator_device(self) -> str:
        """Get device for torch.Generator.

        Note: MPS doesn't support Generator with device parameter,
        so we use CPU for seeded generation (still deterministic).

        Returns:
            Device string for Generator
        """
        if self._detected_device == DeviceType.MPS.value:
            return "cpu"  # MPS Generator workaround
        return self._detected_device


def get_default_device() -> str:
    """Get the default device for the system.

    This is a convenience function that returns the detected device
    without needing to instantiate DeviceManager.

    Returns:
        Device string: "cuda", "mps", or "cpu"
    """
    return DeviceManager().device


def get_device_info() -> dict:
    """Get detailed information about the detected device.

    Returns:
        Dictionary with device information
    """
    manager = DeviceManager()
    return {
        "device": manager.device,
        "is_gpu": manager.is_gpu,
        "is_cuda": manager.is_cuda,
        "is_mps": manager.is_mps,
        "memory": manager.get_memory_info(),
    }
