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


class GallopGenerator(BaseAnimationGenerator):
    """Generates gallop/run animation for quadruped characters."""

    def generate(
        self,
        duration: float = 0.5,
        params: Optional[AnimationParameters] = None,
    ) -> AnimationData:
        """
        Generate gallop animation - fast running gait.

        In a gallop, legs move in a rotary pattern with a suspension phase.
        """
        params = params or AnimationParameters()
        times = self._create_times(duration, params)
        adjusted_duration = duration / params.speed

        tracks: list[KeyframeTrack] = []

        # Body bounce with suspension phase
        if self._has_bone("Hips"):
            tracks.append(self._generate_body_gallop(times, adjusted_duration, params))

        # Spine undulation - more pronounced than trot
        if self._has_bone("Spine"):
            tracks.append(self._generate_spine_gallop(times, adjusted_duration, params))

        # Front legs - reach and pull
        for side in ["Left", "Right"]:
            phase = 0.0 if side == "Left" else 0.15
            tracks.extend(self._generate_front_gallop(times, adjusted_duration, params, side, phase))

        # Back legs - power stroke
        for side in ["Left", "Right"]:
            phase = 0.25 if side == "Left" else 0.4
            tracks.extend(self._generate_back_gallop(times, adjusted_duration, params, side, phase))

        # Head stabilization
        if self._has_bone("Neck"):
            tracks.append(self._generate_neck_stabilize(times, adjusted_duration, params))

        return AnimationData(
            name="Gallop",
            duration=adjusted_duration,
            frame_rate=self.fps,
            tracks=tracks,
        )

    def _generate_body_gallop(self, times, duration, params):
        positions = []
        for t in times:
            phase = (t / duration) * 2 * math.pi
            # Higher bounce with suspension
            y = math.sin(phase) * 0.05 * params.intensity
            z = math.cos(phase) * 0.02 * params.intensity
            positions.append([0, y, z])
        return self._create_position_track("Hips", times, positions)

    def _generate_spine_gallop(self, times, duration, params):
        rotations = []
        for t in times:
            phase = (t / duration) * 2 * math.pi
            x_rot = math.sin(phase) * 0.1 * params.intensity
            rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
        return self._create_rotation_track("Spine", times, rotations)

    def _generate_front_gallop(self, times, duration, params, side, phase_offset):
        tracks = []
        prefix = f"Front{side}"

        upper = f"{prefix}UpperArm" if self._has_bone(f"{prefix}UpperArm") else f"{prefix}Shoulder"
        if self._has_bone(upper):
            rotations = []
            for t in times:
                phase = ((t / duration) + phase_offset) * 2 * math.pi
                x_rot = math.sin(phase) * 0.6 * params.intensity
                rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
            tracks.append(self._create_rotation_track(upper, times, rotations))

        lower = f"{prefix}LowerArm" if self._has_bone(f"{prefix}LowerArm") else f"{prefix}Arm"
        if self._has_bone(lower):
            rotations = []
            for t in times:
                phase = ((t / duration) + phase_offset) * 2 * math.pi
                swing = max(0, math.sin(phase))
                x_rot = swing * 0.7 * params.intensity
                rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
            tracks.append(self._create_rotation_track(lower, times, rotations))

        return tracks

    def _generate_back_gallop(self, times, duration, params, side, phase_offset):
        tracks = []
        prefix = f"Back{side}"

        upper = f"{prefix}UpperLeg" if self._has_bone(f"{prefix}UpperLeg") else f"{prefix}Hip"
        if self._has_bone(upper):
            rotations = []
            for t in times:
                phase = ((t / duration) + phase_offset) * 2 * math.pi
                x_rot = math.sin(phase) * 0.55 * params.intensity
                rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
            tracks.append(self._create_rotation_track(upper, times, rotations))

        lower = f"{prefix}LowerLeg" if self._has_bone(f"{prefix}LowerLeg") else f"{prefix}Leg"
        if self._has_bone(lower):
            rotations = []
            for t in times:
                phase = ((t / duration) + phase_offset) * 2 * math.pi
                swing = max(0, math.sin(phase))
                x_rot = swing * 0.65 * params.intensity
                rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
            tracks.append(self._create_rotation_track(lower, times, rotations))

        return tracks

    def _generate_neck_stabilize(self, times, duration, params):
        rotations = []
        for t in times:
            phase = (t / duration) * 2 * math.pi
            x_rot = -math.sin(phase) * 0.06 * params.intensity
            rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
        return self._create_rotation_track("Neck", times, rotations)


