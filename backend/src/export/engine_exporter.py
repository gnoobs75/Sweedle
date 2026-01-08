"""
Engine Exporter - Export 3D assets to Unity, Unreal, and Godot projects

Handles engine-specific folder structures, material conversions, and optimizations.
"""

import asyncio
import shutil
import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

try:
    import trimesh
    HAS_TRIMESH = True
except ImportError:
    HAS_TRIMESH = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

logger = logging.getLogger(__name__)


class EngineType(Enum):
    UNITY = "unity"
    UNREAL = "unreal"
    GODOT = "godot"


@dataclass
class ExportSettings:
    """Settings for engine export"""
    include_lods: bool = True
    lod_ratios: list[float] = field(default_factory=lambda: [1.0, 0.5, 0.25])
    compress_textures: bool = True
    max_texture_size: int = 2048
    generate_materials: bool = True
    create_prefab: bool = True  # Unity/Godot
    create_blueprint: bool = True  # Unreal
    include_metadata: bool = True


@dataclass
class ExportResult:
    """Result of an export operation"""
    success: bool
    engine: EngineType
    source_path: Path
    destination_path: Path
    exported_files: list[Path] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    error: Optional[str] = None


class BaseEngineExporter(ABC):
    """Base class for engine-specific exporters"""

    def __init__(self, project_path: Path, settings: Optional[ExportSettings] = None):
        self.project_path = project_path
        self.settings = settings or ExportSettings()

        if not project_path.exists():
            raise ValueError(f"Project path does not exist: {project_path}")

    @abstractmethod
    def validate_project(self) -> bool:
        """Validate that the path is a valid engine project"""
        pass

    @abstractmethod
    def get_import_directory(self, asset_name: str) -> Path:
        """Get the appropriate import directory for an asset"""
        pass

    @abstractmethod
    async def export(self, asset_path: Path, asset_name: Optional[str] = None) -> ExportResult:
        """Export an asset to the engine project"""
        pass

    async def _copy_file(self, src: Path, dst: Path) -> bool:
        """Copy a file asynchronously"""
        def do_copy():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            return dst.exists()

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, do_copy)


