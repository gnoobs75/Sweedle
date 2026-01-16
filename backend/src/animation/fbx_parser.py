"""FBX animation parser using Blender.

This module extracts animation data from FBX files (particularly Mixamo
animations) using Blender's FBX import capabilities.
"""

import asyncio
import json
import logging
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class AnimationTrack:
    """Single animation channel data."""
    bone_name: str
    channel: str  # rotation_quaternion, location, scale
    index: int     # 0-3 for quaternion, 0-2 for position/scale
    keyframes: list[tuple[float, float]]  # (frame, value)


@dataclass
class BoneInfo:
    """Bone information from skeleton."""
    name: str
    parent: Optional[str]
    head: tuple[float, float, float]
    tail: tuple[float, float, float]


@dataclass
class MixamoAnimationData:
    """Parsed Mixamo animation data."""
    name: str
    duration_frames: int
    fps: int
    duration_seconds: float
    bones: dict[str, BoneInfo] = field(default_factory=dict)
    tracks: list[AnimationTrack] = field(default_factory=list)


class FBXAnimationParser:
    """Parse FBX animation files using Blender.

    Uses Blender in background mode to extract animation data from FBX files.
    """

    def __init__(self, blender_path: str = "blender"):
        self._blender_path = blender_path
        self._scripts_dir = Path(__file__).parent / "blender_scripts"
        self._initialized = False
        self._timeout = 120  # 2 minute timeout

    async def initialize(self) -> None:
        """Initialize the parser, ensuring Blender is available."""
        if self._initialized:
            return

        # Check if Blender is available
        blender_available = await self._check_blender()
        if not blender_available:
            raise RuntimeError(
                f"Blender not found at '{self._blender_path}'. "
                "Please install Blender and add it to PATH."
            )

        # Ensure scripts directory exists
        self._scripts_dir.mkdir(parents=True, exist_ok=True)

        # Create parser script
        await self._ensure_scripts()

        self._initialized = True
        logger.info("FBX parser initialized")

    async def _check_blender(self) -> bool:
        """Check if Blender is available."""
        try:
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
        """Ensure Blender scripts exist."""
        script_path = self._scripts_dir / "parse_fbx_animation.py"
        if not script_path.exists():
            script_path.write_text(PARSE_FBX_SCRIPT)
            logger.info("Created parse_fbx_animation.py script")

    async def parse(self, fbx_path: Path) -> MixamoAnimationData:
        """Parse an FBX file and extract animation data.

        Args:
            fbx_path: Path to the FBX file

        Returns:
            MixamoAnimationData with extracted animation
        """
        if not self._initialized:
            await self.initialize()

        if not fbx_path.exists():
            raise FileNotFoundError(f"FBX file not found: {fbx_path}")

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            result_file = temp_path / "animation_data.json"

            # Build Blender command
            script_path = self._scripts_dir / "parse_fbx_animation.py"
            cmd = [
                self._blender_path,
                "--background",
                "--python", str(script_path),
                "--",
                "--input", str(fbx_path),
                "--output", str(result_file),
            ]

            logger.info(f"Parsing FBX: {fbx_path}")

            # Run Blender process
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self._timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                raise RuntimeError(f"FBX parsing timed out after {self._timeout}s")

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.error(f"FBX parsing failed: {error_msg}")
                raise RuntimeError(f"Failed to parse FBX: {error_msg[:500]}")

            # Read result
            if not result_file.exists():
                raise RuntimeError("Blender did not produce animation data file")

            with open(result_file) as f:
                data = json.load(f)

            if not data.get("success"):
                raise RuntimeError(data.get("error", "Unknown parsing error"))

            # Convert to dataclass
            bones = {}
            for name, bone_data in data.get("bones", {}).items():
                bones[name] = BoneInfo(
                    name=name,
                    parent=bone_data.get("parent"),
                    head=tuple(bone_data.get("head", [0, 0, 0])),
                    tail=tuple(bone_data.get("tail", [0, 0, 0])),
                )

            tracks = []
            for track_data in data.get("tracks", []):
                tracks.append(AnimationTrack(
                    bone_name=track_data["bone"],
                    channel=track_data["channel"],
                    index=track_data["index"],
                    keyframes=[(kf[0], kf[1]) for kf in track_data["keyframes"]],
                ))

            fps = data.get("fps", 30)
            duration_frames = data.get("duration_frames", 0)

            return MixamoAnimationData(
                name=data.get("name", fbx_path.stem),
                duration_frames=duration_frames,
                fps=fps,
                duration_seconds=duration_frames / fps if fps > 0 else 0,
                bones=bones,
                tracks=tracks,
            )

    async def validate(self, fbx_path: Path) -> dict:
        """Validate an FBX file without full parsing.

        Returns basic info about the animation for preview.
        """
        try:
            data = await self.parse(fbx_path)
            return {
                "valid": True,
                "name": data.name,
                "duration_seconds": data.duration_seconds,
                "fps": data.fps,
                "bone_count": len(data.bones),
                "track_count": len(data.tracks),
                "bone_names": list(data.bones.keys()),
            }
        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
            }