class QuadrupedSitGenerator(BaseAnimationGenerator):
    """Generates sit animation for quadruped characters."""

    def generate(
        self,
        duration: float = 1.0,
        params: Optional[AnimationParameters] = None,
    ) -> AnimationData:
        """Generate transition to sitting position."""
        params = params or AnimationParameters()
        times = self._create_times(duration, params)
        adjusted_duration = duration / params.speed

        tracks: list[KeyframeTrack] = []

        # Lower hindquarters
        if self._has_bone("Hips"):
            tracks.append(self._generate_hips_sit(times, adjusted_duration, params))

        # Back legs fold
        for side in ["Left", "Right"]:
            tracks.extend(self._generate_back_leg_sit(times, adjusted_duration, params, side))

        # Front legs stay straight, slight adjust
        for side in ["Left", "Right"]:
            tracks.extend(self._generate_front_leg_sit(times, adjusted_duration, params, side))

        # Spine curves
        if self._has_bone("Spine"):
            tracks.append(self._generate_spine_sit(times, adjusted_duration, params))

        # Head looks up
        if self._has_bone("Head"):
            tracks.append(self._generate_head_sit(times, adjusted_duration, params))

        # Tail rests
        for i in range(1, 4):
            tail = f"Tail{i}" if i > 1 else "Tail"
            if self._has_bone(tail):
                tracks.append(self._generate_tail_sit(tail, times, adjusted_duration, params, i))

        return AnimationData(
            name="Sit",
            duration=adjusted_duration,
            frame_rate=self.fps,
            tracks=tracks,
        )

    def _ease_in_out(self, t):
        return t * t * (3 - 2 * t)

    def _generate_hips_sit(self, times, duration, params):
        positions = []
        rotations = []
        for t in times:
            progress = self._ease_in_out(t / duration)
            # Lower and tilt back
            y = -progress * 0.15 * params.intensity
            positions.append([0, y, 0])
            x_rot = -progress * 0.4 * params.intensity
            rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
        # Return position track (rotation handled separately if needed)
        return self._create_position_track("Hips", times, positions)

    def _generate_back_leg_sit(self, times, duration, params, side):
        tracks = []
        prefix = f"Back{side}"
        progress_fn = lambda t: self._ease_in_out(t / duration)

        upper = f"{prefix}UpperLeg" if self._has_bone(f"{prefix}UpperLeg") else f"{prefix}Hip"
        if self._has_bone(upper):
            rotations = []
            for t in times:
                p = progress_fn(t)
                x_rot = p * 1.2 * params.intensity  # Fold up
                rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
            tracks.append(self._create_rotation_track(upper, times, rotations))

        lower = f"{prefix}LowerLeg" if self._has_bone(f"{prefix}LowerLeg") else f"{prefix}Leg"
        if self._has_bone(lower):
            rotations = []
            for t in times:
                p = progress_fn(t)
                x_rot = p * 1.5 * params.intensity  # Tight fold
                rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
            tracks.append(self._create_rotation_track(lower, times, rotations))

        return tracks

    def _generate_front_leg_sit(self, times, duration, params, side):
        tracks = []
        prefix = f"Front{side}"
        progress_fn = lambda t: self._ease_in_out(t / duration)

        upper = f"{prefix}UpperArm" if self._has_bone(f"{prefix}UpperArm") else f"{prefix}Shoulder"
        if self._has_bone(upper):
            rotations = []
            for t in times:
                p = progress_fn(t)
                x_rot = p * 0.1 * params.intensity  # Slight forward
                rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
            tracks.append(self._create_rotation_track(upper, times, rotations))

        return tracks

    def _generate_spine_sit(self, times, duration, params):
        rotations = []
        for t in times:
            p = self._ease_in_out(t / duration)
            x_rot = p * 0.2 * params.intensity  # Curve up
            rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
        return self._create_rotation_track("Spine", times, rotations)

    def _generate_head_sit(self, times, duration, params):
        rotations = []
        for t in times:
            p = self._ease_in_out(t / duration)
            x_rot = -p * 0.15 * params.intensity  # Look up
            rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
        return self._create_rotation_track("Head", times, rotations)

    def _generate_tail_sit(self, bone_name, times, duration, params, segment):
        rotations = []
        for t in times:
            p = self._ease_in_out(t / duration)
            # Tail curves down/around
            x_rot = p * 0.2 * segment * params.intensity
            rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
        return self._create_rotation_track(bone_name, times, rotations)


