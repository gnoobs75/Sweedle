"""SQLAlchemy ORM models for generation and assets."""

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import backref, relationship
from sqlalchemy.sql import func

from src.database import Base


class AssetStatus(enum.Enum):
    """Asset generation status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowStage(str, enum.Enum):
    """Workflow stage for asset processing pipeline."""
    UPLOADED = "uploaded"           # Image uploaded, not yet generated
    MESH_GENERATED = "mesh_generated"   # Mesh generated, awaiting approval
    MESH_APPROVED = "mesh_approved"     # Mesh approved, ready for texture
    TEXTURED = "textured"               # Texture applied, awaiting approval
    TEXTURE_APPROVED = "texture_approved"  # Texture approved, ready for rigging
    RIGGED = "rigged"                   # Rigged, ready for animation
    ANIMATED = "animated"               # Animations added, ready for export
    EXPORTED = "exported"               # Final export complete


class GenerationType(enum.Enum):
    """Type of generation."""
    IMAGE_TO_3D = "image_to_3d"
    TEXT_TO_3D = "text_to_3d"


class JobStatus(enum.Enum):
    """Job status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Many-to-many relationship table for assets and tags
asset_tags = Table(
    'asset_tags',
    Base.metadata,
    Column('asset_id', String(36), ForeignKey('assets.id', ondelete='CASCADE'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True),
)

# Many-to-many relationship for assets and projects
project_assets = Table(
    'project_assets',
    Base.metadata,
    Column('project_id', String(36), ForeignKey('projects.id', ondelete='CASCADE'), primary_key=True),
    Column('asset_id', String(36), ForeignKey('assets.id', ondelete='CASCADE'), primary_key=True),
)


class Folder(Base):
    """Folder for organizing assets in the library."""
    __tablename__ = "folders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    color = Column(String(7), default="#6366f1")  # Hex color for folder icon
    icon = Column(String(50), default="folder")  # Icon name

    # Hierarchy - parent folder for nested structure
    parent_id = Column(Integer, ForeignKey('folders.id', ondelete='CASCADE'), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    children = relationship("Folder", backref=backref("parent", remote_side=[id]), cascade="all, delete-orphan")
    assets = relationship("Asset", back_populates="folder")


class Tag(Base):
    """Tag for categorizing assets."""
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    color = Column(String(7), default="#6366f1")  # Hex color
    created_at = Column(DateTime, default=func.now())

    # Relationships
    assets = relationship("Asset", secondary=asset_tags, back_populates="tags")


class Asset(Base):
    """Generated 3D asset."""
    __tablename__ = "assets"

    id = Column(String(36), primary_key=True)  # UUID
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Source information
    source_type = Column(SQLEnum(GenerationType), nullable=False)
    source_image_path = Column(String(500), nullable=True)
    source_prompt = Column(Text, nullable=True)

    # Generation parameters
    generation_params = Column(JSON, nullable=True)

    # File paths (relative to GENERATED_DIR)
    file_path = Column(String(500), nullable=False)
    thumbnail_path = Column(String(500), nullable=True)

    # Mesh metadata
    vertex_count = Column(Integer, nullable=True)
    face_count = Column(Integer, nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    generation_time_seconds = Column(Float, nullable=True)

    # Status
    status = Column(SQLEnum(AssetStatus), default=AssetStatus.PENDING)
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # LOD information
    has_lod = Column(Boolean, default=False)
    lod_levels = Column(JSON, nullable=True)

    # Texture information
    has_texture = Column(Boolean, default=False)

    # User preferences
    is_favorite = Column(Boolean, default=False)
    rating = Column(Integer, nullable=True)

    # Rigging information
    is_rigged = Column(Boolean, default=False)
    rigging_data = Column(JSON, nullable=True)  # SkeletonData JSON
    skinning_data = Column(JSON, nullable=True)  # SkinningData JSON (vertex weights)
    character_type = Column(String(50), nullable=True)  # humanoid, quadruped
    rigged_mesh_path = Column(String(500), nullable=True)
    rigging_processor = Column(String(50), nullable=True)  # unirig, blender

    # Animation information
    has_animations = Column(Boolean, default=False)
    animated_mesh_path = Column(String(500), nullable=True)

    # Workflow tracking
    workflow_stage = Column(String(50), default=WorkflowStage.UPLOADED.value)
    mesh_path = Column(String(500), nullable=True)      # Untextured mesh path
    textured_path = Column(String(500), nullable=True)  # Textured mesh path

    # Folder organization
    folder_id = Column(Integer, ForeignKey('folders.id', ondelete='SET NULL'), nullable=True)

    # Variant tracking
    variant_group_id = Column(String(36), ForeignKey('variant_groups.id', ondelete='SET NULL'), nullable=True)
    generation_seed = Column(Integer, nullable=True)  # Random seed used for generation
    variant_index = Column(Integer, nullable=True)  # Order within variant group

    # Relationships
    tags = relationship("Tag", secondary=asset_tags, back_populates="assets")
    projects = relationship("Project", secondary=project_assets, back_populates="assets")
    folder = relationship("Folder", back_populates="assets")
    job = relationship("GenerationJob", back_populates="asset", uselist=False)
    animations = relationship("AnimationClip", back_populates="asset", cascade="all, delete-orphan")
    variant_group = relationship("VariantGroup", back_populates="variants", foreign_keys=[variant_group_id])
    versions = relationship("AssetVersion", back_populates="asset", cascade="all, delete-orphan", order_by="AssetVersion.version_number")


class Project(Base):
    """Project for organizing assets."""
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True)  # UUID
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Engine integration
    engine_type = Column(String(50), nullable=True)
    engine_project_path = Column(String(500), nullable=True)
    default_export_folder = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    assets = relationship("Asset", secondary=project_assets, back_populates="projects")


class GenerationJob(Base):
    """Generation job for queue tracking."""
    __tablename__ = "generation_jobs"

    id = Column(String(36), primary_key=True)  # UUID
    asset_id = Column(String(36), ForeignKey('assets.id'), nullable=True)

    # Job info
    job_type = Column(String(50), nullable=False)
    priority = Column(Integer, default=1)
    status = Column(SQLEnum(JobStatus), default=JobStatus.PENDING)

    # Payload and result
    payload = Column(JSON, nullable=False)
    result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)

    # Progress tracking
    progress = Column(Float, default=0.0)
    stage = Column(String(100), default="pending")

    # Timestamps
    created_at = Column(DateTime, default=func.now())
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    asset = relationship("Asset", back_populates="job")


class AnimationClip(Base):
    """Animation clip attached to an asset."""
    __tablename__ = "animation_clips"

    id = Column(String(36), primary_key=True)  # UUID
    asset_id = Column(String(36), ForeignKey('assets.id', ondelete='CASCADE'), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Animation type
    animation_type = Column(String(50), nullable=False)  # idle, walk, run, attack, etc.
    character_type = Column(String(50), nullable=False)  # humanoid, quadruped

    # Parameters (for procedural regeneration)
    parameters = Column(JSON, nullable=True)  # speed, intensity, blend_factor

    # Animation data
    duration_seconds = Column(Float, nullable=False)
    frame_rate = Column(Integer, default=30)
    loop_mode = Column(String(20), default='loop')  # loop, once, pingpong

    # Keyframe data (for export)
    keyframe_data = Column(JSON, nullable=True)  # Serialized animation tracks

    # File paths
    preview_path = Column(String(500), nullable=True)  # Video/GIF preview

    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationship
    asset = relationship("Asset", back_populates="animations")


class VariantGroup(Base):
    """Group of asset variants generated from the same source."""
    __tablename__ = "variant_groups"

    id = Column(String(36), primary_key=True)  # UUID
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Source information (copied from first asset for reference)
    source_type = Column(SQLEnum(GenerationType), nullable=False)
    source_image_path = Column(String(500), nullable=True)
    source_prompt = Column(Text, nullable=True)

    # Primary variant (the "best" or selected one)
    primary_asset_id = Column(String(36), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    variants = relationship("Asset", back_populates="variant_group", foreign_keys="Asset.variant_group_id")


class AssetVersion(Base):
    """Version history for an asset (tracks changes/edits)."""
    __tablename__ = "asset_versions"

    id = Column(String(36), primary_key=True)  # UUID
    asset_id = Column(String(36), ForeignKey('assets.id', ondelete='CASCADE'), nullable=False)
    version_number = Column(Integer, nullable=False)

    # Change information
    change_type = Column(String(50), nullable=False)  # mesh_edit, texture_change, rigging, animation
    change_description = Column(Text, nullable=True)

    # Snapshot of asset state
    file_path = Column(String(500), nullable=False)  # Backup of the file at this version
    thumbnail_path = Column(String(500), nullable=True)
    vertex_count = Column(Integer, nullable=True)
    face_count = Column(Integer, nullable=True)
    file_size_bytes = Column(Integer, nullable=True)

    # Version metadata
    version_metadata = Column(JSON, nullable=True)  # Additional context about the change

    # Timestamps
    created_at = Column(DateTime, default=func.now())

    # Relationship
    asset = relationship("Asset", back_populates="versions")


class WorkflowTemplate(Base):
    """Reusable workflow template for common pipelines."""
    __tablename__ = "workflow_templates"

    id = Column(String(36), primary_key=True)  # UUID
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)  # character, prop, environment, etc.

    # Template type: what stages are included
    include_mesh = Column(Boolean, default=True)
    include_texture = Column(Boolean, default=True)
    include_rigging = Column(Boolean, default=False)
    include_animation = Column(Boolean, default=False)
    include_export = Column(Boolean, default=True)

    # Mesh generation settings
    mesh_settings = Column(JSON, nullable=True)  # inference_steps, octree_resolution, etc.

    # Texture settings
    texture_settings = Column(JSON, nullable=True)  # resolution, camera_views, etc.

    # Rigging settings
    rigging_settings = Column(JSON, nullable=True)  # character_type, processor, etc.

    # Animation settings
    animation_settings = Column(JSON, nullable=True)  # presets to apply, parameters, etc.

    # Export settings
    export_settings = Column(JSON, nullable=True)  # format, compression, lod_levels, etc.

    # Template metadata
    is_builtin = Column(Boolean, default=False)  # Built-in templates vs user-created
    use_count = Column(Integer, default=0)  # How many times this template was used

    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
