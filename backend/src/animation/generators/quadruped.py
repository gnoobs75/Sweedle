"""
Animation generators for quadruped characters.
"""

import math
from typing import Optional

from .base import BaseAnimationGenerator
from ..schemas import AnimationParameters, AnimationData, KeyframeTrack


class QuadrupedIdleGenerator(BaseAnimationGenerator):
    """Generates idle animation for quadruped characters."""

    def generate(
        self,
        duration: float = 4.0,
        params: Optional[AnimationParameters] = None,
    ) -> AnimationData:
        """
        Generate idle animation with breathing and tail movement.

        Args:
            duration: Animation duration
            params: Animation parameters

        Returns:
            AnimationData with idle keyframes
        """
        params = params or AnimationParameters()
        times = self._create_times(duration, params)
        adjusted_duration = duration / params.speed

        tracks: list[KeyframeTrack] = []

        # Breathing in spine
        if self._has_bone("Spine"):
            tracks.append(self._generate_breathing(times, adjusted_duration, params))

        # Subtle head movement
        if self._has_bone("Head"):
            tracks.append(self._generate_head_idle(times, adjusted_duration, params))

        # Ear twitches
        for side in ["Left", "Right"]:
            ear = f"{side}Ear"
            if self._has_bone(ear):
                tracks.append(self._generate_ear_twitch(ear, times, adjusted_duration, params, side))

        # Tail sway
        for i in range(1, 6):
            tail = f"Tail{i}" if i > 1 else "Tail"
            alt_tail = f"Tail_{i}" if i > 1 else "Tail"
            bone_name = tail if self._has_bone(tail) else alt_tail
            if self._has_bone(bone_name):
                tracks.append(self._generate_tail_sway(bone_name, times, adjusted_duration, params, i))

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
        """Generate breathing in spine."""
        rotations = []
        cycle_time = 4.0

        for t in times:
            phase = (t / cycle_time) * 2 * math.pi
            # Slight vertical movement from breathing
            x_rot = math.sin(phase) * 0.02 * params.intensity
            rotations.append(self._euler_to_quaternion(x_rot, 0, 0))

        return self._create_rotation_track("Spine", times, rotations)

    def _generate_head_idle(
        self,
        times: list[float],
        duration: float,
        params: AnimationParameters,
    ) -> KeyframeTrack:
        """Generate subtle head movements."""
        rotations = []

        for t in times:
            # Random-like movement using multiple frequencies
            x_rot = math.sin(t * 0.5) * 0.015 * params.intensity
            y_rot = math.sin(t * 0.8) * 0.02 * params.intensity
            rotations.append(self._euler_to_quaternion(x_rot, y_rot, 0))

        return self._create_rotation_track("Head", times, rotations)

    def _generate_ear_twitch(
        self,
        bone_name: str,
        times: list[float],
        duration: float,
        params: AnimationParameters,
        side: str,
    ) -> KeyframeTrack:
        """Generate occasional ear twitches."""
        rotations = []
        # Different timing for each ear
        offset = 0.5 if side == "Right" else 0.0

        for t in times:
            # Occasional twitch using a spiky function
            twitch_phase = ((t + offset) % 3.0) / 0.3
            if twitch_phase < 1.0:
                # Quick twitch
                z_rot = math.sin(twitch_phase * math.pi) * 0.15 * params.intensity
            else:
                z_rot = 0

            # Constant slight movement
            base_rot = math.sin(t * 2 + offset) * 0.03 * params.intensity
            z_rot += base_rot

            if side == "Right":
                z_rot = -z_rot

            rotations.append(self._euler_to_quaternion(0, 0, z_rot))

        return self._create_rotation_track(bone_name, times, rotations)

    def _generate_tail_sway(
        self,
        bone_name: str,
        times: list[float],
        duration: float,
        params: AnimationParameters,
        segment: int,
    ) -> KeyframeTrack:
        """Generate gentle tail sway with wave propagation."""
        rotations = []
        # Delay increases along tail for wave effect
        delay = segment * 0.2

        for t in times:
            phase = ((t - delay) / 3.0) * 2 * math.pi
            # Side-to-side sway
            y_rot = math.sin(phase) * 0.08 * params.intensity * (1 + segment * 0.1)
            rotations.append(self._euler_to_quaternion(0, y_rot, 0))

        return self._create_rotation_track(bone_name, times, rotations)