class QuadrupedLieDownGenerator(BaseAnimationGenerator):
    """Generates lie down animation for quadruped characters."""

    def generate(
        self,
        duration: float = 1.5,
        params: Optional[AnimationParameters] = None,
    ) -> AnimationData:
        """Generate transition to lying down position."""
        params = params or AnimationParameters()
        times = self._create_times(duration, params)
        adjusted_duration = duration / params.speed

        tracks: list[KeyframeTrack] = []

        # Lower entire body
        if self._has_bone("Hips"):
            tracks.append(self._generate_hips_down(times, adjusted_duration, params))

        # All legs fold
        for side in ["Left", "Right"]:
            tracks.extend(self._generate_front_fold(times, adjusted_duration, params, side))
            tracks.extend(self._generate_back_fold(times, adjusted_duration, params, side))

        # Head rests
        if self._has_bone("Head"):
            tracks.append(self._generate_head_rest(times, adjusted_duration, params))
        if self._has_bone("Neck"):
            tracks.append(self._generate_neck_rest(times, adjusted_duration, params))

        return AnimationData(
            name="LieDown",
            duration=adjusted_duration,
            frame_rate=self.fps,
            tracks=tracks,
        )

    def _ease_in_out(self, t):
        return t * t * (3 - 2 * t)

    def _generate_hips_down(self, times, duration, params):
        positions = []
        for t in times:
            p = self._ease_in_out(t / duration)
            y = -p * 0.25 * params.intensity
            positions.append([0, y, 0])
        return self._create_position_track("Hips", times, positions)

    def _generate_front_fold(self, times, duration, params, side):
        tracks = []
        prefix = f"Front{side}"
        progress_fn = lambda t: self._ease_in_out(t / duration)

        upper = f"{prefix}UpperArm" if self._has_bone(f"{prefix}UpperArm") else f"{prefix}Shoulder"
        if self._has_bone(upper):
            rotations = []
            for t in times:
                p = progress_fn(t)
                x_rot = p * 0.8 * params.intensity
                rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
            tracks.append(self._create_rotation_track(upper, times, rotations))

        lower = f"{prefix}LowerArm" if self._has_bone(f"{prefix}LowerArm") else f"{prefix}Arm"
        if self._has_bone(lower):
            rotations = []
            for t in times:
                p = progress_fn(t)
                x_rot = p * 1.2 * params.intensity
                rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
            tracks.append(self._create_rotation_track(lower, times, rotations))

        return tracks

    def _generate_back_fold(self, times, duration, params, side):
        tracks = []
        prefix = f"Back{side}"
        progress_fn = lambda t: self._ease_in_out(t / duration)

        upper = f"{prefix}UpperLeg" if self._has_bone(f"{prefix}UpperLeg") else f"{prefix}Hip"
        if self._has_bone(upper):
            rotations = []
            for t in times:
                p = progress_fn(t)
                x_rot = p * 1.0 * params.intensity
                z_rot = (0.2 if side == "Left" else -0.2) * p * params.intensity
                rotations.append(self._euler_to_quaternion(x_rot, 0, z_rot))
            tracks.append(self._create_rotation_track(upper, times, rotations))

        lower = f"{prefix}LowerLeg" if self._has_bone(f"{prefix}LowerLeg") else f"{prefix}Leg"
        if self._has_bone(lower):
            rotations = []
            for t in times:
                p = progress_fn(t)
                x_rot = p * 1.4 * params.intensity
                rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
            tracks.append(self._create_rotation_track(lower, times, rotations))

        return tracks

    def _generate_head_rest(self, times, duration, params):
        rotations = []
        for t in times:
            p = self._ease_in_out(t / duration)
            x_rot = p * 0.3 * params.intensity
            rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
        return self._create_rotation_track("Head", times, rotations)

    def _generate_neck_rest(self, times, duration, params):
        rotations = []
        for t in times:
            p = self._ease_in_out(t / duration)
            x_rot = p * 0.4 * params.intensity
            rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
        return self._create_rotation_track("Neck", times, rotations)


