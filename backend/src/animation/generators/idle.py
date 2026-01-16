"""
Idle/breathing animation generator for humanoids.
"""

import math
from typing import Optional

from .base import BaseAnimationGenerator
from ..schemas import AnimationParameters, AnimationData, KeyframeTrack


class IdleGenerator(BaseAnimationGenerator):
    """Generates idle/breathing animation for humanoid characters."""

    def generate(
        self,
        duration: float = 4.0,
        params: Optional[AnimationParameters] = None,
    ) -> AnimationData:
        """
        Generate idle animation with subtle breathing and weight shift.

        Args:
            duration: Animation duration (default 4 seconds for smooth loop)
            params: Animation parameters

        Returns:
            AnimationData with breathing and idle movement
        """
        params = params or AnimationParameters()
        times = self._create_times(duration, params)
        adjusted_duration = duration / params.speed

        tracks: list[KeyframeTrack] = []

        # Breathing: Spine oscillates slightly
        if self._has_bone("Spine"):
            tracks.append(self._generate_breathing(times, adjusted_duration, params))

        # Subtle weight shift on hips
        if self._has_bone("Hips"):
            tracks.append(self._generate_weight_shift(times, adjusted_duration, params))

        # Head micro-movements
        if self._has_bone("Head"):
            tracks.append(self._generate_head_idle(times, adjusted_duration, params))

        # Shoulder breathing movement
        for side in ["Left", "Right"]:
            bone_name = f"{side}Shoulder"
            if self._has_bone(bone_name):
                tracks.append(
                    self._generate_shoulder_breathing(
                        bone_name, times, adjusted_duration, params, side
                    )
                )

        return AnimationData(
            name="Idle",
            duration=adjusted_duration,
            frame_rate=self.fps,
            tracks=tracks,
        )

    def _generate_breathing(
        self,
        times: list[float],
        duration: float,
        params: AnimationParameters,
    ) -> KeyframeTrack:
        """Generate breathing rotation for spine."""
        rotations = []
        cycle_time = 4.0  # 4 second breathing cycle

        for t in times:
            # Sine wave for breathing (X rotation - chest expands forward)
            phase = (t / cycle_time) * 2 * math.pi
            angle = math.sin(phase) * 0.015 * params.intensity

            quat = self._euler_to_quaternion(angle, 0, 0)
            rotations.append(quat)

        return self._create_rotation_track("Spine", times, rotations)

    def _generate_weight_shift(
        self,
        times: list[float],
        duration: float,
        params: AnimationParameters,
    ) -> KeyframeTrack:
        """Generate subtle weight shift for hips."""
        positions = []
        cycle_time = 8.0  # Slower weight shift cycle

        for t in times:
            # Slow side-to-side movement
            phase = (t / cycle_time) * 2 * math.pi
            x_offset = math.sin(phase) * 0.005 * params.intensity
            positions.append([x_offset, 0, 0])

        return self._create_position_track("Hips", times, positions)

    def _generate_head_idle(
        self,
        times: list[float],
        duration: float,
        params: AnimationParameters,
    ) -> KeyframeTrack:
        """Generate head micro-movements."""
        rotations = []

        for t in times:
            # Use two different frequencies for natural look
            x_rot = math.sin(t * 0.7) * 0.008 * params.intensity
            y_rot = math.sin(t * 1.1) * 0.012 * params.intensity

            quat = self._euler_to_quaternion(x_rot, y_rot, 0)
            rotations.append(quat)

        return self._create_rotation_track("Head", times, rotations)

    def _generate_shoulder_breathing(
        self,
        bone_name: str,
        times: list[float],
        duration: float,
        params: AnimationParameters,
        side: str,
    ) -> KeyframeTrack:
        """Generate shoulder movement with breathing."""
        rotations = []
        cycle_time = 4.0

        for t in times:
            phase = (t / cycle_time) * 2 * math.pi
            # Shoulders rise slightly with inhale
            z_rot = math.sin(phase) * 0.01 * params.intensity
            # Mirror for opposite sides
            if side == "Right":
                z_rot = -z_rot

            quat = self._euler_to_quaternion(0, 0, z_rot)
            rotations.append(quat)

        return self._create_rotation_track(bone_name, times, rotations)