# Blender Python script for parsing FBX animations
PARSE_FBX_SCRIPT = '''
"""
Blender script to extract animation data from FBX files.
Run with: blender --background --python parse_fbx_animation.py -- --input anim.fbx --output data.json
"""

import argparse
import json
import sys
import os


def main():
    # Parse arguments after --
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []

    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Input FBX file")
    parser.add_argument("--output", required=True, help="Output JSON file")
    args = parser.parse_args(argv)

    result = {"success": False}

    try:
        import bpy

        # Clear default scene
        bpy.ops.wm.read_factory_settings(use_empty=True)

        # Import FBX
        bpy.ops.import_scene.fbx(filepath=args.input)

        # Find armature
        armature = None
        for obj in bpy.data.objects:
            if obj.type == "ARMATURE":
                armature = obj
                break

        if armature is None:
            raise ValueError("No armature found in FBX file")

        # Check for animation data
        if armature.animation_data is None or armature.animation_data.action is None:
            raise ValueError("No animation found in FBX file")

        action = armature.animation_data.action

        # Get animation info
        frame_range = action.frame_range
        fps = bpy.context.scene.render.fps

        result["name"] = action.name
        result["duration_frames"] = int(frame_range[1] - frame_range[0])
        result["fps"] = fps
        result["frame_start"] = int(frame_range[0])
        result["frame_end"] = int(frame_range[1])

        # Extract bone hierarchy
        bones = {}
        for bone in armature.data.bones:
            bones[bone.name] = {
                "parent": bone.parent.name if bone.parent else None,
                "head": list(bone.head_local),
                "tail": list(bone.tail_local),
            }
        result["bones"] = bones

        # Extract animation tracks
        tracks = []
        for fcurve in action.fcurves:
            # Parse data path to get bone name
            # Format: pose.bones["BoneName"].rotation_quaternion
            data_path = fcurve.data_path

            if not data_path.startswith('pose.bones["'):
                continue

            # Extract bone name
            try:
                bone_start = data_path.index('["') + 2
                bone_end = data_path.index('"]')
                bone_name = data_path[bone_start:bone_end]

                # Get channel (rotation_quaternion, location, scale)
                channel = data_path.split(".")[-1]
            except (ValueError, IndexError):
                continue

            # Extract keyframes
            keyframes = []
            for kf in fcurve.keyframe_points:
                keyframes.append([kf.co[0], kf.co[1]])

            tracks.append({
                "bone": bone_name,
                "channel": channel,
                "index": fcurve.array_index,
                "keyframes": keyframes,
            })

        result["tracks"] = tracks
        result["success"] = True

    except Exception as e:
        result["success"] = False
        result["error"] = str(e)
        import traceback
        result["traceback"] = traceback.format_exc()

    # Write result
    with open(args.output, "w") as f:
        json.dump(result, f, indent=2)


if __name__ == "__main__":
    main()
'''


# Global instance
_parser: Optional[FBXAnimationParser] = None


def get_fbx_parser() -> FBXAnimationParser:
    """Get the global FBX parser instance."""
    global _parser
    if _parser is None:
        _parser = FBXAnimationParser()
    return _parser