class QuadrupedJumpGenerator(BaseAnimationGenerator):
    """Generates jump animation for quadruped characters."""

    def generate(
        self,
        duration: float = 0.8,
        params: Optional[AnimationParameters] = None,
    ) -> AnimationData:
        """Generate jump animation with crouch, leap, and land phases."""
        params = params or AnimationParameters()
        times = self._create_times(duration, params)
        adjusted_duration = duration / params.speed

        tracks: list[KeyframeTrack] = []

        # Body trajectory
        if self._has_bone("Hips"):
            tracks.append(self._generate_jump_arc(times, adjusted_duration, params))

        # Legs extend then tuck
        for side in ["Left", "Right"]:
            tracks.extend(self._generate_front_jump(times, adjusted_duration, params, side))
            tracks.extend(self._generate_back_jump(times, adjusted_duration, params, side))

        # Spine arches
        if self._has_bone("Spine"):
            tracks.append(self._generate_spine_jump(times, adjusted_duration, params))

        return AnimationData(
            name="Jump",
            duration=adjusted_duration,
            frame_rate=self.fps,
            tracks=tracks,
        )

    def _get_jump_phase(self, t, duration):
        progress = t / duration
        if progress < 0.2:
            return "crouch", progress / 0.2
        elif progress < 0.5:
            return "leap", (progress - 0.2) / 0.3
        elif progress < 0.8:
            return "air", (progress - 0.5) / 0.3
        else:
            return "land", (progress - 0.8) / 0.2

    def _generate_jump_arc(self, times, duration, params):
        positions = []
        for t in times:
            phase, p = self._get_jump_phase(t, duration)
            if phase == "crouch":
                y = -p * 0.08 * params.intensity
            elif phase == "leap":
                y = -0.08 + p * 0.25 * params.intensity
            elif phase == "air":
                y = 0.17 - p * 0.1 * params.intensity
            else:
                y = 0.07 * (1 - p) * params.intensity
            positions.append([0, y * params.intensity, 0])
        return self._create_position_track("Hips", times, positions)

    def _generate_front_jump(self, times, duration, params, side):
        tracks = []
        prefix = f"Front{side}"

        upper = f"{prefix}UpperArm" if self._has_bone(f"{prefix}UpperArm") else f"{prefix}Shoulder"
        if self._has_bone(upper):
            rotations = []
            for t in times:
                phase, p = self._get_jump_phase(t, duration)
                if phase == "crouch":
                    x_rot = p * 0.4 * params.intensity
                elif phase == "leap":
                    x_rot = 0.4 - p * 0.8 * params.intensity
                elif phase == "air":
                    x_rot = -0.4 + p * 0.3 * params.intensity
                else:
                    x_rot = -0.1 * (1 - p) * params.intensity
                rotations.append(self._euler_to_quaternion(x_rot * params.intensity, 0, 0))
            tracks.append(self._create_rotation_track(upper, times, rotations))

        return tracks

    def _generate_back_jump(self, times, duration, params, side):
        tracks = []
        prefix = f"Back{side}"

        upper = f"{prefix}UpperLeg" if self._has_bone(f"{prefix}UpperLeg") else f"{prefix}Hip"
        if self._has_bone(upper):
            rotations = []
            for t in times:
                phase, p = self._get_jump_phase(t, duration)
                if phase == "crouch":
                    x_rot = p * 0.6 * params.intensity
                elif phase == "leap":
                    x_rot = 0.6 - p * 1.0 * params.intensity
                elif phase == "air":
                    x_rot = -0.4 * params.intensity
                else:
                    x_rot = -0.4 + p * 0.4 * params.intensity
                rotations.append(self._euler_to_quaternion(x_rot * params.intensity, 0, 0))
            tracks.append(self._create_rotation_track(upper, times, rotations))

        return tracks

    def _generate_spine_jump(self, times, duration, params):
        rotations = []
        for t in times:
            phase, p = self._get_jump_phase(t, duration)
            if phase == "crouch":
                x_rot = p * 0.15 * params.intensity
            elif phase == "leap":
                x_rot = 0.15 - p * 0.3 * params.intensity
            elif phase == "air":
                x_rot = -0.15 * params.intensity
            else:
                x_rot = -0.15 * (1 - p) * params.intensity
            rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
        return self._create_rotation_track("Spine", times, rotations)


class ShakeGenerator(BaseAnimationGenerator):
    """Generates shake animation for quadrupeds (shaking off water/dirt)."""

    def generate(
        self,
        duration: float = 1.2,
        params: Optional[AnimationParameters] = None,
    ) -> AnimationData:
        """Generate full body shake animation."""
        params = params or AnimationParameters()
        times = self._create_times(duration, params)
        adjusted_duration = duration / params.speed

        tracks: list[KeyframeTrack] = []

        # Rapid body rotation
        if self._has_bone("Hips"):
            tracks.append(self._generate_body_shake(times, adjusted_duration, params))

        if self._has_bone("Spine"):
            tracks.append(self._generate_spine_shake(times, adjusted_duration, params))

        # Head whips side to side
        if self._has_bone("Head"):
            tracks.append(self._generate_head_shake(times, adjusted_duration, params))
        if self._has_bone("Neck"):
            tracks.append(self._generate_neck_shake(times, adjusted_duration, params))

        # Ears flop
        for side in ["Left", "Right"]:
            ear = f"{side}Ear"
            if self._has_bone(ear):
                tracks.append(self._generate_ear_flop(ear, times, adjusted_duration, params, side))

        # Tail whips
        for i in range(1, 5):
            tail = f"Tail{i}" if i > 1 else "Tail"
            if self._has_bone(tail):
                tracks.append(self._generate_tail_shake(tail, times, adjusted_duration, params, i))

        return AnimationData(
            name="Shake",
            duration=adjusted_duration,
            frame_rate=self.fps,
            tracks=tracks,
        )

    def _generate_body_shake(self, times, duration, params):
        rotations = []
        freq = 12  # Fast shake frequency
        for t in times:
            # Amplitude envelope - ramps up then down
            envelope = math.sin(math.pi * t / duration)
            z_rot = math.sin(t * freq * 2 * math.pi / duration) * 0.15 * envelope * params.intensity
            rotations.append(self._euler_to_quaternion(0, 0, z_rot))
        return self._create_rotation_track("Hips", times, rotations)

    def _generate_spine_shake(self, times, duration, params):
        rotations = []
        freq = 12
        for t in times:
            envelope = math.sin(math.pi * t / duration)
            # Spine rotates opposite for whip effect
            z_rot = math.sin(t * freq * 2 * math.pi / duration + 0.5) * 0.2 * envelope * params.intensity
            rotations.append(self._euler_to_quaternion(0, 0, z_rot))
        return self._create_rotation_track("Spine", times, rotations)

    def _generate_head_shake(self, times, duration, params):
        rotations = []
        freq = 14  # Head shakes faster
        for t in times:
            envelope = math.sin(math.pi * t / duration)
            y_rot = math.sin(t * freq * 2 * math.pi / duration) * 0.3 * envelope * params.intensity
            rotations.append(self._euler_to_quaternion(0, y_rot, 0))
        return self._create_rotation_track("Head", times, rotations)

    def _generate_neck_shake(self, times, duration, params):
        rotations = []
        freq = 13
        for t in times:
            envelope = math.sin(math.pi * t / duration)
            y_rot = math.sin(t * freq * 2 * math.pi / duration + 0.3) * 0.2 * envelope * params.intensity
            rotations.append(self._euler_to_quaternion(0, y_rot, 0))
        return self._create_rotation_track("Neck", times, rotations)

    def _generate_ear_flop(self, bone_name, times, duration, params, side):
        rotations = []
        freq = 16
        for t in times:
            envelope = math.sin(math.pi * t / duration)
            z_rot = math.sin(t * freq * 2 * math.pi / duration) * 0.4 * envelope * params.intensity
            if side == "Right":
                z_rot = -z_rot
            rotations.append(self._euler_to_quaternion(0, 0, z_rot))
        return self._create_rotation_track(bone_name, times, rotations)

    def _generate_tail_shake(self, bone_name, times, duration, params, segment):
        rotations = []
        freq = 10 + segment
        delay = segment * 0.1
        for t in times:
            envelope = math.sin(math.pi * max(0, t - delay) / duration)
            y_rot = math.sin((t - delay) * freq * 2 * math.pi / duration) * 0.25 * envelope * params.intensity
            rotations.append(self._euler_to_quaternion(0, y_rot, 0))
        return self._create_rotation_track(bone_name, times, rotations)


