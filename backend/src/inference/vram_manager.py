"""
VRAM Manager for Hunyuan3D Pipeline

Handles proper cleanup of GPU memory between shape and texture generation stages.
RTX 4090 (24GB) can't hold both models simultaneously, so we need careful management.
"""

import gc
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)


def get_vram_usage() -> float:
    """Get current VRAM usage in GB."""
    try:
        import torch
        if torch.cuda.is_available():
            return torch.cuda.memory_allocated(0) / 1e9
    except:
        pass
    return 0.0


def get_vram_info() -> dict:
    """Get detailed VRAM info."""
    try:
        import torch
        if torch.cuda.is_available():
            allocated = torch.cuda.memory_allocated(0)
            reserved = torch.cuda.memory_reserved(0)
            total = torch.cuda.get_device_properties(0).total_memory
            return {
                "allocated_gb": allocated / 1e9,
                "reserved_gb": reserved / 1e9,
                "total_gb": total / 1e9,
                "free_gb": (total - allocated) / 1e9,
            }
    except:
        pass
    return {"allocated_gb": 0, "reserved_gb": 0, "total_gb": 0, "free_gb": 0}


def move_module_to_cpu(module: Any, name: str = "module") -> bool:
    """
    Recursively move a PyTorch module and all its submodules to CPU.

    Returns True if successful.
    """
    try:
        import torch

        if module is None:
            return True

        if not hasattr(module, 'to'):
            return True

        # Try the standard .to() method first
        try:
            module.to('cpu')
        except Exception as e:
            logger.warning(f"Standard .to('cpu') failed for {name}: {e}")

        # For nn.Module, iterate through all submodules
        if isinstance(module, torch.nn.Module):
            for child_name, child in module.named_modules():
                try:
                    child.to('cpu')
                except:
                    pass

                # Move any tensor attributes
                for attr_name in dir(child):
                    if attr_name.startswith('_'):
                        continue
                    try:
                        attr = getattr(child, attr_name, None)
                        if isinstance(attr, torch.Tensor) and attr.is_cuda:
                            setattr(child, attr_name, attr.cpu())
                    except:
                        pass

        # Check for common pipeline attributes that might hold GPU tensors
        tensor_attrs = ['latents', 'noise', 'timesteps', 'encoder_hidden_states',
                       'image_embeds', 'pooled_output', 'grid_logits']
        for attr in tensor_attrs:
            if hasattr(module, attr):
                try:
                    val = getattr(module, attr)
                    if isinstance(val, torch.Tensor) and val.is_cuda:
                        setattr(module, attr, val.cpu())
                except:
                    pass

        return True

    except Exception as e:
        logger.warning(f"Failed to move {name} to CPU: {e}")
        return False


def clear_cuda_cache() -> float:
    """
    Aggressively clear CUDA cache and return amount freed (GB).
    """
    try:
        import torch

        if not torch.cuda.is_available():
            return 0.0

        before = torch.cuda.memory_allocated(0) / 1e9

        # Synchronize to ensure all operations complete
        torch.cuda.synchronize()

        # Python garbage collection (run multiple times for circular refs)
        gc.collect()
        gc.collect()
        gc.collect()

        # Clear PyTorch cache
        torch.cuda.empty_cache()

        # IPC collect if available (helps with multiprocess scenarios)
        if hasattr(torch.cuda, 'ipc_collect'):
            torch.cuda.ipc_collect()

        # Final sync
        torch.cuda.synchronize()

        after = torch.cuda.memory_allocated(0) / 1e9
        freed = before - after

        logger.info(f"CUDA cache cleared: {before:.2f}GB -> {after:.2f}GB (freed {freed:.2f}GB)")

        return freed

    except Exception as e:
        logger.warning(f"Failed to clear CUDA cache: {e}")
        return 0.0


