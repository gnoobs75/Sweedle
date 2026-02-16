"""Mesh editing API router."""

import logging
from pathlib import Path

import numpy as np
import trimesh
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database import get_session
from src.generation.models import Asset

from .schemas import (
    CenterPivotRequest,
    CenterPivotResponse,
    CollisionMeshInfo,
    DecimateMeshRequest,
    DecimateMeshResponse,
    GenerateCollisionRequest,
    GenerateCollisionResponse,
    MeshInfo,
    MeshInfoRequest,
    MeshInfoResponse,
    RepairMeshRequest,
    RepairMeshResponse,
    ScaleMeshRequest,
    ScaleMeshResponse,
    SmoothMeshRequest,
    SmoothMeshResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mesh", tags=["mesh"])


def get_mesh_path(asset: Asset) -> Path:
    """Get the mesh file path for an asset."""
    # Check various possible paths
    if asset.textured_path:
        path = settings.GENERATED_DIR / asset.textured_path
        if path.exists():
            return path

    if asset.rigged_mesh_path:
        path = settings.GENERATED_DIR / asset.rigged_mesh_path
        if path.exists():
            return path

    if asset.mesh_path:
        path = settings.GENERATED_DIR / asset.mesh_path
        if path.exists():
            return path

    # Default to file_path
    path = settings.GENERATED_DIR / asset.file_path
    if path.exists():
        return path

    raise FileNotFoundError(f"Mesh file not found for asset {asset.id}")


def load_mesh(path: Path) -> trimesh.Trimesh:
    """Load a mesh from file."""
    mesh = trimesh.load(str(path), force="mesh")
    if isinstance(mesh, trimesh.Scene):
        # Combine all meshes in scene
        mesh = mesh.dump(concatenate=True)
    return mesh


def save_mesh(mesh: trimesh.Trimesh, path: Path) -> None:
    """Save a mesh to file."""
    # Create backup
    backup_path = path.with_suffix(path.suffix + ".bak")
    if path.exists():
        import shutil
        shutil.copy(path, backup_path)

    # Save mesh
    mesh.export(str(path))
    logger.info(f"Saved mesh to {path}")


@router.post("/info", response_model=MeshInfoResponse)
async def get_mesh_info(
    request: MeshInfoRequest,
    db: AsyncSession = Depends(get_session),
):
    """Get detailed mesh information."""
    try:
        # Get asset
        query = select(Asset).where(Asset.id == request.asset_id)
        result = await db.execute(query)
        asset = result.scalar_one_or_none()

        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")

        # Load mesh
        mesh_path = get_mesh_path(asset)
        mesh = load_mesh(mesh_path)

        # Get bounding box
        bounds = mesh.bounds
        center = mesh.centroid

        info = MeshInfo(
            vertexCount=len(mesh.vertices),
            faceCount=len(mesh.faces),
            hasNormals=mesh.vertex_normals is not None and len(mesh.vertex_normals) > 0,
            hasUvs=hasattr(mesh.visual, 'uv') and mesh.visual.uv is not None,
            isWatertight=mesh.is_watertight,
            boundingBoxMin=bounds[0].tolist(),
            boundingBoxMax=bounds[1].tolist(),
            centerOfMass=center.tolist(),
        )

        return MeshInfoResponse(
            success=True,
            asset_id=request.asset_id,
            info=info,
        )

    except FileNotFoundError as e:
        return MeshInfoResponse(
            success=False,
            asset_id=request.asset_id,
            info=MeshInfo(
                vertexCount=0,
                faceCount=0,
                hasNormals=False,
                hasUvs=False,
                isWatertight=False,
                boundingBoxMin=[0, 0, 0],
                boundingBoxMax=[0, 0, 0],
                centerOfMass=[0, 0, 0],
            ),
            error=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to get mesh info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/smooth", response_model=SmoothMeshResponse)
async def smooth_mesh(
    request: SmoothMeshRequest,
    db: AsyncSession = Depends(get_session),
):
    """Apply Laplacian smoothing to a mesh."""
    try:
        # Get asset
        query = select(Asset).where(Asset.id == request.asset_id)
        result = await db.execute(query)
        asset = result.scalar_one_or_none()

        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")

        # Load mesh
        mesh_path = get_mesh_path(asset)
        mesh = load_mesh(mesh_path)

        original_count = len(mesh.vertices)

        # Apply Laplacian smoothing
        # trimesh doesn't have built-in smoothing, so we implement it
        for _ in range(request.iterations):
            # Get vertex neighbors
            adjacency = mesh.vertex_neighbors
            new_vertices = mesh.vertices.copy()

            for i, neighbors in enumerate(adjacency):
                if len(neighbors) > 0:
                    neighbor_positions = mesh.vertices[neighbors]
                    centroid = neighbor_positions.mean(axis=0)
                    new_vertices[i] = (
                        (1 - request.lambda_factor) * mesh.vertices[i] +
                        request.lambda_factor * centroid
                    )

            mesh.vertices = new_vertices

        # Update normals
        mesh.fix_normals()

        # Save mesh
        save_mesh(mesh, mesh_path)

        # Update asset in database
        asset.vertex_count = len(mesh.vertices)
        asset.face_count = len(mesh.faces)
        await db.commit()

        return SmoothMeshResponse(
            success=True,
            asset_id=request.asset_id,
            original_vertex_count=original_count,
            new_vertex_count=len(mesh.vertices),
            message=f"Applied {request.iterations} smoothing iteration(s)",
        )

    except FileNotFoundError as e:
        return SmoothMeshResponse(
            success=False,
            asset_id=request.asset_id,
            original_vertex_count=0,
            new_vertex_count=0,
            message="Failed",
            error=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to smooth mesh: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/repair", response_model=RepairMeshResponse)
async def repair_mesh(
    request: RepairMeshRequest,
    db: AsyncSession = Depends(get_session),
):
    """Repair mesh issues (holes, normals, degenerates)."""
    try:
        # Get asset
        query = select(Asset).where(Asset.id == request.asset_id)
        result = await db.execute(query)
        asset = result.scalar_one_or_none()

        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")

        # Load mesh
        mesh_path = get_mesh_path(asset)
        mesh = load_mesh(mesh_path)

        original_faces = len(mesh.faces)
        original_vertices = len(mesh.vertices)
        holes_filled = 0
        faces_removed = 0
        vertices_merged = 0

        # Fill holes
        if request.fill_holes:
            try:
                trimesh.repair.fill_holes(mesh)
                holes_filled = len(mesh.faces) - original_faces
                if holes_filled < 0:
                    holes_filled = 0
            except Exception as e:
                logger.warning(f"Hole filling failed: {e}")

        # Remove degenerate faces
        if request.remove_degenerates:
            before = len(mesh.faces)
            mesh.remove_degenerate_faces()
            faces_removed = before - len(mesh.faces)

        # Merge duplicate vertices
        if request.merge_duplicates:
            before = len(mesh.vertices)
            mesh.merge_vertices()
            vertices_merged = before - len(mesh.vertices)

        # Fix normals
        normals_fixed = False
        if request.fix_normals:
            mesh.fix_normals()
            normals_fixed = True

        # Save mesh
        save_mesh(mesh, mesh_path)

        # Update asset in database
        asset.vertex_count = len(mesh.vertices)
        asset.face_count = len(mesh.faces)
        await db.commit()

        return RepairMeshResponse(
            success=True,
            asset_id=request.asset_id,
            holes_filled=holes_filled,
            faces_removed=faces_removed,
            vertices_merged=vertices_merged,
            normals_fixed=normals_fixed,
            message="Mesh repair completed",
        )

    except FileNotFoundError as e:
        return RepairMeshResponse(
            success=False,
            asset_id=request.asset_id,
            holes_filled=0,
            faces_removed=0,
            vertices_merged=0,
            normals_fixed=False,
            message="Failed",
            error=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to repair mesh: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/decimate", response_model=DecimateMeshResponse)
async def decimate_mesh(
    request: DecimateMeshRequest,
    db: AsyncSession = Depends(get_session),
):
    """Reduce mesh face count."""
    try:
        # Get asset
        query = select(Asset).where(Asset.id == request.asset_id)
        result = await db.execute(query)
        asset = result.scalar_one_or_none()

        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")

        # Load mesh
        mesh_path = get_mesh_path(asset)
        mesh = load_mesh(mesh_path)

        original_faces = len(mesh.faces)

        # Calculate target faces
        if request.target_faces is not None:
            target = request.target_faces
        elif request.ratio is not None:
            target = int(original_faces * request.ratio)
        else:
            target = original_faces // 2  # Default to 50%

        target = max(100, min(target, original_faces))

        # Decimate using fast_simplification if available
        try:
            import fast_simplification
            simplified_vertices, simplified_faces = fast_simplification.simplify(
                mesh.vertices.astype(np.float32),
                mesh.faces.astype(np.int32),
                target_count=target,
            )
            mesh = trimesh.Trimesh(vertices=simplified_vertices, faces=simplified_faces)
        except ImportError:
            # Fallback to trimesh's simplify (slower)
            mesh = mesh.simplify_quadric_decimation(target)

        # Fix normals after decimation
        mesh.fix_normals()

        # Save mesh
        save_mesh(mesh, mesh_path)

        new_faces = len(mesh.faces)
        reduction = ((original_faces - new_faces) / original_faces) * 100

        # Update asset in database
        asset.vertex_count = len(mesh.vertices)
        asset.face_count = new_faces
        await db.commit()

        return DecimateMeshResponse(
            success=True,
            asset_id=request.asset_id,
            original_faces=original_faces,
            new_faces=new_faces,
            reduction_percent=round(reduction, 1),
            message=f"Reduced from {original_faces} to {new_faces} faces ({reduction:.1f}% reduction)",
        )

    except FileNotFoundError as e:
        return DecimateMeshResponse(
            success=False,
            asset_id=request.asset_id,
            original_faces=0,
            new_faces=0,
            reduction_percent=0,
            message="Failed",
            error=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to decimate mesh: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/center-pivot", response_model=CenterPivotResponse)
async def center_pivot(
    request: CenterPivotRequest,
    db: AsyncSession = Depends(get_session),
):
    """Center the mesh pivot point."""
    try:
        # Get asset
        query = select(Asset).where(Asset.id == request.asset_id)
        result = await db.execute(query)
        asset = result.scalar_one_or_none()

        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")

        # Load mesh
        mesh_path = get_mesh_path(asset)
        mesh = load_mesh(mesh_path)

        # Calculate center
        bounds = mesh.bounds
        center = (bounds[0] + bounds[1]) / 2

        # Calculate offset
        offset = np.zeros(3)
        if request.center_x:
            offset[0] = -center[0]
        if request.center_y:
            offset[1] = -bounds[0][1]  # Move bottom to Y=0
        if request.center_z:
            offset[2] = -center[2]

        # Apply offset
        mesh.vertices += offset

        # Save mesh
        save_mesh(mesh, mesh_path)

        return CenterPivotResponse(
            success=True,
            asset_id=request.asset_id,
            offset_applied=offset.tolist(),
            message="Pivot centered",
        )

    except FileNotFoundError as e:
        return CenterPivotResponse(
            success=False,
            asset_id=request.asset_id,
            offset_applied=[0, 0, 0],
            message="Failed",
            error=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to center pivot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scale", response_model=ScaleMeshResponse)
async def scale_mesh(
    request: ScaleMeshRequest,
    db: AsyncSession = Depends(get_session),
):
    """Scale the mesh."""
    try:
        # Get asset
        query = select(Asset).where(Asset.id == request.asset_id)
        result = await db.execute(query)
        asset = result.scalar_one_or_none()

        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")

        # Load mesh
        mesh_path = get_mesh_path(asset)
        mesh = load_mesh(mesh_path)

        # Calculate scale
        if request.uniform:
            scale = np.array([request.scale_factor] * 3)
        else:
            scale = np.array([
                request.scale_x or 1.0,
                request.scale_y or 1.0,
                request.scale_z or 1.0,
            ])

        # Apply scale
        mesh.vertices *= scale

        # Save mesh
        save_mesh(mesh, mesh_path)

        return ScaleMeshResponse(
            success=True,
            asset_id=request.asset_id,
            scale_applied=scale.tolist(),
            message=f"Scaled by {scale.tolist()}",
        )

    except FileNotFoundError as e:
        return ScaleMeshResponse(
            success=False,
            asset_id=request.asset_id,
            scale_applied=[1, 1, 1],
            message="Failed",
            error=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to scale mesh: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-collision", response_model=GenerateCollisionResponse)
async def generate_collision(
    request: GenerateCollisionRequest,
    db: AsyncSession = Depends(get_session),
):
    """Generate a collision mesh for physics."""

    try:
        # Get asset
        query = select(Asset).where(Asset.id == request.asset_id)
        result = await db.execute(query)
        asset = result.scalar_one_or_none()

        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")

        # Load mesh
        mesh_path = get_mesh_path(asset)
        mesh = load_mesh(mesh_path)

        collision_mesh = None

        if request.method == "convex_hull":
            # Generate convex hull
            collision_mesh = mesh.convex_hull

        elif request.method == "simplified":
            # Simplified version of the mesh
            target_faces = int(len(mesh.faces) * request.simplification_ratio)
            target_faces = max(100, target_faces)

            try:
                import fast_simplification
                simplified_vertices, simplified_faces = fast_simplification.simplify(
                    mesh.vertices.astype(np.float32),
                    mesh.faces.astype(np.int32),
                    target_count=target_faces,
                )
                collision_mesh = trimesh.Trimesh(vertices=simplified_vertices, faces=simplified_faces)
            except ImportError:
                collision_mesh = mesh.simplify_quadric_decimation(target_faces)

        elif request.method == "box":
            # Oriented bounding box
            collision_mesh = mesh.bounding_box_oriented.to_mesh()

        elif request.method == "capsule":
            # Bounding capsule approximation
            # Get oriented bounding box and create a capsule-like shape
            obb = mesh.bounding_box_oriented
            extents = obb.primitive.extents

            # Find longest axis
            axis_idx = np.argmax(extents)
            radius = np.mean([extents[i] for i in range(3) if i != axis_idx]) / 2
            height = extents[axis_idx]

            # Create capsule mesh
            from trimesh.creation import capsule
            collision_mesh = capsule(height=height, radius=radius, count=[8, 8])

            # Transform to match original mesh orientation
            collision_mesh.apply_transform(obb.primitive.transform)

        elif request.method == "sphere":
            # Bounding sphere
            center, radius = mesh.bounding_sphere
            from trimesh.creation import icosphere
            collision_mesh = icosphere(subdivisions=2, radius=radius)
            collision_mesh.vertices += center

        if collision_mesh is None:
            return GenerateCollisionResponse(
                success=False,
                asset_id=request.asset_id,
                message="Failed to generate collision mesh",
                error=f"Unknown method: {request.method}",
            )

        # Save collision mesh
        collision_dir = settings.GENERATED_DIR / asset.id
        collision_path = collision_dir / f"collision_{request.method}.glb"
        collision_mesh.export(str(collision_path))

        file_size = collision_path.stat().st_size

        logger.info(f"Generated {request.method} collision mesh for asset {asset.id}")

        return GenerateCollisionResponse(
            success=True,
            asset_id=request.asset_id,
            collision=CollisionMeshInfo(
                method=request.method,
                vertex_count=len(collision_mesh.vertices),
                face_count=len(collision_mesh.faces),
                file_path=f"/storage/generated/{asset.id}/collision_{request.method}.glb",
                file_size_bytes=file_size,
            ),
            message=f"Generated {request.method} collision mesh with {len(collision_mesh.faces)} faces",
        )

    except FileNotFoundError as e:
        return GenerateCollisionResponse(
            success=False,
            asset_id=request.asset_id,
            message="Failed",
            error=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to generate collision mesh: {e}")
        raise HTTPException(status_code=500, detail=str(e))