class PounceGenerator(BaseAnimationGenerator):
    """Generates pounce animation for quadrupeds."""

    def generate(
        self,
        duration: float = 0.7,
        params: Optional[AnimationParameters] = None,
    ) -> AnimationData:
        """Generate pounce attack - crouch, spring, land."""
        params = params or AnimationParameters()
        times = self._create_times(duration, params)
        adjusted_duration = duration / params.speed

        tracks: list[KeyframeTrack] = []

        # Body launches forward
        if self._has_bone("Hips"):
            tracks.append(self._generate_pounce_arc(times, adjusted_duration, params))

        # Front legs reach out
        for side in ["Left", "Right"]:
            tracks.extend(self._generate_front_pounce(times, adjusted_duration, params, side))

        # Back legs push off
        for side in ["Left", "Right"]:
            tracks.extend(self._generate_back_pounce(times, adjusted_duration, params, side))

        # Spine extends
        if self._has_bone("Spine"):
            tracks.append(self._generate_spine_pounce(times, adjusted_duration, params))

        # Head targets
        if self._has_bone("Head"):
            tracks.append(self._generate_head_pounce(times, adjusted_duration, params))

        return AnimationData(
            name="Pounce",
            duration=adjusted_duration,
            frame_rate=self.fps,
            tracks=tracks,
        )

    def _get_pounce_phase(self, t, duration):
        progress = t / duration
        if progress < 0.3:
            return "crouch", progress / 0.3
        elif progress < 0.6:
            return "spring", (progress - 0.3) / 0.3
        else:
            return "land", (progress - 0.6) / 0.4

    def _generate_pounce_arc(self, times, duration, params):
        positions = []
        for t in times:
            phase, p = self._get_pounce_phase(t, duration)
            if phase == "crouch":
                y = -p * 0.1 * params.intensity
                z = -p * 0.05 * params.intensity
            elif phase == "spring":
                y = -0.1 + p * 0.2 * params.intensity
                z = -0.05 + p * 0.2 * params.intensity
            else:
                y = 0.1 * (1 - p) * params.intensity
                z = 0.15 * params.intensity
            positions.append([0, y, z])
        return self._create_position_track("Hips", times, positions)

    def _generate_front_pounce(self, times, duration, params, side):
        tracks = []
        prefix = f"Front{side}"

        upper = f"{prefix}UpperArm" if self._has_bone(f"{prefix}UpperArm") else f"{prefix}Shoulder"
        if self._has_bone(upper):
            rotations = []
            for t in times:
                phase, p = self._get_pounce_phase(t, duration)
                if phase == "crouch":
                    x_rot = p * 0.3 * params.intensity
                elif phase == "spring":
                    x_rot = 0.3 - p * 0.9 * params.intensity  # Reach forward
                else:
                    x_rot = -0.6 + p * 0.6 * params.intensity
                rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
            tracks.append(self._create_rotation_track(upper, times, rotations))

        return tracks

    def _generate_back_pounce(self, times, duration, params, side):
        tracks = []
        prefix = f"Back{side}"

        upper = f"{prefix}UpperLeg" if self._has_bone(f"{prefix}UpperLeg") else f"{prefix}Hip"
        if self._has_bone(upper):
            rotations = []
            for t in times:
                phase, p = self._get_pounce_phase(t, duration)
                if phase == "crouch":
                    x_rot = p * 0.5 * params.intensity
                elif phase == "spring":
                    x_rot = 0.5 - p * 1.0 * params.intensity  # Extend back
                else:
                    x_rot = -0.5 + p * 0.5 * params.intensity
                rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
            tracks.append(self._create_rotation_track(upper, times, rotations))

        return tracks

    def _generate_spine_pounce(self, times, duration, params):
        rotations = []
        for t in times:
            phase, p = self._get_pounce_phase(t, duration)
            if phase == "crouch":
                x_rot = p * 0.2 * params.intensity
            elif phase == "spring":
                x_rot = 0.2 - p * 0.4 * params.intensity
            else:
                x_rot = -0.2 * (1 - p) * params.intensity
            rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
        return self._create_rotation_track("Spine", times, rotations)

    def _generate_head_pounce(self, times, duration, params):
        rotations = []
        for t in times:
            phase, p = self._get_pounce_phase(t, duration)
            if phase == "spring":
                x_rot = p * 0.2 * params.intensity  # Look at target
            else:
                x_rot = 0.2 * (1 - p) * params.intensity if phase == "land" else 0
            rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
        return self._create_rotation_track("Head", times, rotations)