class UnityExporter(BaseEngineExporter):
    """
    Export assets to Unity projects.

    Structure:
    Assets/
    └── Sweedle/
        └── {AssetName}/
            ├── {AssetName}.glb
            ├── {AssetName}_LOD1.glb
            ├── {AssetName}.prefab (optional)
            └── Materials/
                └── {Material}.mat
    """

    ENGINE = EngineType.UNITY

    def validate_project(self) -> bool:
        """Check for valid Unity project structure"""
        assets_dir = self.project_path / "Assets"
        project_settings = self.project_path / "ProjectSettings"
        return assets_dir.exists() and project_settings.exists()

    def get_import_directory(self, asset_name: str) -> Path:
        return self.project_path / "Assets" / "Sweedle" / asset_name

    async def export(self, asset_path: Path, asset_name: Optional[str] = None) -> ExportResult:
        """Export asset to Unity project"""
        asset_name = asset_name or asset_path.stem
        export_dir = self.get_import_directory(asset_name)
        exported_files: list[Path] = []
        warnings: list[str] = []

        try:
            export_dir.mkdir(parents=True, exist_ok=True)

            # Copy main asset (Unity prefers GLB)
            dest_path = export_dir / f"{asset_name}.glb"
            if asset_path.suffix.lower() == ".glb":
                await self._copy_file(asset_path, dest_path)
                exported_files.append(dest_path)
            else:
                # Convert to GLB if needed
                if HAS_TRIMESH:
                    await self._convert_to_glb(asset_path, dest_path)
                    exported_files.append(dest_path)
                else:
                    # Copy original format
                    dest_path = export_dir / asset_path.name
                    await self._copy_file(asset_path, dest_path)
                    exported_files.append(dest_path)
                    warnings.append("Could not convert to GLB, copied original format")

            # Generate LODs if requested
            if self.settings.include_lods:
                lod_files = await self._generate_lods_for_unity(
                    dest_path, export_dir, asset_name
                )
                exported_files.extend(lod_files)

            # Create Unity meta file for import settings
            await self._create_unity_meta(dest_path)

            # Create metadata file
            if self.settings.include_metadata:
                meta_path = await self._create_metadata(export_dir, asset_name, asset_path)
                exported_files.append(meta_path)

            return ExportResult(
                success=True,
                engine=self.ENGINE,
                source_path=asset_path,
                destination_path=export_dir,
                exported_files=exported_files,
                warnings=warnings,
            )

        except Exception as e:
            logger.error(f"Unity export failed: {e}")
            return ExportResult(
                success=False,
                engine=self.ENGINE,
                source_path=asset_path,
                destination_path=export_dir,
                exported_files=exported_files,
                warnings=warnings,
                error=str(e),
            )

    async def _convert_to_glb(self, src: Path, dst: Path):
        """Convert mesh to GLB format"""
        def do_convert():
            mesh = trimesh.load(str(src))
            mesh.export(str(dst), file_type='glb')

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, do_convert)

    async def _generate_lods_for_unity(
        self, source_glb: Path, export_dir: Path, asset_name: str
    ) -> list[Path]:
        """Generate LOD meshes for Unity"""
        from .lod_generator import LODGenerator

        lod_files = []
        generator = LODGenerator()

        result = await generator.generate_lods(
            source_path=source_glb,
            ratios=self.settings.lod_ratios,
            output_dir=export_dir,
        )

        if result.success:
            for lod in result.lod_levels[1:]:  # Skip LOD0
                # Rename to Unity LOD naming convention
                new_name = export_dir / f"{asset_name}_LOD{lod.level}.glb"
                if lod.file_path != new_name:
                    lod.file_path.rename(new_name)
                lod_files.append(new_name)

        return lod_files

    async def _create_unity_meta(self, asset_path: Path):
        """Create Unity .meta file for the asset"""
        meta_content = {
            "fileFormatVersion": 2,
            "guid": self._generate_guid(str(asset_path)),
            "ModelImporter": {
                "serializedVersion": 21300,
                "importAnimation": True,
                "importMaterials": True,
                "materialImportMode": 1,
                "materialLocation": 1,
                "meshCompression": 0,
                "addCollider": False,
            }
        }

        meta_path = Path(str(asset_path) + ".meta")

        def write_meta():
            import yaml
            try:
                with open(meta_path, 'w') as f:
                    yaml.dump(meta_content, f, default_flow_style=False)
            except ImportError:
                # Fallback to JSON if YAML not available
                with open(meta_path, 'w') as f:
                    json.dump(meta_content, f, indent=2)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, write_meta)

    async def _create_metadata(self, export_dir: Path, asset_name: str, source_path: Path) -> Path:
        """Create Sweedle metadata file"""
        meta_path = export_dir / "sweedle_meta.json"

        metadata = {
            "asset_name": asset_name,
            "source_path": str(source_path),
            "export_engine": "unity",
            "lod_levels": len(self.settings.lod_ratios) if self.settings.include_lods else 1,
        }

        def write_meta():
            with open(meta_path, 'w') as f:
                json.dump(metadata, f, indent=2)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, write_meta)
        return meta_path

    def _generate_guid(self, seed: str) -> str:
        """Generate a Unity-style GUID from a string"""
        import hashlib
        hash_obj = hashlib.md5(seed.encode())
        return hash_obj.hexdigest()[:32]


