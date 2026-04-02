"""Ship Builder API router — TRELLIS.2-4B inference.

Generates 3D ship models from concept art using Microsoft TRELLIS.2-4B.
Lazy model loading, VRAM pre-flight gates, OOM catch with auto-downgrade.
"""

import base64
import gc
import json
import logging
import os
import subprocess
import time
import traceback
import uuid
from io import BytesIO
from pathlib import Path
from typing import Optional

# Windows compatibility: use sdpa attention (no flash_attn)
os.environ.setdefault("ATTN_BACKEND", "sdpa")
os.environ.setdefault("SPARSE_ATTN_BACKEND", "sdpa")

from fastapi import APIRouter, HTTPException
from PIL import Image

from src.config import settings
from src.shipbuilder.schemas import (
    FLEET_CLASS_CONFIG,
    ShipGenerateRequest,
    ShipGenerateResponse,
    VRAMStatusResponse,
)

# TRELLIS.2 environment requirements
os.environ["OPENCV_IO_ENABLE_OPENEXR"] = "1"
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

logger = logging.getLogger(__name__)
router = APIRouter()

# Lazy singleton pipeline
_pipeline = None

# VRAM thresholds (GB free required)
# TRELLIS.2-4B actual usage: ~3GB at 512, ~8GB at 1024
VRAM_THRESHOLD_512 = 6.0
VRAM_THRESHOLD_1024 = 12.0


