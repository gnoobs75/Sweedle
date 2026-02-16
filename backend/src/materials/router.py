"""Materials API router."""

import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database import get_session
from src.generation.models import Asset

from .generator import generate_pbr_maps

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/materials", tags=["materials"])


class GeneratePBRMapsRequest(BaseModel):
    """Request to generate PBR maps."""
    asset_id: str
    normal_strength: float = Field(default=1.0, ge=0.1, le=3.0)
    base_roughness: float = Field(default=0.5, ge=0.0, le=1.0)
    roughness_variance: float = Field(default=0.3, ge=0.0, le=1.0)
    ao_strength: float = Field(default=1.0, ge=0.0, le=2.0)


class PBRMapPaths(BaseModel):
    """Paths to generated PBR maps."""
    color: str
    normal: str
    roughness: str
    metallic: str
    ao: str


class GeneratePBRMapsResponse(BaseModel):
    """Response for PBR map generation."""
    success: bool
    asset_id: str
    maps: Optional[PBRMapPaths] = None
    message: str
    error: Optional[str] = None


class MaterialInfo(BaseModel):
    """Material information for an asset."""
    has_color_texture: bool
    has_normal_map: bool
    has_roughness_map: bool
    has_metallic_map: bool
    has_ao_map: bool
    color_texture_path: Optional[str] = None
    normal_map_path: Optional[str] = None
    roughness_map_path: Optional[str] = None
    metallic_map_path: Optional[str] = None
    ao_map_path: Optional[str] = None


class GetMaterialInfoResponse(BaseModel):
    """Response for material info."""
    success: bool
    asset_id: str
    info: Optional[MaterialInfo] = None
    error: Optional[str] = None


def find_texture_path(asset: Asset) -> Optional[Path]:
    """Find the color texture for an asset."""
    asset_dir = settings.GENERATED_DIR / asset.id

    # Check common texture file names
    texture_names = [
        "texture.png",
        "texture.jpg",
        "color.png",
        "color.jpg",
        "albedo.png",
        "albedo.jpg",
        "diffuse.png",
        "diffuse.jpg",
        f"{asset.id}_texture.png",
    ]

    for name in texture_names:
        path = asset_dir / name
        if path.exists():
            return path

    # Check for any image file
    for ext in ['*.png', '*.jpg', '*.jpeg']:
        files = list(asset_dir.glob(ext))
        for f in files:
            if 'thumbnail' not in f.name.lower():
                return f

    return None


@router.get("/{asset_id}/info", response_model=GetMaterialInfoResponse)
async def get_material_info(
    asset_id: str,
    db: AsyncSession = Depends(get_session),
):
    """Get material information for an asset."""
    try:
        # Get asset
        query = select(Asset).where(Asset.id == asset_id)
        result = await db.execute(query)
        asset = result.scalar_one_or_none()

        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")

        asset_dir = settings.GENERATED_DIR / asset_id

        # Check for textures
        color_path = find_texture_path(asset)
        normal_path = asset_dir / "normal.png"
        roughness_path = asset_dir / "roughness.png"
        metallic_path = asset_dir / "metallic.png"
        ao_path = asset_dir / "ao.png"

        info = MaterialInfo(
            has_color_texture=color_path is not None,
            has_normal_map=normal_path.exists(),
            has_roughness_map=roughness_path.exists(),
            has_metallic_map=metallic_path.exists(),
            has_ao_map=ao_path.exists(),
            color_texture_path=f"/storage/generated/{asset_id}/{color_path.name}" if color_path else None,
            normal_map_path=f"/storage/generated/{asset_id}/normal.png" if normal_path.exists() else None,
            roughness_map_path=f"/storage/generated/{asset_id}/roughness.png" if roughness_path.exists() else None,
            metallic_map_path=f"/storage/generated/{asset_id}/metallic.png" if metallic_path.exists() else None,
            ao_map_path=f"/storage/generated/{asset_id}/ao.png" if ao_path.exists() else None,
        )

        return GetMaterialInfoResponse(
            success=True,
            asset_id=asset_id,
            info=info,
        )

    except Exception as e:
        logger.error(f"Failed to get material info: {e}")
        return GetMaterialInfoResponse(
            success=False,
            asset_id=asset_id,
            error=str(e),
        )


@router.post("/generate-pbr", response_model=GeneratePBRMapsResponse)
async def generate_pbr(
    request: GeneratePBRMapsRequest,
    db: AsyncSession = Depends(get_session),
):
    """Generate PBR material maps from the asset's color texture."""
    try:
        # Get asset
        query = select(Asset).where(Asset.id == request.asset_id)
        result = await db.execute(query)
        asset = result.scalar_one_or_none()

        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")

        # Find color texture
        color_path = find_texture_path(asset)
        if not color_path:
            return GeneratePBRMapsResponse(
                success=False,
                asset_id=request.asset_id,
                message="No color texture found",
                error="Asset does not have a color texture. Generate or add a texture first.",
            )

        # Generate PBR maps
        output_dir = settings.GENERATED_DIR / asset.id
        maps = generate_pbr_maps(
            color_texture_path=color_path,
            output_dir=output_dir,
            prefix="",
            normal_strength=request.normal_strength,
            base_roughness=request.base_roughness,
            roughness_variance=request.roughness_variance,
            ao_strength=request.ao_strength,
        )

        # Create relative paths for response
        pbr_paths = PBRMapPaths(
            color=f"/storage/generated/{asset.id}/{color_path.name}",
            normal=f"/storage/generated/{asset.id}/normal.png",
            roughness=f"/storage/generated/{asset.id}/roughness.png",
            metallic=f"/storage/generated/{asset.id}/metallic.png",
            ao=f"/storage/generated/{asset.id}/ao.png",
        )

        logger.info(f"Generated PBR maps for asset {asset.id}")

        return GeneratePBRMapsResponse(
            success=True,
            asset_id=request.asset_id,
            maps=pbr_paths,
            message="PBR maps generated successfully",
        )

    except Exception as e:
        logger.error(f"Failed to generate PBR maps: {e}")
        return GeneratePBRMapsResponse(
            success=False,
            asset_id=request.asset_id,
            message="Failed to generate PBR maps",
            error=str(e),
        )