class TrotGenerator(BaseAnimationGenerator):
    """Generates trot animation for quadruped characters."""

    def generate(
        self,
        duration: float = 0.8,
        params: Optional[AnimationParameters] = None,
    ) -> AnimationData:
        """
        Generate diagonal gait trot animation.

        In a trot, diagonal pairs of legs move together:
        - Front left + Back right
        - Front right + Back left

        Args:
            duration: Duration of one complete cycle
            params: Animation parameters

        Returns:
            AnimationData with trot keyframes
        """
        params = params or AnimationParameters()
        times = self._create_times(duration, params)
        adjusted_duration = duration / params.speed

        tracks: list[KeyframeTrack] = []

        # Body bounce
        if self._has_bone("Hips"):
            tracks.append(self._generate_body_bounce(times, adjusted_duration, params))

        # Spine undulation
        if self._has_bone("Spine"):
            tracks.append(self._generate_spine_motion(times, adjusted_duration, params))

        # Front legs (diagonal pairs)
        for side in ["Left", "Right"]:
            phase = 0.0 if side == "Left" else 0.5
            tracks.extend(self._generate_front_leg(times, adjusted_duration, params, side, phase))

        # Back legs (opposite phase)
        for side in ["Left", "Right"]:
            phase = 0.5 if side == "Left" else 0.0
            tracks.extend(self._generate_back_leg(times, adjusted_duration, params, side, phase))

        # Head stabilization
        if self._has_bone("Neck"):
            tracks.append(self._generate_neck_counter(times, adjusted_duration, params))

        # Tail movement
        for i in range(1, 4):
            tail = f"Tail{i}" if i > 1 else "Tail"
            if self._has_bone(tail):
                tracks.append(self._generate_tail_motion(tail, times, adjusted_duration, params, i))

        return AnimationData(
            name="Trot",
            duration=adjusted_duration,
            frame_rate=self.fps,
            tracks=tracks,
        )

    def _generate_body_bounce(
        self,
        times: list[float],
        duration: float,
        params: AnimationParameters,
    ) -> KeyframeTrack:
        """Generate vertical body movement."""
        positions = []

        for t in times:
            phase = (t / duration) * 4 * math.pi
            y = math.sin(phase) * 0.02 * params.intensity
            positions.append([0, y, 0])

        return self._create_position_track("Hips", times, positions)

    def _generate_spine_motion(
        self,
        times: list[float],
        duration: float,
        params: AnimationParameters,
    ) -> KeyframeTrack:
        """Generate spine flexion during trot."""
        rotations = []

        for t in times:
            phase = (t / duration) * 4 * math.pi
            x_rot = math.sin(phase) * 0.04 * params.intensity
            rotations.append(self._euler_to_quaternion(x_rot, 0, 0))

        return self._create_rotation_track("Spine", times, rotations)

    def _generate_front_leg(
        self,
        times: list[float],
        duration: float,
        params: AnimationParameters,
        side: str,
        phase_offset: float,
    ) -> list[KeyframeTrack]:
        """Generate front leg movement."""
        tracks = []
        prefix = f"Front{side}" if self._has_bone(f"Front{side}UpperArm") else f"{side}Front"

        # Upper arm
        upper = f"{prefix}UpperArm" if self._has_bone(f"{prefix}UpperArm") else f"Front{side}Shoulder"
        if self._has_bone(upper):
            rotations = []
            for t in times:
                phase = ((t / duration) + phase_offset) * 2 * math.pi
                x_rot = math.sin(phase) * 0.4 * params.intensity
                rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
            tracks.append(self._create_rotation_track(upper, times, rotations))

        # Lower arm
        lower = f"{prefix}LowerArm" if self._has_bone(f"{prefix}LowerArm") else f"Front{side}Arm"
        if self._has_bone(lower):
            rotations = []
            for t in times:
                phase = ((t / duration) + phase_offset) * 2 * math.pi
                swing = max(0, math.sin(phase))
                x_rot = swing * 0.5 * params.intensity
                rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
            tracks.append(self._create_rotation_track(lower, times, rotations))

        return tracks

    def _generate_back_leg(
        self,
        times: list[float],
        duration: float,
        params: AnimationParameters,
        side: str,
        phase_offset: float,
    ) -> list[KeyframeTrack]:
        """Generate back leg movement."""
        tracks = []
        prefix = f"Back{side}" if self._has_bone(f"Back{side}UpperLeg") else f"{side}Back"

        # Upper leg
        upper = f"{prefix}UpperLeg" if self._has_bone(f"{prefix}UpperLeg") else f"Back{side}Hip"
        if self._has_bone(upper):
            rotations = []
            for t in times:
                phase = ((t / duration) + phase_offset) * 2 * math.pi
                x_rot = math.sin(phase) * 0.35 * params.intensity
                rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
            tracks.append(self._create_rotation_track(upper, times, rotations))

        # Lower leg
        lower = f"{prefix}LowerLeg" if self._has_bone(f"{prefix}LowerLeg") else f"Back{side}Leg"
        if self._has_bone(lower):
            rotations = []
            for t in times:
                phase = ((t / duration) + phase_offset) * 2 * math.pi
                swing = max(0, math.sin(phase))
                x_rot = swing * 0.45 * params.intensity
                rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
            tracks.append(self._create_rotation_track(lower, times, rotations))

        return tracks

    def _generate_neck_counter(
        self,
        times: list[float],
        duration: float,
        params: AnimationParameters,
    ) -> KeyframeTrack:
        """Generate neck counter-movement for head stability."""
        rotations = []

        for t in times:
            phase = (t / duration) * 4 * math.pi
            # Counter the body bounce
            x_rot = -math.sin(phase) * 0.03 * params.intensity
            rotations.append(self._euler_to_quaternion(x_rot, 0, 0))

        return self._create_rotation_track("Neck", times, rotations)

    def _generate_tail_motion(
        self,
        bone_name: str,
        times: list[float],
        duration: float,
        params: AnimationParameters,
        segment: int,
    ) -> KeyframeTrack:
        """Generate tail motion during trot."""
        rotations = []
        delay = segment * 0.1

        for t in times:
            phase = ((t - delay) / duration) * 2 * math.pi
            y_rot = math.sin(phase) * 0.1 * params.intensity
            rotations.append(self._euler_to_quaternion(0, y_rot, 0))

        return self._create_rotation_track(bone_name, times, rotations)