def _get_vram_info() -> dict:
    """Query nvidia-smi for VRAM status. Returns {free_gb, total_gb, allocated_gb}."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.free,memory.total,memory.used", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split(",")
            free_mb, total_mb, used_mb = float(parts[0]), float(parts[1]), float(parts[2])
            return {
                "free_gb": round(free_mb / 1024, 2),
                "total_gb": round(total_mb / 1024, 2),
                "allocated_gb": round(used_mb / 1024, 2),
            }
    except Exception as e:
        logger.warning(f"nvidia-smi failed: {e}")

    return {"free_gb": 0.0, "total_gb": 0.0, "allocated_gb": 0.0}


def _load_pipeline():
    """Lazy-load TRELLIS.2-4B pipeline. Called on first /generate request.

    Redirects stdout/stderr to devnull during loading because tqdm (used by
    transformers/safetensors weight loading) calls sys.stderr.flush() which
    crashes with [Errno 22] when Electron's piped handles are the stdio.
    """
    import sys

    global _pipeline
    if _pipeline is not None:
        return _pipeline

    from trellis2.pipelines import Trellis2ImageTo3DPipeline

    logger.info("Loading TRELLIS.2-4B pipeline...")

    # Redirect stdout/stderr — tqdm flush crashes on Electron's piped handles
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    devnull = open(os.devnull, 'w')
    sys.stdout = devnull
    sys.stderr = devnull
    try:
        _pipeline = Trellis2ImageTo3DPipeline.from_pretrained("microsoft/TRELLIS.2-4B")
        _pipeline.cuda()
    finally:
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        devnull.close()

    logger.info("TRELLIS.2-4B pipeline loaded and moved to CUDA")
    return _pipeline


def _unload_pipeline():
    """Unload pipeline and free VRAM."""
    global _pipeline
    import torch

    if _pipeline is not None:
        logger.info("Unloading TRELLIS.2 pipeline...")
        del _pipeline
        _pipeline = None

    torch.cuda.empty_cache()
    gc.collect()
    logger.info("VRAM cleared (empty_cache + gc.collect)")


def _decode_image(image_base64: str) -> Image.Image:
    """Decode base64 image string to PIL Image."""
    if "," in image_base64:
        image_base64 = image_base64.split(",", 1)[1]
    img_bytes = base64.b64decode(image_base64)
    return Image.open(BytesIO(img_bytes)).convert("RGBA")


def _remove_background(image: Image.Image) -> Image.Image:
    """Remove background using rembg u2net.

    TRELLIS.2's built-in rembg (RMBG-2.0) is gated on HuggingFace, so we
    use the standard rembg library with u2net instead. Without background
    removal, TRELLIS.2 treats the full rectangle as the object.
    """
    try:
        from rembg import remove
        import numpy as np

        logger.info("Removing background with rembg/u2net...")
        rgb = image.convert("RGB")
        result = remove(rgb)

        alpha = np.array(result)[:, :, 3]
        transparent_pct = (alpha < 128).sum() / alpha.size * 100
        logger.info(f"Background removal: {transparent_pct:.0f}% transparent")
        if transparent_pct < 5:
            logger.warning("Background removal had little effect — image may already be clean")

        result = _crop_to_content(result)
        return result
    except Exception as e:
        logger.warning(f"Background removal failed ({e}), using original image")
        return image


def _crop_to_content(image: Image.Image) -> Image.Image:
    """Crop RGBA image tightly to non-transparent content."""
    import numpy as np

    arr = np.array(image)
    if arr.shape[2] < 4:
        return image

    alpha = arr[:, :, 3]
    rows = np.any(alpha > 128, axis=1)
    cols = np.any(alpha > 128, axis=0)
    if not rows.any():
        return image

    rmin, rmax = np.where(rows)[0][[0, -1]]
    cmin, cmax = np.where(cols)[0][[0, -1]]

    pad = 10
    rmin = max(0, rmin - pad)
    rmax = min(arr.shape[0] - 1, rmax + pad)
    cmin = max(0, cmin - pad)
    cmax = min(arr.shape[1] - 1, cmax + pad)

    cropped = image.crop((cmin, rmin, cmax + 1, rmax + 1))
    logger.info(f"Cropped to content: {image.size[0]}x{image.size[1]} -> {cropped.size[0]}x{cropped.size[1]}")
    return cropped


def _run_trellis(pipeline, image: Image.Image, seed: Optional[int], sampler_steps: int, pipeline_type: str = '512'):
    """Run TRELLIS.2 inference. Returns mesh object."""
    import sys
    import torch

    kwargs = {
        "sparse_structure_sampler_params": {"steps": sampler_steps},
        "shape_slat_sampler_params": {"steps": sampler_steps},
        "tex_slat_sampler_params": {"steps": sampler_steps},
        "pipeline_type": pipeline_type,
    }
    if seed is not None:
        kwargs["seed"] = seed

    logger.info(f"[TRELLIS] Starting pipeline.run(type={pipeline_type}, steps={sampler_steps})...")

    # Clear VRAM between generations to prevent residual tensor contamination
    torch.cuda.empty_cache()
    gc.collect()
    torch.cuda.reset_peak_memory_stats()
    logger.info(f"[TRELLIS] VRAM cleared before generation ({torch.cuda.memory_allocated(0)/1e9:.1f}GB allocated)")

    # Redirect stdout/stderr — tqdm flush crashes on Electron's piped handles
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    devnull = open(os.devnull, 'w')
    sys.stdout = devnull
    sys.stderr = devnull
    try:
        results = pipeline.run(image, **kwargs)
    finally:
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        devnull.close()

    logger.info("[TRELLIS] Pipeline complete.")

    mesh = results[0]
    del results
    torch.cuda.empty_cache()
    gc.collect()

    return mesh


def _export_glb(mesh, output_path: Path, decimation_target: int, texture_size: int):
    """Export mesh to GLB via o_voxel postprocessing, then remove small floating islands."""
    import o_voxel

    glb = o_voxel.postprocess.to_glb(
        vertices=mesh.vertices,
        faces=mesh.faces,
        attr_volume=mesh.attrs,
        coords=mesh.coords,
        attr_layout=mesh.layout,
        voxel_size=mesh.voxel_size,
        aabb=[[-0.5, -0.5, -0.5], [0.5, 0.5, 0.5]],
        decimation_target=decimation_target,
        texture_size=texture_size,
        remesh=False,
        verbose=False,
    )
    glb.export(str(output_path), extension_webp=True)


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/vram-status", response_model=VRAMStatusResponse)
async def vram_status():
    """Check VRAM status before starting generation."""
    info = _get_vram_info()
    ok = info["free_gb"] >= VRAM_THRESHOLD_512

    return VRAMStatusResponse(
        ok=ok,
        free_gb=info["free_gb"],
        total_gb=info["total_gb"],
        allocated_gb=info["allocated_gb"],
        circuit_breaker_tripped=not ok and info["free_gb"] < 8.0,
        message="Ready" if ok else f"Need {VRAM_THRESHOLD_512}GB free, have {info['free_gb']}GB",
    )


@router.post("/vram-reset")
async def vram_reset():
    """Unload pipeline and free VRAM."""
    before = _get_vram_info()
    _unload_pipeline()
    after = _get_vram_info()

    freed = after["free_gb"] - before["free_gb"]
    return {
        "ok": True,
        "freed_gb": round(max(freed, 0), 2),
        "free_gb": after["free_gb"],
        "message": f"Pipeline unloaded, freed {max(freed, 0):.1f}GB",
    }


@router.post("/warm-up")
async def warm_up_pipeline():
    """Pre-load the TRELLIS.2 pipeline so first generation doesn't pay the load cost."""
    global _pipeline
    if _pipeline is not None:
        return {"ok": True, "status": "already_loaded", "message": "Pipeline already loaded"}

    vram = _get_vram_info()
    if vram["free_gb"] < VRAM_THRESHOLD_512:
        return {"ok": False, "status": "insufficient_vram",
                "message": f"Need {VRAM_THRESHOLD_512}GB free VRAM, have {vram['free_gb']}GB"}

    logger.info("Pre-warming TRELLIS.2 pipeline...")
    try:
        _load_pipeline()
        return {"ok": True, "status": "loaded", "message": "Pipeline loaded and ready"}
    except Exception as e:
        logger.error(f"Pipeline warm-up failed: {e}\n{traceback.format_exc()}")
        return {"ok": False, "status": "error", "message": str(e)}