class HowlGenerator(BaseAnimationGenerator):
    """Generates howl/bark animation for quadrupeds."""

    def generate(
        self,
        duration: float = 2.0,
        params: Optional[AnimationParameters] = None,
    ) -> AnimationData:
        """Generate howling animation - head up, mouth open."""
        params = params or AnimationParameters()
        times = self._create_times(duration, params)
        adjusted_duration = duration / params.speed

        tracks: list[KeyframeTrack] = []

        # Head tilts up
        if self._has_bone("Head"):
            tracks.append(self._generate_head_howl(times, adjusted_duration, params))
        if self._has_bone("Neck"):
            tracks.append(self._generate_neck_howl(times, adjusted_duration, params))

        # Jaw opens
        if self._has_bone("Jaw"):
            tracks.append(self._generate_jaw_howl(times, adjusted_duration, params))

        # Body sways slightly
        if self._has_bone("Spine"):
            tracks.append(self._generate_spine_howl(times, adjusted_duration, params))

        # Tail position
        for i in range(1, 4):
            tail = f"Tail{i}" if i > 1 else "Tail"
            if self._has_bone(tail):
                tracks.append(self._generate_tail_howl(tail, times, adjusted_duration, params, i))

        return AnimationData(
            name="Howl",
            duration=adjusted_duration,
            frame_rate=self.fps,
            tracks=tracks,
        )

    def _ease_in_out(self, t):
        return t * t * (3 - 2 * t)

    def _generate_head_howl(self, times, duration, params):
        rotations = []
        for t in times:
            progress = t / duration
            if progress < 0.2:
                # Raise head
                p = self._ease_in_out(progress / 0.2)
                x_rot = -p * 0.5 * params.intensity
            elif progress < 0.8:
                # Hold and slight vibration
                x_rot = -0.5 * params.intensity + math.sin(t * 20) * 0.02 * params.intensity
            else:
                # Lower head
                p = self._ease_in_out((progress - 0.8) / 0.2)
                x_rot = -0.5 * (1 - p) * params.intensity
            rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
        return self._create_rotation_track("Head", times, rotations)

    def _generate_neck_howl(self, times, duration, params):
        rotations = []
        for t in times:
            progress = t / duration
            if progress < 0.2:
                p = self._ease_in_out(progress / 0.2)
                x_rot = -p * 0.3 * params.intensity
            elif progress < 0.8:
                x_rot = -0.3 * params.intensity
            else:
                p = self._ease_in_out((progress - 0.8) / 0.2)
                x_rot = -0.3 * (1 - p) * params.intensity
            rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
        return self._create_rotation_track("Neck", times, rotations)

    def _generate_jaw_howl(self, times, duration, params):
        rotations = []
        for t in times:
            progress = t / duration
            if progress < 0.15:
                p = progress / 0.15
                x_rot = p * 0.4 * params.intensity
            elif progress < 0.85:
                # Jaw moves with howl
                x_rot = 0.4 * params.intensity + math.sin(t * 8) * 0.1 * params.intensity
            else:
                p = (progress - 0.85) / 0.15
                x_rot = 0.4 * (1 - p) * params.intensity
            rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
        return self._create_rotation_track("Jaw", times, rotations)

    def _generate_spine_howl(self, times, duration, params):
        rotations = []
        for t in times:
            progress = t / duration
            if 0.2 < progress < 0.8:
                # Slight sway during howl
                x_rot = math.sin(t * 3) * 0.03 * params.intensity
            else:
                x_rot = 0
            rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
        return self._create_rotation_track("Spine", times, rotations)

    def _generate_tail_howl(self, bone_name, times, duration, params, segment):
        rotations = []
        for t in times:
            progress = t / duration
            if 0.2 < progress < 0.8:
                # Tail hangs down relaxed with slight movement
                x_rot = 0.1 * segment * params.intensity
                y_rot = math.sin(t * 2) * 0.05 * params.intensity
            else:
                x_rot = 0
                y_rot = 0
            rotations.append(self._euler_to_quaternion(x_rot, y_rot, 0))
        return self._create_rotation_track(bone_name, times, rotations)


