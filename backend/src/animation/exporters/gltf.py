"""
GLTF/GLB animation exporter.

Embeds animation data into existing GLB files using pygltflib.
"""

import struct
import logging
from pathlib import Path
from typing import Optional

from ..schemas import AnimationData, KeyframeTrack

logger = logging.getLogger(__name__)

# Check for pygltflib availability
try:
    from pygltflib import (
        GLTF2,
        Animation,
        AnimationChannel,
        AnimationChannelTarget,
        AnimationSampler,
        Accessor,
        BufferView,
        FLOAT,
        SCALAR,
        VEC3,
        VEC4,
        LINEAR,
    )
    HAS_PYGLTFLIB = True
except ImportError:
    HAS_PYGLTFLIB = False
    logger.warning("pygltflib not available - GLB animation export disabled")


class GLTFAnimationExporter:
    """Exports animations to GLB files."""

    def __init__(self):
        if not HAS_PYGLTFLIB:
            raise ImportError(
                "pygltflib is required for GLB animation export. "
                "Install it with: pip install pygltflib"
            )

    async def embed_animation(
        self,
        glb_path: Path,
        animation_data: AnimationData,
        output_path: Optional[Path] = None,
    ) -> Path:
        """
        Embed animation data into a GLB file.

        Args:
            glb_path: Source GLB file with skeleton
            animation_data: Animation keyframe data
            output_path: Output path (defaults to input with _animated suffix)

        Returns:
            Path to output GLB file
        """
        output_path = output_path or glb_path.with_stem(f"{glb_path.stem}_animated")

        logger.info(f"Embedding animation '{animation_data.name}' into {glb_path}")

        # Load GLTF
        gltf = GLTF2().load(str(glb_path))

        # Build node name -> index mapping
        node_map = {}
        for i, node in enumerate(gltf.nodes or []):
            if node.name:
                node_map[node.name] = i

        # Get current binary blob
        buffer_data = bytearray(gltf.binary_blob() or b'')

        # Create animation structure
        animation = Animation(
            name=animation_data.name,
            channels=[],
            samplers=[],
        )

        accessor_offset = len(gltf.accessors or [])
        buffer_view_offset = len(gltf.bufferViews or [])

        sampler_index = 0
        view_index = 0

        for track in animation_data.tracks:
            node_index = node_map.get(track.bone_name)
            if node_index is None:
                logger.debug(f"Bone '{track.bone_name}' not found in GLB, skipping")
                continue

            # Determine track type
            if track.rotations:
                values = track.rotations
                path = "rotation"
                accessor_type = VEC4
                components = 4
            elif track.positions:
                values = track.positions
                path = "translation"
                accessor_type = VEC3
                components = 3
            elif track.scales:
                values = track.scales
                path = "scale"
                accessor_type = VEC3
                components = 3
            else:
                continue

            # Encode time data
            times_data = struct.pack(f'{len(track.times)}f', *track.times)

            # Align to 4 bytes
            while len(buffer_data) % 4 != 0:
                buffer_data.append(0)

            times_view_offset = len(buffer_data)
            buffer_data.extend(times_data)

            # Create time accessor
            if gltf.bufferViews is None:
                gltf.bufferViews = []
            gltf.bufferViews.append(BufferView(
                buffer=0,
                byteOffset=times_view_offset,
                byteLength=len(times_data),
            ))

            if gltf.accessors is None:
                gltf.accessors = []
            times_accessor_index = len(gltf.accessors)
            gltf.accessors.append(Accessor(
                bufferView=buffer_view_offset + view_index,
                componentType=FLOAT,
                count=len(track.times),
                type=SCALAR,
                min=[min(track.times)],
                max=[max(track.times)],
            ))
            view_index += 1

            # Encode value data
            flat_values = [v for val in values for v in val]
            values_data = struct.pack(f'{len(flat_values)}f', *flat_values)

            # Align to 4 bytes
            while len(buffer_data) % 4 != 0:
                buffer_data.append(0)

            values_view_offset = len(buffer_data)
            buffer_data.extend(values_data)

            # Create values buffer view
            gltf.bufferViews.append(BufferView(
                buffer=0,
                byteOffset=values_view_offset,
                byteLength=len(values_data),
            ))

            # Create values accessor
            values_accessor_index = len(gltf.accessors)
            gltf.accessors.append(Accessor(
                bufferView=buffer_view_offset + view_index,
                componentType=FLOAT,
                count=len(values),
                type=accessor_type,
            ))
            view_index += 1

            # Create sampler
            animation.samplers.append(AnimationSampler(
                input=times_accessor_index,
                output=values_accessor_index,
                interpolation=LINEAR,
            ))

            # Create channel
            animation.channels.append(AnimationChannel(
                sampler=sampler_index,
                target=AnimationChannelTarget(
                    node=node_index,
                    path=path,
                ),
            ))
            sampler_index += 1

        # Add animation to GLTF if we have any channels
        if animation.channels:
            if gltf.animations is None:
                gltf.animations = []
            gltf.animations.append(animation)

            # Update buffer size
            if gltf.buffers:
                gltf.buffers[0].byteLength = len(buffer_data)

            # Save
            gltf.set_binary_blob(bytes(buffer_data))
            gltf.save(str(output_path))

            logger.info(
                f"Exported animation '{animation_data.name}' with "
                f"{len(animation.channels)} channels to {output_path}"
            )
        else:
            logger.warning(f"No valid animation channels found, copying original file")
            # Just copy the original
            import shutil
            shutil.copy(glb_path, output_path)

        return output_path

    async def embed_multiple_animations(
        self,
        glb_path: Path,
        animations: list[AnimationData],
        output_path: Optional[Path] = None,
    ) -> Path:
        """
        Embed multiple animations into a GLB file.

        Args:
            glb_path: Source GLB file with skeleton
            animations: List of animation data to embed
            output_path: Output path

        Returns:
            Path to output GLB file with all animations
        """
        output_path = output_path or glb_path.with_stem(f"{glb_path.stem}_animated")

        # Process each animation sequentially
        current_path = glb_path
        for i, anim_data in enumerate(animations):
            is_last = i == len(animations) - 1
            temp_output = output_path if is_last else glb_path.with_stem(f"{glb_path.stem}_temp_{i}")

            current_path = await self.embed_animation(
                current_path,
                anim_data,
                temp_output,
            )

            # Clean up temp files
            if not is_last and current_path != glb_path:
                # Keep the file for next iteration
                pass

        logger.info(f"Embedded {len(animations)} animations into {output_path}")
        return output_path