class TailWagGenerator(BaseAnimationGenerator):
    """Generates tail wagging animation for quadrupeds."""

    def generate(
        self,
        duration: float = 1.0,
        params: Optional[AnimationParameters] = None,
    ) -> AnimationData:
        """
        Generate enthusiastic tail wagging animation.

        Args:
            duration: Duration of one wag cycle
            params: Animation parameters

        Returns:
            AnimationData with tail wag keyframes
        """
        params = params or AnimationParameters()
        times = self._create_times(duration, params)
        adjusted_duration = duration / params.speed

        tracks: list[KeyframeTrack] = []

        # Wag each tail segment with increasing amplitude
        for i in range(1, 6):
            tail = f"Tail{i}" if i > 1 else "Tail"
            alt_tail = f"Tail_{i}" if i > 1 else "Tail"
            bone_name = tail if self._has_bone(tail) else alt_tail
            if self._has_bone(bone_name):
                tracks.append(self._generate_tail_wag(bone_name, times, adjusted_duration, params, i))

        # Slight hip wiggle
        if self._has_bone("Hips"):
            tracks.append(self._generate_hip_wiggle(times, adjusted_duration, params))

        return AnimationData(
            name="TailWag",
            duration=adjusted_duration,
            frame_rate=self.fps,
            tracks=tracks,
        )

    def _generate_tail_wag(
        self,
        bone_name: str,
        times: list[float],
        duration: float,
        params: AnimationParameters,
        segment: int,
    ) -> KeyframeTrack:
        """Generate wagging for a tail segment."""
        rotations = []
        delay = segment * 0.05

        for t in times:
            phase = ((t - delay) / (duration / 2)) * 2 * math.pi
            # Amplitude increases along tail
            amplitude = 0.15 * (1 + segment * 0.3) * params.intensity
            y_rot = math.sin(phase) * amplitude
            rotations.append(self._euler_to_quaternion(0, y_rot, 0))

        return self._create_rotation_track(bone_name, times, rotations)

    def _generate_hip_wiggle(
        self,
        times: list[float],
        duration: float,
        params: AnimationParameters,
    ) -> KeyframeTrack:
        """Generate hip wiggle accompanying tail wag."""
        rotations = []

        for t in times:
            phase = (t / (duration / 2)) * 2 * math.pi
            y_rot = math.sin(phase) * 0.03 * params.intensity
            rotations.append(self._euler_to_quaternion(0, y_rot, 0))

        return self._create_rotation_track("Hips", times, rotations)


