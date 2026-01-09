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
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.database import Base


class AssetStatus(enum.Enum):
    """Asset generation status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


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

    # User preferences
    is_favorite = Column(Boolean, default=False)
    rating = Column(Integer, nullable=True)

    # Rigging information
    is_rigged = Column(Boolean, default=False)
    rigging_data = Column(JSON, nullable=True)  # SkeletonData JSON
    character_type = Column(String(50), nullable=True)  # humanoid, quadruped
    rigged_mesh_path = Column(String(500), nullable=True)
    rigging_processor = Column(String(50), nullable=True)  # unirig, blender

    # Relationships
    tags = relationship("Tag", secondary=asset_tags, back_populates="assets")
    projects = relationship("Project", secondary=project_assets, back_populates="assets")
    job = relationship("GenerationJob", back_populates="asset", uselist=False)


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
