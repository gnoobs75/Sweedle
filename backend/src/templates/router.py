"""Router for workflow templates."""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.generation.models import WorkflowTemplate

from .schemas import (
    WorkflowTemplateCreate,
    WorkflowTemplateUpdate,
    WorkflowTemplateResponse,
    WorkflowTemplateList,
    ApplyTemplateRequest,
    ApplyTemplateResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# Built-in templates
BUILTIN_TEMPLATES = [
    {
        "id": "quick-prop",
        "name": "Quick Prop",
        "description": "Fast generation for simple props without rigging",
        "category": "prop",
        "include_mesh": True,
        "include_texture": True,
        "include_rigging": False,
        "include_animation": False,
        "include_export": True,
        "mesh_settings": {
            "inference_steps": 20,
            "octree_resolution": 192,
        },
        "texture_settings": {
            "resolution": 512,
            "camera_views": 4,
        },
        "export_settings": {
            "format": "glb",
            "draco_compression": True,
            "center_pivot": True,
            "ground_origin": True,
        },
    },
    {
        "id": "game-character",
        "name": "Game Character",
        "description": "Full pipeline for game-ready characters with rigging and animations",
        "category": "character",
        "include_mesh": True,
        "include_texture": True,
        "include_rigging": True,
        "include_animation": True,
        "include_export": True,
        "mesh_settings": {
            "inference_steps": 30,
            "octree_resolution": 256,
        },
        "texture_settings": {
            "resolution": 1024,
            "camera_views": 4,
        },
        "rigging_settings": {
            "character_type": "auto",
            "processor": "auto",
            "auto_decimate": True,
            "target_vertices": 30000,
        },
        "animation_settings": {
            "presets": ["idle", "walk", "run"],
            "default_speed": 1.0,
            "default_intensity": 1.0,
        },
        "export_settings": {
            "format": "glb",
            "draco_compression": False,
            "generate_lods": True,
            "lod_levels": [0.5, 0.25],
            "center_pivot": True,
            "ground_origin": True,
        },
    },
    {
        "id": "high-quality",
        "name": "High Quality",
        "description": "Maximum quality settings for hero assets",
        "category": "hero",
        "include_mesh": True,
        "include_texture": True,
        "include_rigging": False,
        "include_animation": False,
        "include_export": True,
        "mesh_settings": {
            "inference_steps": 50,
            "octree_resolution": 384,
        },
        "texture_settings": {
            "resolution": 2048,
            "camera_views": 6,
        },
        "export_settings": {
            "format": "glb",
            "draco_compression": False,
            "center_pivot": True,
            "ground_origin": True,
        },
    },
    {
        "id": "quadruped-creature",
        "name": "Quadruped Creature",
        "description": "Full pipeline for four-legged creatures with rigging and animations",
        "category": "creature",
        "include_mesh": True,
        "include_texture": True,
        "include_rigging": True,
        "include_animation": True,
        "include_export": True,
        "mesh_settings": {
            "inference_steps": 30,
            "octree_resolution": 256,
        },
        "texture_settings": {
            "resolution": 1024,
            "camera_views": 4,
        },
        "rigging_settings": {
            "character_type": "quadruped",
            "processor": "auto",
            "auto_decimate": True,
            "target_vertices": 25000,
        },
        "animation_settings": {
            "presets": ["idle", "trot", "tail_wag"],
            "default_speed": 1.0,
            "default_intensity": 1.0,
        },
        "export_settings": {
            "format": "glb",
            "draco_compression": False,
            "generate_lods": True,
            "lod_levels": [0.5],
            "center_pivot": True,
            "ground_origin": True,
        },
    },
    {
        "id": "environment-asset",
        "name": "Environment Asset",
        "description": "Optimized for static environment objects",
        "category": "environment",
        "include_mesh": True,
        "include_texture": True,
        "include_rigging": False,
        "include_animation": False,
        "include_export": True,
        "mesh_settings": {
            "inference_steps": 25,
            "octree_resolution": 256,
        },
        "texture_settings": {
            "resolution": 1024,
            "camera_views": 4,
        },
        "export_settings": {
            "format": "glb",
            "draco_compression": True,
            "generate_lods": True,
            "lod_levels": [0.5, 0.25, 0.1],
            "center_pivot": True,
            "ground_origin": True,
        },
    },
]


@router.get("/templates", response_model=WorkflowTemplateList)
async def list_templates(
    category: Optional[str] = None,
    include_builtin: bool = True,
    db: AsyncSession = Depends(get_session),
):
    """List all workflow templates."""
    templates = []

    # Add built-in templates
    if include_builtin:
        for template in BUILTIN_TEMPLATES:
            if category is None or template.get("category") == category:
                templates.append(WorkflowTemplateResponse(
                    id=template["id"],
                    name=template["name"],
                    description=template.get("description"),
                    category=template.get("category"),
                    include_mesh=template.get("include_mesh", True),
                    include_texture=template.get("include_texture", True),
                    include_rigging=template.get("include_rigging", False),
                    include_animation=template.get("include_animation", False),
                    include_export=template.get("include_export", True),
                    mesh_settings=template.get("mesh_settings"),
                    texture_settings=template.get("texture_settings"),
                    rigging_settings=template.get("rigging_settings"),
                    animation_settings=template.get("animation_settings"),
                    export_settings=template.get("export_settings"),
                    is_builtin=True,
                    use_count=0,
                    created_at=None,
                    updated_at=None,
                ))

    # Get user-created templates from database
    query = select(WorkflowTemplate)
    if category:
        query = query.where(WorkflowTemplate.category == category)
    query = query.order_by(WorkflowTemplate.use_count.desc())

    result = await db.execute(query)
    db_templates = result.scalars().all()

    for t in db_templates:
        templates.append(WorkflowTemplateResponse(
            id=t.id,
            name=t.name,
            description=t.description,
            category=t.category,
            include_mesh=t.include_mesh,
            include_texture=t.include_texture,
            include_rigging=t.include_rigging,
            include_animation=t.include_animation,
            include_export=t.include_export,
            mesh_settings=t.mesh_settings,
            texture_settings=t.texture_settings,
            rigging_settings=t.rigging_settings,
            animation_settings=t.animation_settings,
            export_settings=t.export_settings,
            is_builtin=t.is_builtin,
            use_count=t.use_count,
            created_at=t.created_at,
            updated_at=t.updated_at,
        ))

    return WorkflowTemplateList(templates=templates, total=len(templates))


@router.get("/templates/{template_id}", response_model=WorkflowTemplateResponse)
async def get_template(
    template_id: str,
    db: AsyncSession = Depends(get_session),
):
    """Get a specific workflow template."""
    # Check built-in templates first
    for template in BUILTIN_TEMPLATES:
        if template["id"] == template_id:
            return WorkflowTemplateResponse(
                id=template["id"],
                name=template["name"],
                description=template.get("description"),
                category=template.get("category"),
                include_mesh=template.get("include_mesh", True),
                include_texture=template.get("include_texture", True),
                include_rigging=template.get("include_rigging", False),
                include_animation=template.get("include_animation", False),
                include_export=template.get("include_export", True),
                mesh_settings=template.get("mesh_settings"),
                texture_settings=template.get("texture_settings"),
                rigging_settings=template.get("rigging_settings"),
                animation_settings=template.get("animation_settings"),
                export_settings=template.get("export_settings"),
                is_builtin=True,
                use_count=0,
                created_at=None,
                updated_at=None,
            )

    # Check database
    result = await db.execute(
        select(WorkflowTemplate).where(WorkflowTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return WorkflowTemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        category=template.category,
        include_mesh=template.include_mesh,
        include_texture=template.include_texture,
        include_rigging=template.include_rigging,
        include_animation=template.include_animation,
        include_export=template.include_export,
        mesh_settings=template.mesh_settings,
        texture_settings=template.texture_settings,
        rigging_settings=template.rigging_settings,
        animation_settings=template.animation_settings,
        export_settings=template.export_settings,
        is_builtin=template.is_builtin,
        use_count=template.use_count,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


@router.post("/templates", response_model=WorkflowTemplateResponse)
async def create_template(
    request: WorkflowTemplateCreate,
    db: AsyncSession = Depends(get_session),
):
    """Create a new workflow template."""
    template_id = str(uuid.uuid4())

    template = WorkflowTemplate(
        id=template_id,
        name=request.name,
        description=request.description,
        category=request.category,
        include_mesh=request.include_mesh,
        include_texture=request.include_texture,
        include_rigging=request.include_rigging,
        include_animation=request.include_animation,
        include_export=request.include_export,
        mesh_settings=request.mesh_settings.model_dump() if request.mesh_settings else None,
        texture_settings=request.texture_settings.model_dump() if request.texture_settings else None,
        rigging_settings=request.rigging_settings.model_dump() if request.rigging_settings else None,
        animation_settings=request.animation_settings.model_dump() if request.animation_settings else None,
        export_settings=request.export_settings.model_dump() if request.export_settings else None,
        is_builtin=False,
        use_count=0,
    )

    db.add(template)
    await db.commit()
    await db.refresh(template)

    logger.info(f"Created workflow template: {template.name} ({template.id})")

    return WorkflowTemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        category=template.category,
        include_mesh=template.include_mesh,
        include_texture=template.include_texture,
        include_rigging=template.include_rigging,
        include_animation=template.include_animation,
        include_export=template.include_export,
        mesh_settings=template.mesh_settings,
        texture_settings=template.texture_settings,
        rigging_settings=template.rigging_settings,
        animation_settings=template.animation_settings,
        export_settings=template.export_settings,
        is_builtin=template.is_builtin,
        use_count=template.use_count,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


@router.patch("/templates/{template_id}", response_model=WorkflowTemplateResponse)
async def update_template(
    template_id: str,
    request: WorkflowTemplateUpdate,
    db: AsyncSession = Depends(get_session),
):
    """Update an existing workflow template."""
    # Check if it's a built-in template
    for template in BUILTIN_TEMPLATES:
        if template["id"] == template_id:
            raise HTTPException(status_code=400, detail="Cannot modify built-in templates")

    result = await db.execute(
        select(WorkflowTemplate).where(WorkflowTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Update fields
    if request.name is not None:
        template.name = request.name
    if request.description is not None:
        template.description = request.description
    if request.category is not None:
        template.category = request.category
    if request.include_mesh is not None:
        template.include_mesh = request.include_mesh
    if request.include_texture is not None:
        template.include_texture = request.include_texture
    if request.include_rigging is not None:
        template.include_rigging = request.include_rigging
    if request.include_animation is not None:
        template.include_animation = request.include_animation
    if request.include_export is not None:
        template.include_export = request.include_export
    if request.mesh_settings is not None:
        template.mesh_settings = request.mesh_settings.model_dump()
    if request.texture_settings is not None:
        template.texture_settings = request.texture_settings.model_dump()
    if request.rigging_settings is not None:
        template.rigging_settings = request.rigging_settings.model_dump()
    if request.animation_settings is not None:
        template.animation_settings = request.animation_settings.model_dump()
    if request.export_settings is not None:
        template.export_settings = request.export_settings.model_dump()

    await db.commit()
    await db.refresh(template)

    return WorkflowTemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        category=template.category,
        include_mesh=template.include_mesh,
        include_texture=template.include_texture,
        include_rigging=template.include_rigging,
        include_animation=template.include_animation,
        include_export=template.include_export,
        mesh_settings=template.mesh_settings,
        texture_settings=template.texture_settings,
        rigging_settings=template.rigging_settings,
        animation_settings=template.animation_settings,
        export_settings=template.export_settings,
        is_builtin=template.is_builtin,
        use_count=template.use_count,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: str,
    db: AsyncSession = Depends(get_session),
):
    """Delete a workflow template."""
    # Check if it's a built-in template
    for template in BUILTIN_TEMPLATES:
        if template["id"] == template_id:
            raise HTTPException(status_code=400, detail="Cannot delete built-in templates")

    result = await db.execute(
        select(WorkflowTemplate).where(WorkflowTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    await db.delete(template)
    await db.commit()

    return {"success": True, "message": f"Deleted template: {template.name}"}


@router.get("/templates/categories")
async def list_categories(
    db: AsyncSession = Depends(get_session),
):
    """List all template categories."""
    categories = set()

    # Built-in categories
    for template in BUILTIN_TEMPLATES:
        if template.get("category"):
            categories.add(template["category"])

    # Database categories
    result = await db.execute(
        select(WorkflowTemplate.category).distinct().where(WorkflowTemplate.category.isnot(None))
    )
    for row in result:
        if row[0]:
            categories.add(row[0])

    return {"categories": sorted(list(categories))}