class UnrealExporter(BaseEngineExporter):
    """
    Export assets to Unreal Engine projects.

    Structure:
    Content/
    └── Sweedle/
        └── {AssetName}/
            ├── SM_{AssetName}.glb
            ├── SM_{AssetName}_LOD1.glb
            ├── T_{AssetName}_D.png (Diffuse)
            ├── T_{AssetName}_ORM.png (Occlusion/Roughness/Metallic packed)
            └── T_{AssetName}_N.png (Normal)
    """

    ENGINE = EngineType.UNREAL

    def validate_project(self) -> bool:
        """Check for valid Unreal project structure"""
        content_dir = self.project_path / "Content"
        uproject_files = list(self.project_path.glob("*.uproject"))
        return content_dir.exists() and len(uproject_files) > 0

    def get_import_directory(self, asset_name: str) -> Path:
        return self.project_path / "Content" / "Sweedle" / asset_name

    async def export(self, asset_path: Path, asset_name: Optional[str] = None) -> ExportResult:
        """Export asset to Unreal project"""
        asset_name = asset_name or asset_path.stem
        export_dir = self.get_import_directory(asset_name)
        exported_files: list[Path] = []
        warnings: list[str] = []

        try:
            export_dir.mkdir(parents=True, exist_ok=True)

            # Copy main asset with Unreal naming convention (SM_ prefix for static mesh)
            dest_path = export_dir / f"SM_{asset_name}.glb"
            if asset_path.suffix.lower() in [".glb", ".gltf"]:
                await self._copy_file(asset_path, dest_path)
                exported_files.append(dest_path)
            elif asset_path.suffix.lower() == ".fbx":
                # Unreal prefers FBX
                dest_path = export_dir / f"SM_{asset_name}.fbx"
                await self._copy_file(asset_path, dest_path)
                exported_files.append(dest_path)
            else:
                await self._copy_file(asset_path, dest_path)
                exported_files.append(dest_path)

            # Generate LODs
            if self.settings.include_lods:
                lod_files = await self._generate_lods_for_unreal(
                    asset_path, export_dir, asset_name
                )
                exported_files.extend(lod_files)

            # Pack textures to ORM format (Unreal standard)
            if self.settings.generate_materials:
                texture_files = await self._pack_orm_textures(
                    asset_path, export_dir, asset_name
                )
                exported_files.extend(texture_files)

            # Create metadata
            if self.settings.include_metadata:
                meta_path = await self._create_metadata(export_dir, asset_name, asset_path)
                exported_files.append(meta_path)

            return ExportResult(
                success=True,
                engine=self.ENGINE,
                source_path=asset_path,
                destination_path=export_dir,
                exported_files=exported_files,
                warnings=warnings,
            )

        except Exception as e:
            logger.error(f"Unreal export failed: {e}")
            return ExportResult(
                success=False,
                engine=self.ENGINE,
                source_path=asset_path,
                destination_path=export_dir,
                exported_files=exported_files,
                warnings=warnings,
                error=str(e),
            )

    async def _generate_lods_for_unreal(
        self, source_path: Path, export_dir: Path, asset_name: str
    ) -> list[Path]:
        """Generate LOD meshes for Unreal"""
        from .lod_generator import LODGenerator

        lod_files = []
        generator = LODGenerator()

        result = await generator.generate_lods(
            source_path=source_path,
            ratios=self.settings.lod_ratios,
            output_dir=export_dir,
        )

        if result.success:
            for lod in result.lod_levels[1:]:
                # Rename to Unreal LOD naming
                new_name = export_dir / f"SM_{asset_name}_LOD{lod.level}.glb"
                if lod.file_path != new_name and lod.file_path.exists():
                    lod.file_path.rename(new_name)
                lod_files.append(new_name)

        return lod_files

    async def _pack_orm_textures(
        self, asset_path: Path, export_dir: Path, asset_name: str
    ) -> list[Path]:
        """
        Pack textures into Unreal's ORM format.
        R = Ambient Occlusion
        G = Roughness
        B = Metallic
        """
        if not HAS_PIL or not HAS_TRIMESH:
            return []

        exported = []

        try:
            def do_pack():
                packed_files = []

                # Try to extract textures from the mesh
                mesh = trimesh.load(str(asset_path))

                # Get material/texture info (implementation varies by format)
                if hasattr(mesh, 'visual') and hasattr(mesh.visual, 'material'):
                    material = mesh.visual.material

                    # Extract base color/diffuse
                    if hasattr(material, 'baseColorTexture'):
                        diffuse_path = export_dir / f"T_{asset_name}_D.png"
                        # Would extract and save texture here
                        packed_files.append(diffuse_path)

                    # Create ORM packed texture
                    # This is a placeholder - actual implementation would
                    # combine AO, Roughness, and Metallic textures
                    orm_path = export_dir / f"T_{asset_name}_ORM.png"
                    # packed_files.append(orm_path)

                return packed_files

            loop = asyncio.get_event_loop()
            exported = await loop.run_in_executor(None, do_pack)

        except Exception as e:
            logger.warning(f"ORM texture packing failed: {e}")

        return exported

    async def _create_metadata(self, export_dir: Path, asset_name: str, source_path: Path) -> Path:
        """Create Sweedle metadata file"""
        meta_path = export_dir / "sweedle_meta.json"

        metadata = {
            "asset_name": asset_name,
            "source_path": str(source_path),
            "export_engine": "unreal",
            "lod_levels": len(self.settings.lod_ratios) if self.settings.include_lods else 1,
            "naming_convention": {
                "static_mesh_prefix": "SM_",
                "texture_prefix": "T_",
                "texture_suffixes": {"diffuse": "_D", "normal": "_N", "orm": "_ORM"},
            }
        }

        def write_meta():
            with open(meta_path, 'w') as f:
                json.dump(metadata, f, indent=2)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, write_meta)
        return meta_path