def unload_shape_pipeline(pipeline: Any) -> dict:
    """
    Fully unload the shape pipeline from GPU.

    This is called before texture generation to free up VRAM.

    Returns dict with before/after VRAM stats.
    """
    import torch

    before_vram = get_vram_usage()
    logger.info(f"Unloading shape pipeline. VRAM before: {before_vram:.2f}GB")

    if pipeline is None:
        return {"before_gb": before_vram, "after_gb": before_vram, "freed_gb": 0}

    try:
        # Step 1: Try pipeline's built-in offloading if available
        if hasattr(pipeline, 'maybe_free_model_hooks'):
            try:
                pipeline.maybe_free_model_hooks()
                logger.info("Called pipeline.maybe_free_model_hooks()")
            except Exception as e:
                logger.warning(f"maybe_free_model_hooks failed: {e}")

        # Step 2: Move main components to CPU
        components_to_move = ['model', 'conditioner', 'vae', 'scheduler',
                             'text_encoder', 'image_encoder', 'unet']

        for comp_name in components_to_move:
            if hasattr(pipeline, comp_name):
                comp = getattr(pipeline, comp_name)
                if comp is not None:
                    move_module_to_cpu(comp, comp_name)

        # Step 3: Check for components dict (hy3dgen style)
        if hasattr(pipeline, 'components'):
            for comp_name, comp in pipeline.components.items():
                if comp is not None and hasattr(comp, 'to'):
                    move_module_to_cpu(comp, comp_name)

        # Step 4: Handle VAE's surface extractor specially (can have cached GPU tensors)
        if hasattr(pipeline, 'vae') and pipeline.vae is not None:
            vae = pipeline.vae
            if hasattr(vae, 'surface_extractor'):
                se = vae.surface_extractor
                # DMCSurfaceExtractor caches self.dmc on GPU
                if hasattr(se, 'dmc') and se.dmc is not None:
                    try:
                        se.dmc.to('cpu')
                        logger.info("Moved surface_extractor.dmc to CPU")
                    except:
                        try:
                            del se.dmc
                            se.dmc = None
                            logger.info("Deleted surface_extractor.dmc")
                        except:
                            pass

        # Step 5: Move entire pipeline to CPU
        move_module_to_cpu(pipeline, "shape_pipeline")

        # Step 6: Clear CUDA cache
        torch.cuda.synchronize()
        gc.collect()
        gc.collect()
        torch.cuda.empty_cache()

    except Exception as e:
        logger.error(f"Error during shape pipeline unload: {e}")
        import traceback
        traceback.print_exc()

    after_vram = get_vram_usage()
    freed = before_vram - after_vram

    logger.info(f"Shape pipeline unloaded. VRAM: {before_vram:.2f}GB -> {after_vram:.2f}GB (freed {freed:.2f}GB)")

    # If we still have significant VRAM usage, log a warning
    if after_vram > 2.0:
        logger.warning(f"Still {after_vram:.2f}GB VRAM in use after unload. This may be Windows/driver overhead.")

    return {
        "before_gb": before_vram,
        "after_gb": after_vram,
        "freed_gb": freed,
    }


def prepare_for_texture(shape_pipeline: Any) -> dict:
    """
    Prepare VRAM for texture generation by unloading shape pipeline.

    For RTX 4090 (24GB):
    - Shape needs ~10GB
    - Texture needs ~21GB
    - Windows/drivers use ~1-2GB
    - We need to free shape completely before texture
    """
    result = unload_shape_pipeline(shape_pipeline)

    # Additional cleanup
    clear_cuda_cache()

    vram_info = get_vram_info()
    logger.info(f"Ready for texture. Available VRAM: {vram_info['free_gb']:.2f}GB")

    # Warn if not enough VRAM
    if vram_info['free_gb'] < 18.0:
        logger.warning(f"Only {vram_info['free_gb']:.2f}GB free. Texture needs ~18-21GB. May fail or be slow.")

    return result


def estimate_baseline_vram() -> float:
    """
    Estimate baseline VRAM usage from Windows/drivers/other apps.

    This is the VRAM that's always in use, not from our models.
    """
    try:
        import subprocess
        import torch

        if not torch.cuda.is_available():
            return 0.0

        # Get total system VRAM usage from nvidia-smi
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            system_used_mb = int(result.stdout.strip())
            system_used_gb = system_used_mb / 1024

            # Get PyTorch's view
            pytorch_used_gb = torch.cuda.memory_allocated(0) / 1e9

            # Baseline is system usage minus PyTorch usage
            baseline = system_used_gb - pytorch_used_gb

            logger.info(f"VRAM baseline estimate: {baseline:.2f}GB (system: {system_used_gb:.2f}GB, pytorch: {pytorch_used_gb:.2f}GB)")

            return max(0, baseline)

    except Exception as e:
        logger.warning(f"Could not estimate baseline VRAM: {e}")

    # Default estimate for Windows with desktop effects
    return 1.5