class RollOverGenerator(BaseAnimationGenerator):
    """Generates roll over animation for quadrupeds."""

    def generate(
        self,
        duration: float = 2.0,
        params: Optional[AnimationParameters] = None,
    ) -> AnimationData:
        """Generate roll onto back animation."""
        params = params or AnimationParameters()
        times = self._create_times(duration, params)
        adjusted_duration = duration / params.speed

        tracks: list[KeyframeTrack] = []

        # Body rolls over
        if self._has_bone("Hips"):
            tracks.append(self._generate_body_roll(times, adjusted_duration, params))

        if self._has_bone("Spine"):
            tracks.append(self._generate_spine_roll(times, adjusted_duration, params))

        # Legs go up in air
        for side in ["Left", "Right"]:
            tracks.extend(self._generate_front_roll(times, adjusted_duration, params, side))
            tracks.extend(self._generate_back_roll(times, adjusted_duration, params, side))

        # Head follows
        if self._has_bone("Head"):
            tracks.append(self._generate_head_roll(times, adjusted_duration, params))

        return AnimationData(
            name="RollOver",
            duration=adjusted_duration,
            frame_rate=self.fps,
            tracks=tracks,
        )

    def _ease_in_out(self, t):
        return t * t * (3 - 2 * t)

    def _generate_body_roll(self, times, duration, params):
        rotations = []
        positions = []
        for t in times:
            progress = t / duration
            if progress < 0.4:
                # Roll onto side then back
                p = self._ease_in_out(progress / 0.4)
                z_rot = p * math.pi * params.intensity
                y = -p * 0.15 * params.intensity
            else:
                # Hold on back with wiggle
                z_rot = math.pi * params.intensity + math.sin(t * 4) * 0.1 * params.intensity
                y = -0.15 * params.intensity
            rotations.append(self._euler_to_quaternion(0, 0, z_rot))
            positions.append([0, y, 0])
        return self._create_rotation_track("Hips", times, rotations)

    def _generate_spine_roll(self, times, duration, params):
        rotations = []
        for t in times:
            progress = t / duration
            if progress > 0.4:
                # Slight wiggle on back
                x_rot = math.sin(t * 5) * 0.1 * params.intensity
            else:
                x_rot = 0
            rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
        return self._create_rotation_track("Spine", times, rotations)

    def _generate_front_roll(self, times, duration, params, side):
        tracks = []
        prefix = f"Front{side}"

        upper = f"{prefix}UpperArm" if self._has_bone(f"{prefix}UpperArm") else f"{prefix}Shoulder"
        if self._has_bone(upper):
            rotations = []
            for t in times:
                progress = t / duration
                if progress < 0.4:
                    p = self._ease_in_out(progress / 0.4)
                    x_rot = -p * 0.5 * params.intensity
                else:
                    # Paw in air, wiggling
                    x_rot = -0.5 * params.intensity + math.sin(t * 6) * 0.15 * params.intensity
                rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
            tracks.append(self._create_rotation_track(upper, times, rotations))

        return tracks

    def _generate_back_roll(self, times, duration, params, side):
        tracks = []
        prefix = f"Back{side}"

        upper = f"{prefix}UpperLeg" if self._has_bone(f"{prefix}UpperLeg") else f"{prefix}Hip"
        if self._has_bone(upper):
            rotations = []
            for t in times:
                progress = t / duration
                if progress < 0.4:
                    p = self._ease_in_out(progress / 0.4)
                    x_rot = -p * 0.6 * params.intensity
                else:
                    x_rot = -0.6 * params.intensity + math.sin(t * 5 + 0.5) * 0.2 * params.intensity
                rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
            tracks.append(self._create_rotation_track(upper, times, rotations))

        return tracks

    def _generate_head_roll(self, times, duration, params):
        rotations = []
        for t in times:
            progress = t / duration
            if progress < 0.4:
                p = self._ease_in_out(progress / 0.4)
                z_rot = p * 0.3 * params.intensity
            else:
                z_rot = 0.3 * params.intensity + math.sin(t * 3) * 0.1 * params.intensity
            rotations.append(self._euler_to_quaternion(0, 0, z_rot))
        return self._create_rotation_track("Head", times, rotations)


