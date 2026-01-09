"""
Blender headless rigging processor.

Uses Blender in background mode for rigging, providing access to
Rigify and other Blender rigging tools.
"""

import asyncio
import json
import logging
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Callable, Optional

from ..config import rigging_settings
from ..schemas import (
    CharacterType,
    RiggingResult,
    SkeletonData,
    BoneData,
    RiggingProcessor,
)
from .base import BaseRiggingProcessor

logger = logging.getLogger(__name__)


class BlenderProcessor(BaseRiggingProcessor):
    """
    Blender headless rigging processor.

    Runs Blender in background mode to perform rigging operations
    using Rigify or custom rigging scripts.
    """

    name = "blender"
    supported_types = [CharacterType.HUMANOID, CharacterType.QUADRUPED, CharacterType.AUTO]

    def __init__(self):
        self._blender_path = rigging_settings.BLENDER_PATH
        self._timeout = rigging_settings.BLENDER_TIMEOUT
        self._scripts_dir = Path(__file__).parent.parent / "blender_scripts"
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the Blender processor."""
        if self._initialized:
            return

        logger.info("Initializing Blender processor...")

        # Check if Blender is available
        blender_available = await self._check_blender()
        if not blender_available:
            raise RuntimeError(
                f"Blender not found at '{self._blender_path}'. "
                "Please install Blender and add it to PATH, or set RIGGING_BLENDER_PATH."
            )

        # Ensure scripts directory exists
        self._scripts_dir.mkdir(parents=True, exist_ok=True)

        # Create rigging scripts if they don't exist
        await self._ensure_scripts()

        logger.info("Blender processor initialized")
        self._initialized = True

    async def _check_blender(self) -> bool:
        """Check if Blender is available."""
        try:
            # Try to find blender
            if shutil.which(self._blender_path):
                return True

            # Try common paths on Windows
            common_paths = [
                r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
                r"C:\Program Files\Blender Foundation\Blender 4.1\blender.exe",
                r"C:\Program Files\Blender Foundation\Blender 4.0\blender.exe",
                r"C:\Program Files\Blender Foundation\Blender 3.6\blender.exe",
            ]
            for path in common_paths:
                if os.path.exists(path):
                    self._blender_path = path
                    return True

            return False
        except Exception:
            return False

    async def _ensure_scripts(self) -> None:
        """Ensure Blender Python scripts exist."""
        auto_rig_script = self._scripts_dir / "auto_rig.py"
        export_fbx_script = self._scripts_dir / "export_fbx.py"

        if not auto_rig_script.exists():
            auto_rig_script.write_text(AUTO_RIG_SCRIPT)
            logger.info(f"Created auto_rig.py script")

        if not export_fbx_script.exists():
            export_fbx_script.write_text(EXPORT_FBX_SCRIPT)
            logger.info(f"Created export_fbx.py script")

    async def process(
        self,
        mesh_path: Path,
        character_type: CharacterType,
        output_dir: Path,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> RiggingResult:
        """
        Process a mesh using Blender for rigging.

        Args:
            mesh_path: Path to input mesh
            character_type: Character type
            output_dir: Output directory
            progress_callback: Progress callback

        Returns:
            RiggingResult with skeleton and output path
        """
        start_time = time.time()

        try:
            if not self._initialized:
                await self.initialize()

            self._report_progress(progress_callback, 0.05, "Preparing Blender...")

            # Create temp directory for Blender output
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                result_file = temp_path / "result.json"
                output_mesh = output_dir / "rigged.glb"

                # Ensure output directory exists
                output_dir.mkdir(parents=True, exist_ok=True)

                self._report_progress(progress_callback, 0.10, "Starting Blender...")

                # Build Blender command
                script_path = self._scripts_dir / "auto_rig.py"
                cmd = [
                    self._blender_path,
                    "--background",
                    "--python", str(script_path),
                    "--",
                    "--input", str(mesh_path),
                    "--output", str(output_mesh),
                    "--result", str(result_file),
                    "--type", character_type.value,
                ]

                logger.info(f"Running Blender: {' '.join(cmd)}")

                # Run Blender process
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                # Monitor progress from stdout
                progress_task = asyncio.create_task(
                    self._monitor_progress(process.stdout, progress_callback)
                )

                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(),
                        timeout=self._timeout,
                    )
                except asyncio.TimeoutError:
                    process.kill()
                    return RiggingResult(
                        success=False,
                        error=f"Blender process timed out after {self._timeout}s",
                        processing_time=time.time() - start_time,
                    )
                finally:
                    progress_task.cancel()

                if process.returncode != 0:
                    error_msg = stderr.decode() if stderr else "Unknown error"
                    logger.error(f"Blender failed: {error_msg}")
                    return RiggingResult(
                        success=False,
                        error=f"Blender process failed: {error_msg[:500]}",
                        processing_time=time.time() - start_time,
                    )

                self._report_progress(progress_callback, 0.90, "Reading results...")

                # Read result file
                if not result_file.exists():
                    return RiggingResult(
                        success=False,
                        error="Blender did not produce result file",
                        processing_time=time.time() - start_time,
                    )

                with open(result_file) as f:
                    result_data = json.load(f)

                if not result_data.get("success"):
                    return RiggingResult(
                        success=False,
                        error=result_data.get("error", "Unknown error from Blender"),
                        processing_time=time.time() - start_time,
                    )

                # Parse skeleton data
                skeleton_data = None
                if "skeleton" in result_data:
                    bones = [
                        BoneData(
                            name=b["name"],
                            parent=b.get("parent"),
                            head_position=tuple(b["head"]),
                            tail_position=tuple(b["tail"]),
                            rotation=tuple(b.get("rotation", [0, 0, 0, 1])),
                        )
                        for b in result_data["skeleton"]["bones"]
                    ]
                    skeleton_data = SkeletonData(
                        root_bone=result_data["skeleton"]["root_bone"],
                        bones=bones,
                        character_type=CharacterType(result_data["skeleton"]["character_type"]),
                        bone_count=len(bones),
                    )

                self._report_progress(progress_callback, 1.0, "Complete")

                return RiggingResult(
                    success=True,
                    skeleton=skeleton_data,
                    rigged_mesh_path=str(output_mesh),
                    detected_type=CharacterType(result_data.get("character_type", character_type.value)),
                    processor_used=RiggingProcessor.BLENDER,
                    processing_time=time.time() - start_time,
                    vertex_count=result_data.get("vertex_count", 0),
                )

        except Exception as e:
            logger.error(f"Blender processing failed: {e}", exc_info=True)
            return RiggingResult(
                success=False,
                error=str(e),
                processing_time=time.time() - start_time,
            )

    async def _monitor_progress(
        self,
        stdout: asyncio.StreamReader,
        callback: Optional[Callable[[float, str], None]],
    ) -> None:
        """Monitor Blender stdout for progress updates."""
        try:
            while True:
                line = await stdout.readline()
                if not line:
                    break

                text = line.decode().strip()
                if text.startswith("PROGRESS:"):
                    # Parse progress line: PROGRESS:0.5:Stage message
                    parts = text[9:].split(":", 1)
                    if len(parts) == 2:
                        try:
                            progress = float(parts[0])
                            stage = parts[1]
                            self._report_progress(callback, progress, stage)
                        except ValueError:
                            pass
        except asyncio.CancelledError:
            pass

    async def export_fbx(
        self,
        input_path: Path,
        output_path: Path,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> Path:
        """
        Convert a rigged GLB to FBX format using Blender.

        Args:
            input_path: Input GLB file
            output_path: Output FBX file
            progress_callback: Progress callback

        Returns:
            Path to exported FBX file
        """
        if not self._initialized:
            await self.initialize()

        self._report_progress(progress_callback, 0.1, "Starting FBX export...")

        script_path = self._scripts_dir / "export_fbx.py"
        cmd = [
            self._blender_path,
            "--background",
            "--python", str(script_path),
            "--",
            "--input", str(input_path),
            "--output", str(output_path),
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=60,
        )

        if process.returncode != 0:
            error = stderr.decode() if stderr else "Unknown error"
            raise RuntimeError(f"FBX export failed: {error}")

        self._report_progress(progress_callback, 1.0, "FBX export complete")
        return output_path

    async def cleanup(self) -> None:
        """Clean up resources."""
        self._initialized = False


# =============================================================================
# Blender Python Scripts (embedded)
# =============================================================================

AUTO_RIG_SCRIPT = '''
"""
Blender auto-rigging script.
Run with: blender --background --python auto_rig.py -- --input mesh.glb --output rigged.glb --type humanoid
"""

import argparse
import json
import sys
import os

def report_progress(progress: float, stage: str):
    """Report progress to stdout for parsing."""
    print(f"PROGRESS:{progress:.2f}:{stage}", flush=True)

def main():
    # Parse arguments after --
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Input mesh file")
    parser.add_argument("--output", required=True, help="Output rigged mesh")
    parser.add_argument("--result", required=True, help="Result JSON file")
    parser.add_argument("--type", default="humanoid", help="Character type")
    args = parser.parse_args(argv)

    result = {"success": False}

    try:
        import bpy
        from mathutils import Vector

        report_progress(0.1, "Clearing scene...")

        # Clear default scene
        bpy.ops.wm.read_factory_settings(use_empty=True)

        report_progress(0.2, "Importing mesh...")

        # Import mesh based on file extension
        input_path = args.input
        ext = os.path.splitext(input_path)[1].lower()

        if ext in [".glb", ".gltf"]:
            bpy.ops.import_scene.gltf(filepath=input_path)
        elif ext == ".obj":
            bpy.ops.import_scene.obj(filepath=input_path)
        elif ext == ".fbx":
            bpy.ops.import_scene.fbx(filepath=input_path)
        else:
            raise ValueError(f"Unsupported format: {ext}")

        # Find mesh object
        mesh_obj = None
        for obj in bpy.context.scene.objects:
            if obj.type == "MESH":
                mesh_obj = obj
                break

        if mesh_obj is None:
            raise ValueError("No mesh found in imported file")

        result["vertex_count"] = len(mesh_obj.data.vertices)

        report_progress(0.3, "Creating armature...")

        # Create armature based on type
        if args.type == "quadruped":
            armature = create_quadruped_armature(mesh_obj)
        else:
            armature = create_humanoid_armature(mesh_obj)

        report_progress(0.6, "Applying automatic weights...")

        # Parent mesh to armature with automatic weights
        mesh_obj.select_set(True)
        armature.select_set(True)
        bpy.context.view_layer.objects.active = armature

        try:
            bpy.ops.object.parent_set(type="ARMATURE_AUTO")
        except Exception as e:
            # Fallback to envelope weights
            bpy.ops.object.parent_set(type="ARMATURE_ENVELOPE")

        report_progress(0.8, "Exporting rigged mesh...")

        # Export result
        output_path = args.output
        out_ext = os.path.splitext(output_path)[1].lower()

        # Select armature and mesh for export
        bpy.ops.object.select_all(action="DESELECT")
        mesh_obj.select_set(True)
        armature.select_set(True)

        if out_ext in [".glb", ".gltf"]:
            bpy.ops.export_scene.gltf(
                filepath=output_path,
                use_selection=True,
                export_format="GLB" if out_ext == ".glb" else "GLTF_SEPARATE",
            )
        elif out_ext == ".fbx":
            bpy.ops.export_scene.fbx(
                filepath=output_path,
                use_selection=True,
                add_leaf_bones=False,
            )

        report_progress(0.9, "Collecting skeleton data...")

        # Collect skeleton data
        bones_data = []
        for bone in armature.data.bones:
            bones_data.append({
                "name": bone.name,
                "parent": bone.parent.name if bone.parent else None,
                "head": list(bone.head_local),
                "tail": list(bone.tail_local),
                "connected": bone.use_connect,
            })

        result["success"] = True
        result["character_type"] = args.type
        result["skeleton"] = {
            "root_bone": armature.data.bones[0].name if armature.data.bones else "root",
            "character_type": args.type,
            "bones": bones_data,
        }

        report_progress(1.0, "Complete")

    except Exception as e:
        result["success"] = False
        result["error"] = str(e)
        import traceback
        result["traceback"] = traceback.format_exc()

    # Write result
    with open(args.result, "w") as f:
        json.dump(result, f, indent=2)


def create_humanoid_armature(mesh_obj):
    """Create a basic humanoid armature fitted to mesh."""
    import bpy
    from mathutils import Vector

    # Get mesh bounds
    bbox = [mesh_obj.matrix_world @ Vector(corner) for corner in mesh_obj.bound_box]
    min_z = min(v.z for v in bbox)
    max_z = max(v.z for v in bbox)
    height = max_z - min_z
    center_x = sum(v.x for v in bbox) / 8
    center_y = sum(v.y for v in bbox) / 8

    # Create armature
    bpy.ops.object.armature_add(enter_editmode=True)
    armature = bpy.context.object
    armature.name = "Armature"

    # Clear default bone
    bpy.ops.armature.select_all(action="SELECT")
    bpy.ops.armature.delete()

    arm = armature.data
    edit_bones = arm.edit_bones

    # Create humanoid skeleton (simplified)
    # Scale factors
    hip_height = min_z + height * 0.5
    shoulder_height = min_z + height * 0.85
    head_height = min_z + height * 0.95

    # Root/Hips
    hips = edit_bones.new("Hips")
    hips.head = (center_x, center_y, hip_height)
    hips.tail = (center_x, center_y, hip_height + height * 0.05)

    # Spine
    spine = edit_bones.new("Spine")
    spine.head = hips.tail
    spine.tail = (center_x, center_y, hip_height + height * 0.15)
    spine.parent = hips
    spine.use_connect = True

    # Spine1
    spine1 = edit_bones.new("Spine1")
    spine1.head = spine.tail
    spine1.tail = (center_x, center_y, shoulder_height - height * 0.05)
    spine1.parent = spine
    spine1.use_connect = True

    # Neck
    neck = edit_bones.new("Neck")
    neck.head = spine1.tail
    neck.tail = (center_x, center_y, head_height - height * 0.05)
    neck.parent = spine1
    neck.use_connect = True

    # Head
    head = edit_bones.new("Head")
    head.head = neck.tail
    head.tail = (center_x, center_y, max_z)
    head.parent = neck
    head.use_connect = True

    # Left leg
    left_up_leg = edit_bones.new("LeftUpLeg")
    left_up_leg.head = (center_x + height * 0.05, center_y, hip_height)
    left_up_leg.tail = (center_x + height * 0.05, center_y, hip_height - height * 0.25)
    left_up_leg.parent = hips

    left_leg = edit_bones.new("LeftLeg")
    left_leg.head = left_up_leg.tail
    left_leg.tail = (center_x + height * 0.05, center_y, min_z + height * 0.05)
    left_leg.parent = left_up_leg
    left_leg.use_connect = True

    left_foot = edit_bones.new("LeftFoot")
    left_foot.head = left_leg.tail
    left_foot.tail = (center_x + height * 0.05, center_y - height * 0.08, min_z)
    left_foot.parent = left_leg
    left_foot.use_connect = True

    # Right leg
    right_up_leg = edit_bones.new("RightUpLeg")
    right_up_leg.head = (center_x - height * 0.05, center_y, hip_height)
    right_up_leg.tail = (center_x - height * 0.05, center_y, hip_height - height * 0.25)
    right_up_leg.parent = hips

    right_leg = edit_bones.new("RightLeg")
    right_leg.head = right_up_leg.tail
    right_leg.tail = (center_x - height * 0.05, center_y, min_z + height * 0.05)
    right_leg.parent = right_up_leg
    right_leg.use_connect = True

    right_foot = edit_bones.new("RightFoot")
    right_foot.head = right_leg.tail
    right_foot.tail = (center_x - height * 0.05, center_y - height * 0.08, min_z)
    right_foot.parent = right_leg
    right_foot.use_connect = True

    # Left arm
    left_arm = edit_bones.new("LeftArm")
    left_arm.head = (center_x + height * 0.08, center_y, shoulder_height)
    left_arm.tail = (center_x + height * 0.2, center_y, shoulder_height - height * 0.02)
    left_arm.parent = spine1

    left_forearm = edit_bones.new("LeftForeArm")
    left_forearm.head = left_arm.tail
    left_forearm.tail = (center_x + height * 0.35, center_y, shoulder_height - height * 0.04)
    left_forearm.parent = left_arm
    left_forearm.use_connect = True

    left_hand = edit_bones.new("LeftHand")
    left_hand.head = left_forearm.tail
    left_hand.tail = (center_x + height * 0.42, center_y, shoulder_height - height * 0.05)
    left_hand.parent = left_forearm
    left_hand.use_connect = True

    # Right arm
    right_arm = edit_bones.new("RightArm")
    right_arm.head = (center_x - height * 0.08, center_y, shoulder_height)
    right_arm.tail = (center_x - height * 0.2, center_y, shoulder_height - height * 0.02)
    right_arm.parent = spine1

    right_forearm = edit_bones.new("RightForeArm")
    right_forearm.head = right_arm.tail
    right_forearm.tail = (center_x - height * 0.35, center_y, shoulder_height - height * 0.04)
    right_forearm.parent = right_arm
    right_forearm.use_connect = True

    right_hand = edit_bones.new("RightHand")
    right_hand.head = right_forearm.tail
    right_hand.tail = (center_x - height * 0.42, center_y, shoulder_height - height * 0.05)
    right_hand.parent = right_forearm
    right_hand.use_connect = True

    # Exit edit mode
    bpy.ops.object.mode_set(mode="OBJECT")

    return armature


def create_quadruped_armature(mesh_obj):
    """Create a basic quadruped armature fitted to mesh."""
    import bpy
    from mathutils import Vector

    # Get mesh bounds
    bbox = [mesh_obj.matrix_world @ Vector(corner) for corner in mesh_obj.bound_box]
    min_x = min(v.x for v in bbox)
    max_x = max(v.x for v in bbox)
    min_y = min(v.y for v in bbox)
    max_y = max(v.y for v in bbox)
    min_z = min(v.z for v in bbox)
    max_z = max(v.z for v in bbox)

    width = max_x - min_x
    length = max_y - min_y
    height = max_z - min_z

    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2

    # Create armature
    bpy.ops.object.armature_add(enter_editmode=True)
    armature = bpy.context.object
    armature.name = "Armature"

    # Clear default bone
    bpy.ops.armature.select_all(action="SELECT")
    bpy.ops.armature.delete()

    arm = armature.data
    edit_bones = arm.edit_bones

    # Quadruped skeleton
    hip_y = center_y + length * 0.3
    shoulder_y = center_y - length * 0.3
    body_height = min_z + height * 0.6

    # Hips
    hips = edit_bones.new("Hips")
    hips.head = (center_x, hip_y, body_height)
    hips.tail = (center_x, hip_y - length * 0.1, body_height)

    # Spine
    spine = edit_bones.new("Spine")
    spine.head = hips.tail
    spine.tail = (center_x, center_y, body_height + height * 0.05)
    spine.parent = hips
    spine.use_connect = True

    spine1 = edit_bones.new("Spine1")
    spine1.head = spine.tail
    spine1.tail = (center_x, shoulder_y + length * 0.1, body_height + height * 0.1)
    spine1.parent = spine
    spine1.use_connect = True

    # Neck and Head
    neck = edit_bones.new("Neck")
    neck.head = spine1.tail
    neck.tail = (center_x, shoulder_y - length * 0.1, body_height + height * 0.2)
    neck.parent = spine1
    neck.use_connect = True

    head = edit_bones.new("Head")
    head.head = neck.tail
    head.tail = (center_x, min_y, body_height + height * 0.15)
    head.parent = neck
    head.use_connect = True

    # Tail
    tail = edit_bones.new("Tail")
    tail.head = (center_x, hip_y + length * 0.1, body_height - height * 0.05)
    tail.tail = (center_x, max_y, body_height - height * 0.15)
    tail.parent = hips

    # Back legs
    leg_offset = width * 0.2

    # Left back leg
    left_back_hip = edit_bones.new("LeftBackHip")
    left_back_hip.head = (center_x + leg_offset, hip_y, body_height - height * 0.1)
    left_back_hip.tail = (center_x + leg_offset, hip_y, body_height - height * 0.3)
    left_back_hip.parent = hips

    left_back_leg = edit_bones.new("LeftBackLeg")
    left_back_leg.head = left_back_hip.tail
    left_back_leg.tail = (center_x + leg_offset, hip_y, min_z + height * 0.05)
    left_back_leg.parent = left_back_hip
    left_back_leg.use_connect = True

    left_back_paw = edit_bones.new("LeftBackPaw")
    left_back_paw.head = left_back_leg.tail
    left_back_paw.tail = (center_x + leg_offset, hip_y - length * 0.05, min_z)
    left_back_paw.parent = left_back_leg
    left_back_paw.use_connect = True

    # Right back leg
    right_back_hip = edit_bones.new("RightBackHip")
    right_back_hip.head = (center_x - leg_offset, hip_y, body_height - height * 0.1)
    right_back_hip.tail = (center_x - leg_offset, hip_y, body_height - height * 0.3)
    right_back_hip.parent = hips

    right_back_leg = edit_bones.new("RightBackLeg")
    right_back_leg.head = right_back_hip.tail
    right_back_leg.tail = (center_x - leg_offset, hip_y, min_z + height * 0.05)
    right_back_leg.parent = right_back_hip
    right_back_leg.use_connect = True

    right_back_paw = edit_bones.new("RightBackPaw")
    right_back_paw.head = right_back_leg.tail
    right_back_paw.tail = (center_x - leg_offset, hip_y - length * 0.05, min_z)
    right_back_paw.parent = right_back_leg
    right_back_paw.use_connect = True

    # Front legs
    # Left front leg
    left_front_shoulder = edit_bones.new("LeftFrontShoulder")
    left_front_shoulder.head = (center_x + leg_offset, shoulder_y, body_height)
    left_front_shoulder.tail = (center_x + leg_offset, shoulder_y, body_height - height * 0.2)
    left_front_shoulder.parent = spine1

    left_front_leg = edit_bones.new("LeftFrontLeg")
    left_front_leg.head = left_front_shoulder.tail
    left_front_leg.tail = (center_x + leg_offset, shoulder_y, min_z + height * 0.05)
    left_front_leg.parent = left_front_shoulder
    left_front_leg.use_connect = True

    left_front_paw = edit_bones.new("LeftFrontPaw")
    left_front_paw.head = left_front_leg.tail
    left_front_paw.tail = (center_x + leg_offset, shoulder_y - length * 0.05, min_z)
    left_front_paw.parent = left_front_leg
    left_front_paw.use_connect = True

    # Right front leg
    right_front_shoulder = edit_bones.new("RightFrontShoulder")
    right_front_shoulder.head = (center_x - leg_offset, shoulder_y, body_height)
    right_front_shoulder.tail = (center_x - leg_offset, shoulder_y, body_height - height * 0.2)
    right_front_shoulder.parent = spine1

    right_front_leg = edit_bones.new("RightFrontLeg")
    right_front_leg.head = right_front_shoulder.tail
    right_front_leg.tail = (center_x - leg_offset, shoulder_y, min_z + height * 0.05)
    right_front_leg.parent = right_front_shoulder
    right_front_leg.use_connect = True

    right_front_paw = edit_bones.new("RightFrontPaw")
    right_front_paw.head = right_front_leg.tail
    right_front_paw.tail = (center_x - leg_offset, shoulder_y - length * 0.05, min_z)
    right_front_paw.parent = right_front_leg
    right_front_paw.use_connect = True

    # Exit edit mode
    bpy.ops.object.mode_set(mode="OBJECT")

    return armature


if __name__ == "__main__":
    main()
'''

EXPORT_FBX_SCRIPT = '''
"""
Blender FBX export script.
Run with: blender --background --python export_fbx.py -- --input rigged.glb --output model.fbx
"""

import argparse
import sys
import os

def main():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Input file (GLB)")
    parser.add_argument("--output", required=True, help="Output FBX file")
    args = parser.parse_args(argv)

    import bpy

    # Clear scene
    bpy.ops.wm.read_factory_settings(use_empty=True)

    # Import GLB
    bpy.ops.import_scene.gltf(filepath=args.input)

    # Export FBX
    bpy.ops.export_scene.fbx(
        filepath=args.output,
        use_selection=False,
        apply_scale_options="FBX_SCALE_ALL",
        add_leaf_bones=False,
        primary_bone_axis="Y",
        secondary_bone_axis="X",
        use_armature_deform_only=True,
    )

    print(f"Exported FBX to {args.output}")


if __name__ == "__main__":
    main()
'''