@router.get("/fleet-classes")
async def list_fleet_classes():
    """List available fleet class configurations."""
    return {
        "classes": {
            k: {"label": v["label"], "bbox": v["bbox"], "prompt_suffix": v["prompt_suffix"]}
            for k, v in FLEET_CLASS_CONFIG.items()
        }
    }


@router.post("/generate", response_model=ShipGenerateResponse)
async def generate_ship(request: ShipGenerateRequest):
    """Generate a 3D ship model from concept art using TRELLIS.2-4B.

    Flow:
    1. VRAM pre-flight (auto-downgrade 1024->512 if insufficient)
    2. Decode concept image + remove background
    3. Lazy-load TRELLIS.2 pipeline (synchronous — threading causes [Errno 22] on Windows)
    4. Run inference (with OOM catch + retry at lower res)
    5. Export PBR GLB via o_voxel
    6. Return base64 GLB
    """
    import torch

    start_time = time.time()
    job_id = str(uuid.uuid4())[:8]
    log_prefix = f"[Ship:{request.ship_name}:{job_id}]"

    logger.info(f"{log_prefix} Generation request: resolution={request.resolution}, "
                f"steps={request.sampler_steps}, class={request.class_id}")

    downgraded = False
    downgrade_reason = None
    resolution = request.resolution

    # Step 1: VRAM pre-flight
    vram = _get_vram_info()
    threshold = VRAM_THRESHOLD_1024 if resolution == 1024 else VRAM_THRESHOLD_512

    if vram["free_gb"] < threshold:
        if resolution == 1024 and vram["free_gb"] >= VRAM_THRESHOLD_512:
            logger.warning(f"{log_prefix} VRAM {vram['free_gb']}GB < {VRAM_THRESHOLD_1024}GB, downgrading 1024->512")
            resolution = 512
            downgraded = True
            downgrade_reason = f"VRAM {vram['free_gb']}GB insufficient for 1024 (need {VRAM_THRESHOLD_1024}GB), downgraded to 512"
        else:
            logger.error(f"{log_prefix} VRAM {vram['free_gb']}GB < {VRAM_THRESHOLD_512}GB, cannot generate")
            return ShipGenerateResponse(
                ok=False,
                error=f"Insufficient VRAM: {vram['free_gb']}GB free, need {VRAM_THRESHOLD_512}GB. Try /vram-reset first.",
            )

    # Step 2: Decode image and remove background
    try:
        image = _decode_image(request.image_base64)
        logger.info(f"{log_prefix} Image decoded: {image.size[0]}x{image.size[1]}")
    except Exception as e:
        return ShipGenerateResponse(ok=False, error=f"Invalid image: {e}")

    # Step 2b: Remove background — critical for 3D quality
    image = _remove_background(image)

    # Debug: save what we're feeding to TRELLIS.2 so we can inspect quality
    try:
        debug_dir = Path(settings.STORAGE_ROOT) / "exports" / "debug"
        debug_dir.mkdir(parents=True, exist_ok=True)
        image.save(str(debug_dir / "pre-trellis-input.png"))
        logger.info(f"{log_prefix} Debug: saved pre-pipeline image to {debug_dir / 'pre-trellis-input.png'}")
    except Exception as e:
        logger.warning(f"Could not save debug image: {e}")

    # Step 3: Load pipeline (lazy) — MUST be synchronous
    # asyncio.to_thread causes [Errno 22] on Windows with Electron's piped stdio
    try:
        pipeline = _load_pipeline()
    except Exception as e:
        logger.error(f"{log_prefix} Pipeline load failed: {e}\n{traceback.format_exc()}")
        return ShipGenerateResponse(ok=False, error=f"Failed to load TRELLIS.2 pipeline: {e}")

    # Step 4: Run inference with OOM handling
    mesh = None
    vram_peak = 0.0

    try:
        logger.info(f"{log_prefix} Running TRELLIS.2 inference (resolution={resolution})...")
        mesh = _run_trellis(pipeline, image, request.seed, request.sampler_steps, pipeline_type=str(resolution))

        if torch.cuda.is_available():
            vram_peak = torch.cuda.max_memory_allocated(0) / 1e9

    except RuntimeError as e:
        if "out of memory" not in str(e).lower():
            raise

        logger.error(f"{log_prefix} CUDA OOM at resolution={resolution}")

        if resolution == 1024:
            logger.info(f"{log_prefix} Retrying at 512 after OOM...")
            _unload_pipeline()
            resolution = 512
            downgraded = True
            downgrade_reason = "CUDA OOM at 1024, retried at 512"

            try:
                pipeline = _load_pipeline()
                mesh = _run_trellis(pipeline, image, request.seed, request.sampler_steps, pipeline_type=str(resolution))
                if torch.cuda.is_available():
                    vram_peak = torch.cuda.max_memory_allocated(0) / 1e9
            except RuntimeError as e2:
                if "out of memory" in str(e2).lower():
                    logger.error(f"{log_prefix} OOM at 512 too — giving up")
                    _unload_pipeline()
                    return ShipGenerateResponse(ok=False, error="GPU out of memory at both 1024 and 512. Free VRAM and retry.")
                raise
        else:
            _unload_pipeline()
            return ShipGenerateResponse(ok=False, error="GPU out of memory at 512. Free VRAM and retry.")

    except Exception as e:
        logger.error(f"{log_prefix} Inference failed: {e}\n{traceback.format_exc()}")
        return ShipGenerateResponse(ok=False, error=f"TRELLIS.2 inference failed: {e}")

    # Step 5: Export GLB
    logger.info(f"{log_prefix} Exporting GLB (decimation={request.decimation_target}, texture={request.texture_size})...")

    output_dir = Path(settings.STORAGE_ROOT) / "exports" / "ships"
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_name = "".join(c if c.isalnum() or c in "-_" else "-" for c in request.ship_name)
    output_path = output_dir / f"{safe_name}-{job_id}.glb"

    try:
        _export_glb(mesh, output_path, request.decimation_target, request.texture_size)
    except Exception as e:
        logger.error(f"{log_prefix} GLB export failed: {e}\n{traceback.format_exc()}")
        return ShipGenerateResponse(ok=False, error=f"GLB export failed: {e}")

    # Step 6: Read GLB and return base64
    glb_bytes = output_path.read_bytes()
    glb_base64 = base64.b64encode(glb_bytes).decode("utf-8")
    glb_size_kb = len(glb_bytes) / 1024

    vertex_count = len(mesh.vertices) if hasattr(mesh, 'vertices') else 0
    face_count = len(mesh.faces) if hasattr(mesh, 'faces') else 0

    elapsed = time.time() - start_time

    logger.info(f"{log_prefix} COMPLETE: {vertex_count} verts, {face_count} faces, "
                f"{glb_size_kb:.0f}KB, {elapsed:.1f}s, downgraded={downgraded}")

    return ShipGenerateResponse(
        ok=True,
        glb_base64=glb_base64,
        glb_path=str(output_path).replace("\\", "/"),
        vertex_count=vertex_count,
        face_count=face_count,
        generation_time_s=round(elapsed, 1),
        texture_applied=True,
        vram_peak_gb=round(vram_peak, 2),
        downgraded=downgraded,
        downgrade_reason=downgrade_reason,
    )