class BiteGenerator(BaseAnimationGenerator):
    """Generates bite attack animation for quadrupeds."""

    def generate(
        self,
        duration: float = 0.6,
        params: Optional[AnimationParameters] = None,
    ) -> AnimationData:
        """
        Generate lunge and bite attack animation.

        Args:
            duration: Animation duration
            params: Animation parameters

        Returns:
            AnimationData with bite attack keyframes
        """
        params = params or AnimationParameters()
        times = self._create_times(duration, params)
        adjusted_duration = duration / params.speed

        tracks: list[KeyframeTrack] = []

        # Body lunge forward
        if self._has_bone("Hips"):
            tracks.append(self._generate_lunge(times, adjusted_duration, params))

        # Spine extension
        if self._has_bone("Spine"):
            tracks.append(self._generate_spine_extension(times, adjusted_duration, params))

        # Neck strike
        if self._has_bone("Neck"):
            tracks.append(self._generate_neck_strike(times, adjusted_duration, params))

        # Head/jaw snap
        if self._has_bone("Head"):
            tracks.append(self._generate_head_snap(times, adjusted_duration, params))

        if self._has_bone("Jaw"):
            tracks.append(self._generate_jaw_snap(times, adjusted_duration, params))

        # Front legs brace
        for side in ["Left", "Right"]:
            tracks.extend(self._generate_front_brace(times, adjusted_duration, params, side))

        return AnimationData(
            name="Bite",
            duration=adjusted_duration,
            frame_rate=self.fps,
            tracks=tracks,
        )

    def _get_phase(self, t: float, duration: float) -> tuple[str, float]:
        """Determine animation phase."""
        progress = t / duration
        if progress < 0.25:
            return "windup", progress / 0.25
        elif progress < 0.5:
            return "strike", (progress - 0.25) / 0.25
        else:
            return "recovery", (progress - 0.5) / 0.5

    def _generate_lunge(
        self,
        times: list[float],
        duration: float,
        params: AnimationParameters,
    ) -> KeyframeTrack:
        """Generate forward lunge position."""
        positions = []

        for t in times:
            phase, progress = self._get_phase(t, duration)
            if phase == "windup":
                z = -progress * 0.02 * params.intensity  # Pull back slightly
            elif phase == "strike":
                z = (-0.02 + progress * 0.08) * params.intensity  # Lunge forward
            else:
                z = 0.06 * (1 - progress) * params.intensity  # Return
            positions.append([0, 0, z])

        return self._create_position_track("Hips", times, positions)

    def _generate_spine_extension(
        self,
        times: list[float],
        duration: float,
        params: AnimationParameters,
    ) -> KeyframeTrack:
        """Generate spine extension during lunge."""
        rotations = []

        for t in times:
            phase, progress = self._get_phase(t, duration)
            if phase == "strike":
                x_rot = -progress * 0.1 * params.intensity  # Extend spine
            elif phase == "recovery":
                x_rot = -0.1 * (1 - progress) * params.intensity
            else:
                x_rot = 0
            rotations.append(self._euler_to_quaternion(x_rot, 0, 0))

        return self._create_rotation_track("Spine", times, rotations)

    def _generate_neck_strike(
        self,
        times: list[float],
        duration: float,
        params: AnimationParameters,
    ) -> KeyframeTrack:
        """Generate neck strike motion."""
        rotations = []

        for t in times:
            phase, progress = self._get_phase(t, duration)
            if phase == "windup":
                x_rot = progress * 0.2 * params.intensity  # Pull back
            elif phase == "strike":
                x_rot = (0.2 - progress * 0.5) * params.intensity  # Snap forward
            else:
                x_rot = -0.3 * (1 - progress) * params.intensity  # Return
            rotations.append(self._euler_to_quaternion(x_rot, 0, 0))

        return self._create_rotation_track("Neck", times, rotations)

    def _generate_head_snap(
        self,
        times: list[float],
        duration: float,
        params: AnimationParameters,
    ) -> KeyframeTrack:
        """Generate head snap for bite."""
        rotations = []

        for t in times:
            phase, progress = self._get_phase(t, duration)
            if phase == "strike":
                # Quick downward snap
                x_rot = progress * 0.3 * params.intensity
            elif phase == "recovery":
                x_rot = 0.3 * (1 - progress) * params.intensity
            else:
                x_rot = 0
            rotations.append(self._euler_to_quaternion(x_rot, 0, 0))

        return self._create_rotation_track("Head", times, rotations)

    def _generate_jaw_snap(
        self,
        times: list[float],
        duration: float,
        params: AnimationParameters,
    ) -> KeyframeTrack:
        """Generate jaw opening and closing."""
        rotations = []

        for t in times:
            phase, progress = self._get_phase(t, duration)
            if phase == "windup":
                # Open jaw
                x_rot = progress * 0.4 * params.intensity
            elif phase == "strike":
                # Snap shut
                if progress < 0.5:
                    x_rot = 0.4 * (1 - progress * 2) * params.intensity
                else:
                    x_rot = 0
            else:
                x_rot = 0
            rotations.append(self._euler_to_quaternion(x_rot, 0, 0))

        return self._create_rotation_track("Jaw", times, rotations)

    def _generate_front_brace(
        self,
        times: list[float],
        duration: float,
        params: AnimationParameters,
        side: str,
    ) -> list[KeyframeTrack]:
        """Generate front leg bracing motion."""
        tracks = []
        prefix = f"Front{side}"

        upper = f"{prefix}UpperArm" if self._has_bone(f"{prefix}UpperArm") else f"{prefix}Shoulder"
        if self._has_bone(upper):
            rotations = []
            for t in times:
                phase, progress = self._get_phase(t, duration)
                if phase == "strike":
                    x_rot = progress * 0.15 * params.intensity
                elif phase == "recovery":
                    x_rot = 0.15 * (1 - progress) * params.intensity
                else:
                    x_rot = 0
                rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
            tracks.append(self._create_rotation_track(upper, times, rotations))

        return tracks
