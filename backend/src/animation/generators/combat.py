"""
Combat animation generators for humanoids.
"""

import math
from typing import Optional

from .base import BaseAnimationGenerator
from ..schemas import AnimationParameters, AnimationData, KeyframeTrack


class AttackGenerator(BaseAnimationGenerator):
    """Generates attack animation for humanoid characters."""

    def generate(
        self,
        duration: float = 0.8,
        params: Optional[AnimationParameters] = None,
    ) -> AnimationData:
        """
        Generate overhead slash attack animation.

        The animation has three phases:
        1. Wind-up (0-30%): Raise arm and lean back
        2. Strike (30-60%): Fast downward slash
        3. Follow-through (60-100%): Recovery to ready stance

        Args:
            duration: Animation duration
            params: Animation parameters

        Returns:
            AnimationData with attack keyframes
        """
        params = params or AnimationParameters()
        adjusted_duration = duration / params.speed
        times = self._create_times(duration, params)

        tracks: list[KeyframeTrack] = []

        # Core body movement
        if self._has_bone("Hips"):
            tracks.append(self._generate_hips_motion(times, adjusted_duration, params))

        if self._has_bone("Spine"):
            tracks.append(self._generate_spine_motion(times, adjusted_duration, params))

        if self._has_bone("Spine1"):
            tracks.append(self._generate_upper_spine_motion(times, adjusted_duration, params))

        # Right arm (attacking arm)
        tracks.extend(self._generate_attack_arm(times, adjusted_duration, params))

        # Left arm (balance/guard)
        tracks.extend(self._generate_guard_arm(times, adjusted_duration, params))

        # Legs (stance adjustment)
        tracks.extend(self._generate_stance(times, adjusted_duration, params))

        return AnimationData(
            name="Attack",
            duration=adjusted_duration,
            frame_rate=self.fps,
            tracks=tracks,
        )

    def _get_phase(self, t: float, duration: float) -> tuple[str, float]:
        """
        Determine animation phase and local progress.

        Returns:
            Tuple of (phase_name, phase_progress 0-1)
        """
        progress = t / duration

        if progress < 0.3:
            return "windup", progress / 0.3
        elif progress < 0.6:
            return "strike", (progress - 0.3) / 0.3
        else:
            return "recovery", (progress - 0.6) / 0.4

    def _ease_in_out(self, t: float) -> float:
        """Smooth ease in/out curve."""
        return t * t * (3 - 2 * t)

    def _ease_out(self, t: float) -> float:
        """Ease out curve (fast start, slow end)."""
        return 1 - (1 - t) * (1 - t)

    def _generate_hips_motion(
        self,
        times: list[float],
        duration: float,
        params: AnimationParameters,
    ) -> KeyframeTrack:
        """Generate hip rotation during attack."""
        rotations = []

        for t in times:
            phase, progress = self._get_phase(t, duration)

            if phase == "windup":
                # Rotate hips back (coil up)
                y_rot = self._ease_in_out(progress) * 0.15 * params.intensity
            elif phase == "strike":
                # Fast rotation forward
                y_rot = (1 - self._ease_out(progress) * 1.3) * 0.15 * params.intensity
            else:
                # Recovery - return to neutral
                y_rot = -0.045 * (1 - self._ease_in_out(progress)) * params.intensity

            quat = self._euler_to_quaternion(0, y_rot, 0)
            rotations.append(quat)

        return self._create_rotation_track("Hips", times, rotations)

    def _generate_spine_motion(
        self,
        times: list[float],
        duration: float,
        params: AnimationParameters,
    ) -> KeyframeTrack:
        """Generate lower spine motion."""
        rotations = []

        for t in times:
            phase, progress = self._get_phase(t, duration)

            if phase == "windup":
                # Lean back slightly
                x_rot = -self._ease_in_out(progress) * 0.1 * params.intensity
            elif phase == "strike":
                # Lean forward with strike
                x_rot = self._ease_out(progress) * 0.15 * params.intensity - 0.1 * params.intensity
            else:
                # Return to neutral
                x_rot = 0.05 * (1 - self._ease_in_out(progress)) * params.intensity

            quat = self._euler_to_quaternion(x_rot, 0, 0)
            rotations.append(quat)

        return self._create_rotation_track("Spine", times, rotations)

    def _generate_upper_spine_motion(
        self,
        times: list[float],
        duration: float,
        params: AnimationParameters,
    ) -> KeyframeTrack:
        """Generate upper spine twist."""
        rotations = []

        for t in times:
            phase, progress = self._get_phase(t, duration)

            if phase == "windup":
                y_rot = self._ease_in_out(progress) * 0.2 * params.intensity
            elif phase == "strike":
                y_rot = (1 - self._ease_out(progress) * 1.5) * 0.2 * params.intensity
            else:
                y_rot = -0.1 * (1 - self._ease_in_out(progress)) * params.intensity

            quat = self._euler_to_quaternion(0, y_rot, 0)
            rotations.append(quat)

        return self._create_rotation_track("Spine1", times, rotations)

    def _generate_attack_arm(
        self,
        times: list[float],
        duration: float,
        params: AnimationParameters,
    ) -> list[KeyframeTrack]:
        """Generate right arm attack motion."""
        tracks = []

        # Shoulder
        if self._has_bone("RightShoulder"):
            rotations = []
            for t in times:
                phase, progress = self._get_phase(t, duration)
                if phase == "windup":
                    z_rot = -self._ease_in_out(progress) * 0.2 * params.intensity
                elif phase == "strike":
                    z_rot = (-0.2 + self._ease_out(progress) * 0.15) * params.intensity
                else:
                    z_rot = -0.05 * (1 - self._ease_in_out(progress)) * params.intensity
                rotations.append(self._euler_to_quaternion(0, 0, z_rot))
            tracks.append(self._create_rotation_track("RightShoulder", times, rotations))

        # Upper arm
        if self._has_bone("RightArm"):
            rotations = []
            for t in times:
                phase, progress = self._get_phase(t, duration)
                if phase == "windup":
                    # Raise arm up and back
                    x_rot = -self._ease_in_out(progress) * 1.2 * params.intensity
                    z_rot = -self._ease_in_out(progress) * 0.3 * params.intensity
                elif phase == "strike":
                    # Swing down fast
                    x_rot = (-1.2 + self._ease_out(progress) * 2.0) * params.intensity
                    z_rot = -0.3 * (1 - self._ease_out(progress)) * params.intensity
                else:
                    # Return to ready
                    x_rot = 0.8 * (1 - self._ease_in_out(progress)) * params.intensity
                    z_rot = 0
                rotations.append(self._euler_to_quaternion(x_rot, 0, z_rot))
            tracks.append(self._create_rotation_track("RightArm", times, rotations))

        # Forearm
        if self._has_bone("RightForeArm"):
            rotations = []
            for t in times:
                phase, progress = self._get_phase(t, duration)
                if phase == "windup":
                    # Bend elbow
                    x_rot = self._ease_in_out(progress) * 1.5 * params.intensity
                elif phase == "strike":
                    # Extend arm
                    x_rot = (1.5 - self._ease_out(progress) * 1.3) * params.intensity
                else:
                    # Slight bend at end
                    x_rot = 0.2 + 0.1 * (1 - self._ease_in_out(progress)) * params.intensity
                rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
            tracks.append(self._create_rotation_track("RightForeArm", times, rotations))

        return tracks

    def _generate_guard_arm(
        self,
        times: list[float],
        duration: float,
        params: AnimationParameters,
    ) -> list[KeyframeTrack]:
        """Generate left arm guard/balance motion."""
        tracks = []

        # Left arm stays in guard position
        if self._has_bone("LeftArm"):
            rotations = []
            for t in times:
                phase, progress = self._get_phase(t, duration)
                # Slight movement to balance
                if phase == "windup":
                    x_rot = self._ease_in_out(progress) * 0.3 * params.intensity
                elif phase == "strike":
                    x_rot = 0.3 * params.intensity
                else:
                    x_rot = 0.3 * (1 - self._ease_in_out(progress)) * params.intensity
                rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
            tracks.append(self._create_rotation_track("LeftArm", times, rotations))

        if self._has_bone("LeftForeArm"):
            rotations = []
            for t in times:
                # Keep elbow bent in guard
                x_rot = 0.7 * params.intensity
                rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
            tracks.append(self._create_rotation_track("LeftForeArm", times, rotations))

        return tracks

    def _generate_stance(
        self,
        times: list[float],
        duration: float,
        params: AnimationParameters,
    ) -> list[KeyframeTrack]:
        """Generate leg stance during attack."""
        tracks = []

        # Right leg steps forward slightly
        if self._has_bone("RightUpLeg"):
            rotations = []
            for t in times:
                phase, progress = self._get_phase(t, duration)
                if phase == "strike":
                    x_rot = self._ease_out(progress) * 0.15 * params.intensity
                elif phase == "recovery":
                    x_rot = 0.15 * (1 - self._ease_in_out(progress)) * params.intensity
                else:
                    x_rot = 0
                rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
            tracks.append(self._create_rotation_track("RightUpLeg", times, rotations))

        # Left leg braces
        if self._has_bone("LeftUpLeg"):
            rotations = []
            for t in times:
                phase, progress = self._get_phase(t, duration)
                if phase == "windup":
                    x_rot = -self._ease_in_out(progress) * 0.1 * params.intensity
                else:
                    x_rot = -0.1 * (1 - (t / duration)) * params.intensity
                rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
            tracks.append(self._create_rotation_track("LeftUpLeg", times, rotations))

        return tracks