class PlayDeadGenerator(BaseAnimationGenerator):
    """Generates play dead/die animation for quadrupeds."""

    def generate(
        self,
        duration: float = 1.5,
        params: Optional[AnimationParameters] = None,
    ) -> AnimationData:
        """Generate collapse and lie still animation."""
        params = params or AnimationParameters()
        times = self._create_times(duration, params)
        adjusted_duration = duration / params.speed

        tracks: list[KeyframeTrack] = []

        # Body collapses to side
        if self._has_bone("Hips"):
            tracks.append(self._generate_body_collapse(times, adjusted_duration, params))

        if self._has_bone("Spine"):
            tracks.append(self._generate_spine_collapse(times, adjusted_duration, params))

        # Legs go limp
        for side in ["Left", "Right"]:
            tracks.extend(self._generate_front_collapse(times, adjusted_duration, params, side))
            tracks.extend(self._generate_back_collapse(times, adjusted_duration, params, side))

        # Head drops
        if self._has_bone("Head"):
            tracks.append(self._generate_head_collapse(times, adjusted_duration, params))
        if self._has_bone("Neck"):
            tracks.append(self._generate_neck_collapse(times, adjusted_duration, params))

        # Tail limp
        for i in range(1, 4):
            tail = f"Tail{i}" if i > 1 else "Tail"
            if self._has_bone(tail):
                tracks.append(self._generate_tail_collapse(tail, times, adjusted_duration, params, i))

        return AnimationData(
            name="PlayDead",
            duration=adjusted_duration,
            frame_rate=self.fps,
            tracks=tracks,
        )

    def _ease_out(self, t):
        return 1 - (1 - t) * (1 - t)

    def _generate_body_collapse(self, times, duration, params):
        positions = []
        rotations = []
        for t in times:
            progress = t / duration
            if progress < 0.6:
                # Collapse phase
                p = self._ease_out(progress / 0.6)
                y = -p * 0.2 * params.intensity
                z_rot = p * 1.2 * params.intensity  # Roll to side
            else:
                # Lie still
                y = -0.2 * params.intensity
                z_rot = 1.2 * params.intensity
            positions.append([0, y, 0])
            rotations.append(self._euler_to_quaternion(0, 0, z_rot))
        return self._create_position_track("Hips", times, positions)

    def _generate_spine_collapse(self, times, duration, params):
        rotations = []
        for t in times:
            progress = t / duration
            if progress < 0.6:
                p = self._ease_out(progress / 0.6)
                x_rot = p * 0.2 * params.intensity
            else:
                x_rot = 0.2 * params.intensity
            rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
        return self._create_rotation_track("Spine", times, rotations)

    def _generate_front_collapse(self, times, duration, params, side):
        tracks = []
        prefix = f"Front{side}"

        upper = f"{prefix}UpperArm" if self._has_bone(f"{prefix}UpperArm") else f"{prefix}Shoulder"
        if self._has_bone(upper):
            rotations = []
            for t in times:
                progress = t / duration
                if progress < 0.6:
                    p = self._ease_out(progress / 0.6)
                    x_rot = p * 0.4 * params.intensity
                    z_rot = (0.3 if side == "Left" else -0.1) * p * params.intensity
                else:
                    x_rot = 0.4 * params.intensity
                    z_rot = (0.3 if side == "Left" else -0.1) * params.intensity
                rotations.append(self._euler_to_quaternion(x_rot, 0, z_rot))
            tracks.append(self._create_rotation_track(upper, times, rotations))

        return tracks

    def _generate_back_collapse(self, times, duration, params, side):
        tracks = []
        prefix = f"Back{side}"

        upper = f"{prefix}UpperLeg" if self._has_bone(f"{prefix}UpperLeg") else f"{prefix}Hip"
        if self._has_bone(upper):
            rotations = []
            for t in times:
                progress = t / duration
                if progress < 0.6:
                    p = self._ease_out(progress / 0.6)
                    x_rot = p * 0.5 * params.intensity
                    z_rot = (0.4 if side == "Left" else -0.2) * p * params.intensity
                else:
                    x_rot = 0.5 * params.intensity
                    z_rot = (0.4 if side == "Left" else -0.2) * params.intensity
                rotations.append(self._euler_to_quaternion(x_rot, 0, z_rot))
            tracks.append(self._create_rotation_track(upper, times, rotations))

        return tracks

    def _generate_head_collapse(self, times, duration, params):
        rotations = []
        for t in times:
            progress = t / duration
            if progress < 0.7:
                p = self._ease_out(progress / 0.7)
                x_rot = p * 0.4 * params.intensity
                z_rot = p * 0.3 * params.intensity
            else:
                x_rot = 0.4 * params.intensity
                z_rot = 0.3 * params.intensity
            rotations.append(self._euler_to_quaternion(x_rot, 0, z_rot))
        return self._create_rotation_track("Head", times, rotations)

    def _generate_neck_collapse(self, times, duration, params):
        rotations = []
        for t in times:
            progress = t / duration
            if progress < 0.6:
                p = self._ease_out(progress / 0.6)
                x_rot = p * 0.3 * params.intensity
            else:
                x_rot = 0.3 * params.intensity
            rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
        return self._create_rotation_track("Neck", times, rotations)

    def _generate_tail_collapse(self, bone_name, times, duration, params, segment):
        rotations = []
        for t in times:
            progress = t / duration
            delay = segment * 0.1
            effective_progress = max(0, progress - delay)
            if effective_progress < 0.5:
                p = self._ease_out(effective_progress / 0.5)
                x_rot = p * 0.15 * segment * params.intensity
            else:
                x_rot = 0.15 * segment * params.intensity
            rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
        return self._create_rotation_track(bone_name, times, rotations)