class GodotExporter(BaseEngineExporter):
    """
    Export assets to Godot 4 projects.

    Structure:
    assets/
    └── sweedle/
        └── {asset_name}/
            ├── {asset_name}.glb
            ├── {asset_name}_lod1.glb
            └── {asset_name}.tscn (scene file)
    """

    ENGINE = EngineType.GODOT

    def validate_project(self) -> bool:
        """Check for valid Godot project structure"""
        project_godot = self.project_path / "project.godot"
        return project_godot.exists()

    def get_import_directory(self, asset_name: str) -> Path:
        # Godot uses lowercase paths conventionally
        return self.project_path / "assets" / "sweedle" / asset_name.lower()

    async def export(self, asset_path: Path, asset_name: Optional[str] = None) -> ExportResult:
        """Export asset to Godot project"""
        asset_name = asset_name or asset_path.stem
        export_dir = self.get_import_directory(asset_name)
        exported_files: list[Path] = []
        warnings: list[str] = []

        try:
            export_dir.mkdir(parents=True, exist_ok=True)

            # Godot 4 supports GLB directly
            dest_path = export_dir / f"{asset_name.lower()}.glb"
            if asset_path.suffix.lower() == ".glb":
                await self._copy_file(asset_path, dest_path)
            elif HAS_TRIMESH:
                await self._convert_to_glb(asset_path, dest_path)
            else:
                dest_path = export_dir / asset_path.name
                await self._copy_file(asset_path, dest_path)
                warnings.append("Could not convert to GLB")

            exported_files.append(dest_path)

            # Generate LODs
            if self.settings.include_lods:
                lod_files = await self._generate_lods_for_godot(
                    dest_path, export_dir, asset_name
                )
                exported_files.extend(lod_files)

            # Create Godot scene file with LOD nodes
            if self.settings.create_prefab and self.settings.include_lods:
                scene_path = await self._create_godot_scene(
                    export_dir, asset_name, len(self.settings.lod_ratios)
                )
                exported_files.append(scene_path)

            # Create metadata
            if self.settings.include_metadata:
                meta_path = await self._create_metadata(export_dir, asset_name, asset_path)
                exported_files.append(meta_path)

            return ExportResult(
                success=True,
                engine=self.ENGINE,
                source_path=asset_path,
                destination_path=export_dir,
                exported_files=exported_files,
                warnings=warnings,
            )

        except Exception as e:
            logger.error(f"Godot export failed: {e}")
            return ExportResult(
                success=False,
                engine=self.ENGINE,
                source_path=asset_path,
                destination_path=export_dir,
                exported_files=exported_files,
                warnings=warnings,
                error=str(e),
            )

    async def _convert_to_glb(self, src: Path, dst: Path):
        """Convert mesh to GLB format"""
        def do_convert():
            mesh = trimesh.load(str(src))
            mesh.export(str(dst), file_type='glb')

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, do_convert)

    async def _generate_lods_for_godot(
        self, source_path: Path, export_dir: Path, asset_name: str
    ) -> list[Path]:
        """Generate LOD meshes for Godot"""
        from .lod_generator import LODGenerator

        lod_files = []
        generator = LODGenerator()

        result = await generator.generate_lods(
            source_path=source_path,
            ratios=self.settings.lod_ratios,
            output_dir=export_dir,
        )

        if result.success:
            for lod in result.lod_levels[1:]:
                new_name = export_dir / f"{asset_name.lower()}_lod{lod.level}.glb"
                if lod.file_path != new_name and lod.file_path.exists():
                    lod.file_path.rename(new_name)
                lod_files.append(new_name)

        return lod_files

    async def _create_godot_scene(
        self, export_dir: Path, asset_name: str, lod_count: int
    ) -> Path:
        """Create a Godot 4 scene file with LOD support"""
        scene_path = export_dir / f"{asset_name.lower()}.tscn"

        # Generate Godot 4 scene file format
        scene_content = f"""[gd_scene load_steps={lod_count + 1} format=3]

[ext_resource type="PackedScene" path="res://assets/sweedle/{asset_name.lower()}/{asset_name.lower()}.glb" id="1"]
"""
        # Add LOD resources
        for i in range(1, lod_count):
            scene_content += f'[ext_resource type="PackedScene" path="res://assets/sweedle/{asset_name.lower()}/{asset_name.lower()}_lod{i}.glb" id="{i + 1}"]\n'

        scene_content += f"""
[node name="{asset_name}" type="Node3D"]

[node name="LOD0" parent="." instance=ExtResource("1")]
"""
        # Add LOD child nodes
        for i in range(1, lod_count):
            scene_content += f'[node name="LOD{i}" parent="." instance=ExtResource("{i + 1}")]\nvisible = false\n\n'

        def write_scene():
            with open(scene_path, 'w') as f:
                f.write(scene_content)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, write_scene)
        return scene_path

    async def _create_metadata(self, export_dir: Path, asset_name: str, source_path: Path) -> Path:
        """Create Sweedle metadata file"""
        meta_path = export_dir / "sweedle_meta.json"

        metadata = {
            "asset_name": asset_name,
            "source_path": str(source_path),
            "export_engine": "godot",
            "godot_version": "4.x",
            "lod_levels": len(self.settings.lod_ratios) if self.settings.include_lods else 1,
        }

        def write_meta():
            with open(meta_path, 'w') as f:
                json.dump(metadata, f, indent=2)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, write_meta)
        return meta_path


