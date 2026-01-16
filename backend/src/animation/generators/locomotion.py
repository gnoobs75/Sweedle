"""
Locomotion animation generators (walk, run) for humanoids.
"""

import math
from typing import Optional

from .base import BaseAnimationGenerator
from ..schemas import AnimationParameters, AnimationData, KeyframeTrack


class WalkGenerator(BaseAnimationGenerator):
    """Generates walk cycle animation for humanoid characters."""

    def generate(
        self,
        duration: float = 1.0,
        params: Optional[AnimationParameters] = None,
    ) -> AnimationData:
        """
        Generate walk cycle animation.

        Args:
            duration: Duration of one complete walk cycle
            params: Animation parameters

        Returns:
            AnimationData with walk cycle keyframes
        """
        params = params or AnimationParameters()
        adjusted_duration = duration / params.speed
        times = self._create_times(duration, params)

        tracks: list[KeyframeTrack] = []

        # Hips up/down movement
        if self._has_bone("Hips"):
            tracks.append(self._generate_hips_bounce(times, adjusted_duration, params))
            tracks.append(self._generate_hips_sway(times, adjusted_duration, params))

        # Leg animations
        for side in ["Left", "Right"]:
            phase_offset = 0.0 if side == "Left" else 0.5
            tracks.extend(self._generate_leg_tracks(times, adjusted_duration, params, side, phase_offset))

        # Arm swing (opposite to legs)
        for side in ["Left", "Right"]:
            phase_offset = 0.5 if side == "Left" else 0.0
            track = self._generate_arm_swing(times, adjusted_duration, params, side, phase_offset)
            if track:
                tracks.append(track)

        # Spine twist
        if self._has_bone("Spine1"):
            tracks.append(self._generate_spine_twist(times, adjusted_duration, params))

        return AnimationData(
            name="Walk",
            duration=adjusted_duration,
            frame_rate=self.fps,
            tracks=tracks,
        )

    def _generate_hips_bounce(
        self,
        times: list[float],
        duration: float,
        params: AnimationParameters,
    ) -> KeyframeTrack:
        """Generate vertical hip movement (double frequency for two steps)."""
        positions = []

        for t in times:
            # Two bounces per cycle (one for each step)
            phase = (t / duration) * 4 * math.pi
            y = math.sin(phase) * 0.015 * params.intensity
            positions.append([0, y, 0])

        return self._create_position_track("Hips", times, positions)

    def _generate_hips_sway(
        self,
        times: list[float],
        duration: float,
        params: AnimationParameters,
    ) -> KeyframeTrack:
        """Generate hip rotation (sway side to side)."""
        rotations = []

        for t in times:
            phase = (t / duration) * 2 * math.pi
            # Slight tilt toward planted foot
            z_rot = math.sin(phase) * 0.03 * params.intensity

            quat = self._euler_to_quaternion(0, 0, z_rot)
            rotations.append(quat)

        return self._create_rotation_track("Hips", times, rotations)

    def _generate_leg_tracks(
        self,
        times: list[float],
        duration: float,
        params: AnimationParameters,
        side: str,
        phase_offset: float,
    ) -> list[KeyframeTrack]:
        """Generate upper leg, lower leg, and foot tracks."""
        tracks = []

        # Upper leg (thigh) swing
        up_leg = f"{side}UpLeg"
        if self._has_bone(up_leg):
            rotations = []
            for t in times:
                phase = ((t / duration) + phase_offset) * 2 * math.pi
                # Forward/back swing
                angle = math.sin(phase) * 0.35 * params.intensity
                quat = self._euler_to_quaternion(angle, 0, 0)
                rotations.append(quat)
            tracks.append(self._create_rotation_track(up_leg, times, rotations))

        # Lower leg (knee bend)
        leg = f"{side}Leg"
        if self._has_bone(leg):
            rotations = []
            for t in times:
                phase = ((t / duration) + phase_offset) * 2 * math.pi
                # Knee bends during swing phase (only positive rotation)
                swing = max(0, math.sin(phase))
                angle = swing * 0.5 * params.intensity
                quat = self._euler_to_quaternion(angle, 0, 0)
                rotations.append(quat)
            tracks.append(self._create_rotation_track(leg, times, rotations))

        # Foot (ankle roll)
        foot = f"{side}Foot"
        if self._has_bone(foot):
            rotations = []
            for t in times:
                phase = ((t / duration) + phase_offset) * 2 * math.pi
                # Foot rolls through contact
                angle = math.sin(phase + 0.5) * 0.15 * params.intensity
                quat = self._euler_to_quaternion(angle, 0, 0)
                rotations.append(quat)
            tracks.append(self._create_rotation_track(foot, times, rotations))

        return tracks

    def _generate_arm_swing(
        self,
        times: list[float],
        duration: float,
        params: AnimationParameters,
        side: str,
        phase_offset: float,
    ) -> Optional[KeyframeTrack]:
        """Generate arm swing opposite to leg movement."""
        arm = f"{side}Arm"
        if not self._has_bone(arm):
            return None

        rotations = []
        for t in times:
            phase = ((t / duration) + phase_offset) * 2 * math.pi
            angle = math.sin(phase) * 0.25 * params.intensity
            quat = self._euler_to_quaternion(angle, 0, 0)
            rotations.append(quat)

        return self._create_rotation_track(arm, times, rotations)

    def _generate_spine_twist(
        self,
        times: list[float],
        duration: float,
        params: AnimationParameters,
    ) -> KeyframeTrack:
        """Generate spine counter-rotation."""
        rotations = []

        for t in times:
            phase = (t / duration) * 2 * math.pi
            # Counter-twist to balance arm/leg movement
            y_rot = math.sin(phase) * 0.04 * params.intensity
            quat = self._euler_to_quaternion(0, y_rot, 0)
            rotations.append(quat)

        return self._create_rotation_track("Spine1", times, rotations)