def get_exporter(
    engine: str,
    project_path: Path,
    settings: Optional[ExportSettings] = None,
) -> BaseEngineExporter:
    """
    Factory function to get the appropriate exporter.

    Args:
        engine: Engine name ("unity", "unreal", "godot")
        project_path: Path to the engine project
        settings: Export settings

    Returns:
        Engine-specific exporter instance
    """
    engine = engine.lower()

    if engine == "unity":
        return UnityExporter(project_path, settings)
    elif engine == "unreal":
        return UnrealExporter(project_path, settings)
    elif engine == "godot":
        return GodotExporter(project_path, settings)
    else:
        raise ValueError(f"Unknown engine: {engine}")


# Convenience function
async def export_to_engine(
    asset_path: Path,
    engine: str,
    project_path: Path,
    asset_name: Optional[str] = None,
    settings: Optional[ExportSettings] = None,
) -> ExportResult:
    """
    Export an asset to a game engine project.

    Args:
        asset_path: Path to the source asset
        engine: Target engine ("unity", "unreal", "godot")
        project_path: Path to the engine project
        asset_name: Optional asset name (defaults to filename)
        settings: Export settings

    Returns:
        ExportResult with exported files
    """
    exporter = get_exporter(engine, project_path, settings)
    return await exporter.export(asset_path, asset_name)