class RunGenerator(BaseAnimationGenerator):
    """Generates run cycle animation for humanoid characters."""

    def generate(
        self,
        duration: float = 0.6,
        params: Optional[AnimationParameters] = None,
    ) -> AnimationData:
        """
        Generate run cycle animation.

        Args:
            duration: Duration of one complete run cycle
            params: Animation parameters

        Returns:
            AnimationData with run cycle keyframes
        """
        params = params or AnimationParameters()
        # Increase intensity for running
        run_params = AnimationParameters(
            speed=params.speed,
            intensity=params.intensity * 1.3,
            blend_factor=params.blend_factor,
        )
        adjusted_duration = duration / params.speed
        times = self._create_times(duration, params)

        tracks: list[KeyframeTrack] = []

        # Hips - more pronounced bounce
        if self._has_bone("Hips"):
            tracks.append(self._generate_hips_bounce(times, adjusted_duration, run_params))
            tracks.append(self._generate_hips_tilt(times, adjusted_duration, run_params))

        # Legs - higher knee lift, more extension
        for side in ["Left", "Right"]:
            phase_offset = 0.0 if side == "Left" else 0.5
            tracks.extend(self._generate_leg_tracks(times, adjusted_duration, run_params, side, phase_offset))

        # Arms - more pronounced swing with elbow bend
        for side in ["Left", "Right"]:
            phase_offset = 0.5 if side == "Left" else 0.0
            tracks.extend(self._generate_arm_tracks(times, adjusted_duration, run_params, side, phase_offset))

        # Spine lean forward and twist
        if self._has_bone("Spine"):
            tracks.append(self._generate_spine_lean(times, adjusted_duration, run_params))
        if self._has_bone("Spine1"):
            tracks.append(self._generate_spine_twist(times, adjusted_duration, run_params))

        return AnimationData(
            name="Run",
            duration=adjusted_duration,
            frame_rate=self.fps,
            tracks=tracks,
        )

    def _generate_hips_bounce(
        self,
        times: list[float],
        duration: float,
        params: AnimationParameters,
    ) -> KeyframeTrack:
        """Generate vertical hip movement with flight phase."""
        positions = []

        for t in times:
            phase = (t / duration) * 4 * math.pi
            # Asymmetric bounce - higher peak (flight phase)
            y = math.sin(phase) * 0.03 * params.intensity
            # Add slight forward lean
            z = 0.01 * params.intensity
            positions.append([0, y, z])

        return self._create_position_track("Hips", times, positions)

    def _generate_hips_tilt(
        self,
        times: list[float],
        duration: float,
        params: AnimationParameters,
    ) -> KeyframeTrack:
        """Generate hip tilt during run."""
        rotations = []

        for t in times:
            phase = (t / duration) * 2 * math.pi
            z_rot = math.sin(phase) * 0.05 * params.intensity
            quat = self._euler_to_quaternion(0, 0, z_rot)
            rotations.append(quat)

        return self._create_rotation_track("Hips", times, rotations)

    def _generate_leg_tracks(
        self,
        times: list[float],
        duration: float,
        params: AnimationParameters,
        side: str,
        phase_offset: float,
    ) -> list[KeyframeTrack]:
        """Generate leg tracks for running."""
        tracks = []

        # Upper leg - higher lift
        up_leg = f"{side}UpLeg"
        if self._has_bone(up_leg):
            rotations = []
            for t in times:
                phase = ((t / duration) + phase_offset) * 2 * math.pi
                angle = math.sin(phase) * 0.55 * params.intensity
                quat = self._euler_to_quaternion(angle, 0, 0)
                rotations.append(quat)
            tracks.append(self._create_rotation_track(up_leg, times, rotations))

        # Lower leg - more bend
        leg = f"{side}Leg"
        if self._has_bone(leg):
            rotations = []
            for t in times:
                phase = ((t / duration) + phase_offset) * 2 * math.pi
                swing = max(0, math.sin(phase))
                angle = swing * 0.8 * params.intensity
                quat = self._euler_to_quaternion(angle, 0, 0)
                rotations.append(quat)
            tracks.append(self._create_rotation_track(leg, times, rotations))

        # Foot
        foot = f"{side}Foot"
        if self._has_bone(foot):
            rotations = []
            for t in times:
                phase = ((t / duration) + phase_offset) * 2 * math.pi
                angle = math.sin(phase + 0.5) * 0.25 * params.intensity
                quat = self._euler_to_quaternion(angle, 0, 0)
                rotations.append(quat)
            tracks.append(self._create_rotation_track(foot, times, rotations))

        return tracks

    def _generate_arm_tracks(
        self,
        times: list[float],
        duration: float,
        params: AnimationParameters,
        side: str,
        phase_offset: float,
    ) -> list[KeyframeTrack]:
        """Generate arm tracks with elbow bend for running."""
        tracks = []

        # Upper arm swing
        arm = f"{side}Arm"
        if self._has_bone(arm):
            rotations = []
            for t in times:
                phase = ((t / duration) + phase_offset) * 2 * math.pi
                angle = math.sin(phase) * 0.45 * params.intensity
                quat = self._euler_to_quaternion(angle, 0, 0)
                rotations.append(quat)
            tracks.append(self._create_rotation_track(arm, times, rotations))

        # Forearm (elbow) - bent during run
        forearm = f"{side}ForeArm"
        if self._has_bone(forearm):
            rotations = []
            for t in times:
                phase = ((t / duration) + phase_offset) * 2 * math.pi
                # Keep elbow bent, vary slightly
                base_bend = 0.8  # ~45 degrees base
                variation = math.sin(phase) * 0.15
                angle = (base_bend + variation) * params.intensity
                quat = self._euler_to_quaternion(angle, 0, 0)
                rotations.append(quat)
            tracks.append(self._create_rotation_track(forearm, times, rotations))

        return tracks

    def _generate_spine_lean(
        self,
        times: list[float],
        duration: float,
        params: AnimationParameters,
    ) -> KeyframeTrack:
        """Generate forward lean in spine."""
        rotations = []

        for t in times:
            # Constant forward lean with slight bounce
            phase = (t / duration) * 4 * math.pi
            base_lean = 0.08 * params.intensity
            bounce = math.sin(phase) * 0.02 * params.intensity
            x_rot = base_lean + bounce
            quat = self._euler_to_quaternion(x_rot, 0, 0)
            rotations.append(quat)

        return self._create_rotation_track("Spine", times, rotations)

    def _generate_spine_twist(
        self,
        times: list[float],
        duration: float,
        params: AnimationParameters,
    ) -> KeyframeTrack:
        """Generate spine counter-rotation for running."""
        rotations = []

        for t in times:
            phase = (t / duration) * 2 * math.pi
            y_rot = math.sin(phase) * 0.06 * params.intensity
            quat = self._euler_to_quaternion(0, y_rot, 0)
            rotations.append(quat)

        return self._create_rotation_track("Spine1", times, rotations)
