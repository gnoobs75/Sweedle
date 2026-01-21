"""
Extended animation generators for humanoid characters.

Includes: Die, Sit, Crouch, Jump, Dodge, Wave, Cheer, Pickup
"""

import math
from typing import Optional

from .base import BaseAnimationGenerator
from ..schemas import AnimationParameters, AnimationData, KeyframeTrack


class DieGenerator(BaseAnimationGenerator):
    """Generates death animation for humanoid characters."""

    def generate(
        self,
        duration: float = 1.5,
        params: Optional[AnimationParameters] = None,
    ) -> AnimationData:
        """Generate death collapse animation."""
        params = params or AnimationParameters()
        times = self._create_times(duration, params)
        adjusted_duration = duration / params.speed

        tracks: list[KeyframeTrack] = []

        # Body falls
        if self._has_bone("Hips"):
            tracks.append(self._generate_hips_fall(times, adjusted_duration, params))

        if self._has_bone("Spine"):
            tracks.append(self._generate_spine_fall(times, adjusted_duration, params))

        if self._has_bone("Spine1"):
            tracks.append(self._generate_upper_spine_fall(times, adjusted_duration, params))

        # Head drops
        if self._has_bone("Head"):
            tracks.append(self._generate_head_fall(times, adjusted_duration, params))

        # Arms go limp
        for side in ["Left", "Right"]:
            tracks.extend(self._generate_arm_fall(times, adjusted_duration, params, side))

        # Legs buckle
        for side in ["Left", "Right"]:
            tracks.extend(self._generate_leg_fall(times, adjusted_duration, params, side))

        return AnimationData(
            name="Die",
            duration=adjusted_duration,
            frame_rate=self.fps,
            tracks=tracks,
        )

    def _ease_out(self, t):
        return 1 - (1 - t) * (1 - t)

    def _generate_hips_fall(self, times, duration, params):
        positions = []
        rotations = []
        for t in times:
            progress = t / duration
            if progress < 0.6:
                p = self._ease_out(progress / 0.6)
                y = -p * 0.5 * params.intensity
                x_rot = p * 0.3 * params.intensity
                z_rot = p * 0.2 * params.intensity
            else:
                y = -0.5 * params.intensity
                x_rot = 0.3 * params.intensity
                z_rot = 0.2 * params.intensity
            positions.append([0, y, 0])
            rotations.append(self._euler_to_quaternion(x_rot, 0, z_rot))
        return self._create_position_track("Hips", times, positions)

    def _generate_spine_fall(self, times, duration, params):
        rotations = []
        for t in times:
            progress = t / duration
            if progress < 0.6:
                p = self._ease_out(progress / 0.6)
                x_rot = p * 0.4 * params.intensity
            else:
                x_rot = 0.4 * params.intensity
            rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
        return self._create_rotation_track("Spine", times, rotations)

    def _generate_upper_spine_fall(self, times, duration, params):
        rotations = []
        for t in times:
            progress = t / duration
            if progress < 0.7:
                p = self._ease_out(progress / 0.7)
                x_rot = p * 0.3 * params.intensity
            else:
                x_rot = 0.3 * params.intensity
            rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
        return self._create_rotation_track("Spine1", times, rotations)

    def _generate_head_fall(self, times, duration, params):
        rotations = []
        for t in times:
            progress = t / duration
            if progress < 0.8:
                p = self._ease_out(progress / 0.8)
                x_rot = p * 0.5 * params.intensity
                z_rot = p * 0.2 * params.intensity
            else:
                x_rot = 0.5 * params.intensity
                z_rot = 0.2 * params.intensity
            rotations.append(self._euler_to_quaternion(x_rot, 0, z_rot))
        return self._create_rotation_track("Head", times, rotations)

    def _generate_arm_fall(self, times, duration, params, side):
        tracks = []

        arm = f"{side}Arm"
        if self._has_bone(arm):
            rotations = []
            for t in times:
                progress = t / duration
                if progress < 0.5:
                    p = self._ease_out(progress / 0.5)
                    x_rot = p * 0.3 * params.intensity
                    z_rot = (0.5 if side == "Left" else -0.5) * p * params.intensity
                else:
                    x_rot = 0.3 * params.intensity
                    z_rot = (0.5 if side == "Left" else -0.5) * params.intensity
                rotations.append(self._euler_to_quaternion(x_rot, 0, z_rot))
            tracks.append(self._create_rotation_track(arm, times, rotations))

        forearm = f"{side}ForeArm"
        if self._has_bone(forearm):
            rotations = []
            for t in times:
                progress = t / duration
                if progress < 0.6:
                    p = self._ease_out(progress / 0.6)
                    x_rot = p * 0.4 * params.intensity
                else:
                    x_rot = 0.4 * params.intensity
                rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
            tracks.append(self._create_rotation_track(forearm, times, rotations))

        return tracks

    def _generate_leg_fall(self, times, duration, params, side):
        tracks = []

        upleg = f"{side}UpLeg"
        if self._has_bone(upleg):
            rotations = []
            for t in times:
                progress = t / duration
                if progress < 0.5:
                    p = self._ease_out(progress / 0.5)
                    x_rot = p * 0.3 * params.intensity
                    z_rot = (0.2 if side == "Left" else -0.2) * p * params.intensity
                else:
                    x_rot = 0.3 * params.intensity
                    z_rot = (0.2 if side == "Left" else -0.2) * params.intensity
                rotations.append(self._euler_to_quaternion(x_rot, 0, z_rot))
            tracks.append(self._create_rotation_track(upleg, times, rotations))

        leg = f"{side}Leg"
        if self._has_bone(leg):
            rotations = []
            for t in times:
                progress = t / duration
                if progress < 0.4:
                    p = self._ease_out(progress / 0.4)
                    x_rot = p * 0.6 * params.intensity
                else:
                    x_rot = 0.6 * params.intensity
                rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
            tracks.append(self._create_rotation_track(leg, times, rotations))

        return tracks


class SitGenerator(BaseAnimationGenerator):
    """Generates sit down animation for humanoid characters."""

    def generate(
        self,
        duration: float = 1.2,
        params: Optional[AnimationParameters] = None,
    ) -> AnimationData:
        """Generate sitting down animation."""
        params = params or AnimationParameters()
        times = self._create_times(duration, params)
        adjusted_duration = duration / params.speed

        tracks: list[KeyframeTrack] = []

        # Lower body
        if self._has_bone("Hips"):
            tracks.append(self._generate_hips_sit(times, adjusted_duration, params))

        # Bend knees
        for side in ["Left", "Right"]:
            tracks.extend(self._generate_leg_sit(times, adjusted_duration, params, side))

        # Spine adjusts
        if self._has_bone("Spine"):
            tracks.append(self._generate_spine_sit(times, adjusted_duration, params))

        # Arms rest
        for side in ["Left", "Right"]:
            tracks.extend(self._generate_arm_sit(times, adjusted_duration, params, side))

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
            p = self._ease_in_out(t / duration)
            y = -p * 0.4 * params.intensity
            z = -p * 0.1 * params.intensity
            positions.append([0, y, z])
            x_rot = -p * 0.1 * params.intensity
            rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
        return self._create_position_track("Hips", times, positions)

    def _generate_leg_sit(self, times, duration, params, side):
        tracks = []

        upleg = f"{side}UpLeg"
        if self._has_bone(upleg):
            rotations = []
            for t in times:
                p = self._ease_in_out(t / duration)
                x_rot = p * 1.4 * params.intensity  # ~80 degrees
                rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
            tracks.append(self._create_rotation_track(upleg, times, rotations))

        leg = f"{side}Leg"
        if self._has_bone(leg):
            rotations = []
            for t in times:
                p = self._ease_in_out(t / duration)
                x_rot = p * 1.5 * params.intensity  # ~85 degrees
                rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
            tracks.append(self._create_rotation_track(leg, times, rotations))

        return tracks

    def _generate_spine_sit(self, times, duration, params):
        rotations = []
        for t in times:
            p = self._ease_in_out(t / duration)
            x_rot = p * 0.15 * params.intensity
            rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
        return self._create_rotation_track("Spine", times, rotations)

    def _generate_arm_sit(self, times, duration, params, side):
        tracks = []

        arm = f"{side}Arm"
        if self._has_bone(arm):
            rotations = []
            for t in times:
                p = self._ease_in_out(t / duration)
                x_rot = p * 0.3 * params.intensity
                z_rot = (0.1 if side == "Left" else -0.1) * p * params.intensity
                rotations.append(self._euler_to_quaternion(x_rot, 0, z_rot))
            tracks.append(self._create_rotation_track(arm, times, rotations))

        forearm = f"{side}ForeArm"
        if self._has_bone(forearm):
            rotations = []
            for t in times:
                p = self._ease_in_out(t / duration)
                x_rot = p * 0.8 * params.intensity
                rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
            tracks.append(self._create_rotation_track(forearm, times, rotations))

        return tracks


class CrouchGenerator(BaseAnimationGenerator):
    """Generates crouch animation for humanoid characters."""

    def generate(
        self,
        duration: float = 0.6,
        params: Optional[AnimationParameters] = None,
    ) -> AnimationData:
        """Generate crouching animation."""
        params = params or AnimationParameters()
        times = self._create_times(duration, params)
        adjusted_duration = duration / params.speed

        tracks: list[KeyframeTrack] = []

        # Lower hips
        if self._has_bone("Hips"):
            tracks.append(self._generate_hips_crouch(times, adjusted_duration, params))

        # Bend knees
        for side in ["Left", "Right"]:
            tracks.extend(self._generate_leg_crouch(times, adjusted_duration, params, side))

        # Lean forward
        if self._has_bone("Spine"):
            tracks.append(self._generate_spine_crouch(times, adjusted_duration, params))

        # Arms ready
        for side in ["Left", "Right"]:
            tracks.extend(self._generate_arm_crouch(times, adjusted_duration, params, side))

        return AnimationData(
            name="Crouch",
            duration=adjusted_duration,
            frame_rate=self.fps,
            tracks=tracks,
        )

    def _ease_in_out(self, t):
        return t * t * (3 - 2 * t)

    def _generate_hips_crouch(self, times, duration, params):
        positions = []
        for t in times:
            p = self._ease_in_out(t / duration)
            y = -p * 0.25 * params.intensity
            positions.append([0, y, 0])
        return self._create_position_track("Hips", times, positions)

    def _generate_leg_crouch(self, times, duration, params, side):
        tracks = []

        upleg = f"{side}UpLeg"
        if self._has_bone(upleg):
            rotations = []
            for t in times:
                p = self._ease_in_out(t / duration)
                x_rot = p * 0.8 * params.intensity
                rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
            tracks.append(self._create_rotation_track(upleg, times, rotations))

        leg = f"{side}Leg"
        if self._has_bone(leg):
            rotations = []
            for t in times:
                p = self._ease_in_out(t / duration)
                x_rot = p * 1.2 * params.intensity
                rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
            tracks.append(self._create_rotation_track(leg, times, rotations))

        return tracks

    def _generate_spine_crouch(self, times, duration, params):
        rotations = []
        for t in times:
            p = self._ease_in_out(t / duration)
            x_rot = p * 0.2 * params.intensity
            rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
        return self._create_rotation_track("Spine", times, rotations)

    def _generate_arm_crouch(self, times, duration, params, side):
        tracks = []

        arm = f"{side}Arm"
        if self._has_bone(arm):
            rotations = []
            for t in times:
                p = self._ease_in_out(t / duration)
                x_rot = p * 0.5 * params.intensity
                rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
            tracks.append(self._create_rotation_track(arm, times, rotations))

        forearm = f"{side}ForeArm"
        if self._has_bone(forearm):
            rotations = []
            for t in times:
                p = self._ease_in_out(t / duration)
                x_rot = p * 1.0 * params.intensity
                rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
            tracks.append(self._create_rotation_track(forearm, times, rotations))

        return tracks


class JumpGenerator(BaseAnimationGenerator):
    """Generates jump animation for humanoid characters."""

    def generate(
        self,
        duration: float = 0.8,
        params: Optional[AnimationParameters] = None,
    ) -> AnimationData:
        """Generate jump animation with crouch, leap, air, and land phases."""
        params = params or AnimationParameters()
        times = self._create_times(duration, params)
        adjusted_duration = duration / params.speed

        tracks: list[KeyframeTrack] = []

        # Body arc
        if self._has_bone("Hips"):
            tracks.append(self._generate_jump_arc(times, adjusted_duration, params))

        # Legs push and tuck
        for side in ["Left", "Right"]:
            tracks.extend(self._generate_leg_jump(times, adjusted_duration, params, side))

        # Arms swing
        for side in ["Left", "Right"]:
            tracks.extend(self._generate_arm_jump(times, adjusted_duration, params, side))

        # Spine arches
        if self._has_bone("Spine"):
            tracks.append(self._generate_spine_jump(times, adjusted_duration, params))

        return AnimationData(
            name="Jump",
            duration=adjusted_duration,
            frame_rate=self.fps,
            tracks=tracks,
        )

    def _get_phase(self, t, duration):
        progress = t / duration
        if progress < 0.2:
            return "crouch", progress / 0.2
        elif progress < 0.4:
            return "push", (progress - 0.2) / 0.2
        elif progress < 0.7:
            return "air", (progress - 0.4) / 0.3
        else:
            return "land", (progress - 0.7) / 0.3

    def _generate_jump_arc(self, times, duration, params):
        positions = []
        for t in times:
            phase, p = self._get_phase(t, duration)
            if phase == "crouch":
                y = -p * 0.15 * params.intensity
            elif phase == "push":
                y = -0.15 + p * 0.4 * params.intensity
            elif phase == "air":
                y = 0.25 - p * 0.15 * params.intensity
            else:
                y = 0.1 * (1 - p) * params.intensity
            positions.append([0, y * params.intensity, 0])
        return self._create_position_track("Hips", times, positions)

    def _generate_leg_jump(self, times, duration, params, side):
        tracks = []

        upleg = f"{side}UpLeg"
        if self._has_bone(upleg):
            rotations = []
            for t in times:
                phase, p = self._get_phase(t, duration)
                if phase == "crouch":
                    x_rot = p * 0.6 * params.intensity
                elif phase == "push":
                    x_rot = 0.6 - p * 0.8 * params.intensity
                elif phase == "air":
                    x_rot = -0.2 * params.intensity
                else:
                    x_rot = -0.2 + p * 0.2 * params.intensity
                rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
            tracks.append(self._create_rotation_track(upleg, times, rotations))

        leg = f"{side}Leg"
        if self._has_bone(leg):
            rotations = []
            for t in times:
                phase, p = self._get_phase(t, duration)
                if phase == "crouch":
                    x_rot = p * 1.0 * params.intensity
                elif phase == "push":
                    x_rot = 1.0 - p * 1.0 * params.intensity
                elif phase == "air":
                    x_rot = p * 0.3 * params.intensity
                else:
                    x_rot = 0.3 * (1 - p) * params.intensity
                rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
            tracks.append(self._create_rotation_track(leg, times, rotations))

        return tracks

    def _generate_arm_jump(self, times, duration, params, side):
        tracks = []

        arm = f"{side}Arm"
        if self._has_bone(arm):
            rotations = []
            for t in times:
                phase, p = self._get_phase(t, duration)
                if phase == "crouch":
                    x_rot = p * 0.5 * params.intensity
                elif phase == "push":
                    x_rot = 0.5 - p * 1.5 * params.intensity
                elif phase == "air":
                    x_rot = -1.0 + p * 0.5 * params.intensity
                else:
                    x_rot = -0.5 * (1 - p) * params.intensity
                rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
            tracks.append(self._create_rotation_track(arm, times, rotations))

        return tracks

    def _generate_spine_jump(self, times, duration, params):
        rotations = []
        for t in times:
            phase, p = self._get_phase(t, duration)
            if phase == "crouch":
                x_rot = p * 0.2 * params.intensity
            elif phase == "push":
                x_rot = 0.2 - p * 0.3 * params.intensity
            elif phase == "air":
                x_rot = -0.1 * params.intensity
            else:
                x_rot = -0.1 * (1 - p) * params.intensity
            rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
        return self._create_rotation_track("Spine", times, rotations)


class DodgeGenerator(BaseAnimationGenerator):
    """Generates dodge/roll animation for humanoid characters."""

    def generate(
        self,
        duration: float = 0.8,
        params: Optional[AnimationParameters] = None,
    ) -> AnimationData:
        """Generate side dodge roll animation."""
        params = params or AnimationParameters()
        times = self._create_times(duration, params)
        adjusted_duration = duration / params.speed

        tracks: list[KeyframeTrack] = []

        # Body rolls sideways
        if self._has_bone("Hips"):
            tracks.append(self._generate_dodge_roll(times, adjusted_duration, params))

        # Tuck body
        if self._has_bone("Spine"):
            tracks.append(self._generate_spine_tuck(times, adjusted_duration, params))

        # Arms tuck in
        for side in ["Left", "Right"]:
            tracks.extend(self._generate_arm_tuck(times, adjusted_duration, params, side))

        # Legs tuck
        for side in ["Left", "Right"]:
            tracks.extend(self._generate_leg_tuck(times, adjusted_duration, params, side))

        return AnimationData(
            name="Dodge",
            duration=adjusted_duration,
            frame_rate=self.fps,
            tracks=tracks,
        )

    def _ease_in_out(self, t):
        return t * t * (3 - 2 * t)

    def _generate_dodge_roll(self, times, duration, params):
        positions = []
        rotations = []
        for t in times:
            progress = t / duration
            if progress < 0.3:
                # Crouch and start roll
                p = progress / 0.3
                y = -p * 0.2 * params.intensity
                x = p * 0.3 * params.intensity
                z_rot = p * 1.0 * params.intensity
            elif progress < 0.7:
                # Rolling
                p = (progress - 0.3) / 0.4
                y = -0.2 + p * 0.1 * params.intensity
                x = 0.3 + p * 0.4 * params.intensity
                z_rot = 1.0 + p * 1.5 * params.intensity
            else:
                # Recovery
                p = (progress - 0.7) / 0.3
                y = -0.1 * (1 - p) * params.intensity
                x = 0.7 * params.intensity
                z_rot = 2.5 * (1 - p * 0.5) * params.intensity
            positions.append([x, y, 0])
            rotations.append(self._euler_to_quaternion(0, 0, z_rot))
        return self._create_position_track("Hips", times, positions)

    def _generate_spine_tuck(self, times, duration, params):
        rotations = []
        for t in times:
            progress = t / duration
            if progress < 0.3:
                p = progress / 0.3
                x_rot = p * 0.5 * params.intensity
            elif progress < 0.7:
                x_rot = 0.5 * params.intensity
            else:
                p = (progress - 0.7) / 0.3
                x_rot = 0.5 * (1 - p) * params.intensity
            rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
        return self._create_rotation_track("Spine", times, rotations)

    def _generate_arm_tuck(self, times, duration, params, side):
        tracks = []

        arm = f"{side}Arm"
        if self._has_bone(arm):
            rotations = []
            for t in times:
                progress = t / duration
                if progress < 0.7:
                    x_rot = 0.3 * params.intensity
                    z_rot = (0.5 if side == "Left" else -0.5) * params.intensity
                else:
                    p = (progress - 0.7) / 0.3
                    x_rot = 0.3 * (1 - p) * params.intensity
                    z_rot = (0.5 if side == "Left" else -0.5) * (1 - p) * params.intensity
                rotations.append(self._euler_to_quaternion(x_rot, 0, z_rot))
            tracks.append(self._create_rotation_track(arm, times, rotations))

        forearm = f"{side}ForeArm"
        if self._has_bone(forearm):
            rotations = []
            for t in times:
                progress = t / duration
                if progress < 0.7:
                    x_rot = 1.5 * params.intensity
                else:
                    p = (progress - 0.7) / 0.3
                    x_rot = 1.5 * (1 - p) * params.intensity
                rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
            tracks.append(self._create_rotation_track(forearm, times, rotations))

        return tracks

    def _generate_leg_tuck(self, times, duration, params, side):
        tracks = []

        upleg = f"{side}UpLeg"
        if self._has_bone(upleg):
            rotations = []
            for t in times:
                progress = t / duration
                if progress < 0.3:
                    p = progress / 0.3
                    x_rot = p * 0.8 * params.intensity
                elif progress < 0.7:
                    x_rot = 0.8 * params.intensity
                else:
                    p = (progress - 0.7) / 0.3
                    x_rot = 0.8 * (1 - p) * params.intensity
                rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
            tracks.append(self._create_rotation_track(upleg, times, rotations))

        leg = f"{side}Leg"
        if self._has_bone(leg):
            rotations = []
            for t in times:
                progress = t / duration
                if progress < 0.3:
                    p = progress / 0.3
                    x_rot = p * 1.2 * params.intensity
                elif progress < 0.7:
                    x_rot = 1.2 * params.intensity
                else:
                    p = (progress - 0.7) / 0.3
                    x_rot = 1.2 * (1 - p) * params.intensity
                rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
            tracks.append(self._create_rotation_track(leg, times, rotations))

        return tracks


class WaveGenerator(BaseAnimationGenerator):
    """Generates wave animation for humanoid characters."""

    def generate(
        self,
        duration: float = 2.0,
        params: Optional[AnimationParameters] = None,
    ) -> AnimationData:
        """Generate waving hand animation."""
        params = params or AnimationParameters()
        times = self._create_times(duration, params)
        adjusted_duration = duration / params.speed

        tracks: list[KeyframeTrack] = []

        # Raise right arm
        if self._has_bone("RightArm"):
            tracks.append(self._generate_arm_wave(times, adjusted_duration, params))

        if self._has_bone("RightForeArm"):
            tracks.append(self._generate_forearm_wave(times, adjusted_duration, params))

        if self._has_bone("RightHand"):
            tracks.append(self._generate_hand_wave(times, adjusted_duration, params))

        # Slight body lean
        if self._has_bone("Spine"):
            tracks.append(self._generate_spine_wave(times, adjusted_duration, params))

        return AnimationData(
            name="Wave",
            duration=adjusted_duration,
            frame_rate=self.fps,
            tracks=tracks,
        )

    def _ease_in_out(self, t):
        return t * t * (3 - 2 * t)

    def _generate_arm_wave(self, times, duration, params):
        rotations = []
        for t in times:
            progress = t / duration
            if progress < 0.2:
                # Raise arm
                p = self._ease_in_out(progress / 0.2)
                x_rot = -p * 1.2 * params.intensity
                z_rot = -p * 0.8 * params.intensity
            elif progress < 0.8:
                # Hold raised
                x_rot = -1.2 * params.intensity
                z_rot = -0.8 * params.intensity
            else:
                # Lower arm
                p = self._ease_in_out((progress - 0.8) / 0.2)
                x_rot = -1.2 * (1 - p) * params.intensity
                z_rot = -0.8 * (1 - p) * params.intensity
            rotations.append(self._euler_to_quaternion(x_rot, 0, z_rot))
        return self._create_rotation_track("RightArm", times, rotations)

    def _generate_forearm_wave(self, times, duration, params):
        rotations = []
        for t in times:
            progress = t / duration
            if 0.2 < progress < 0.8:
                # Wave back and forth
                wave_progress = (progress - 0.2) / 0.6
                x_rot = 0.3 * params.intensity
                z_rot = math.sin(wave_progress * 6 * math.pi) * 0.4 * params.intensity
            else:
                x_rot = 0
                z_rot = 0
            rotations.append(self._euler_to_quaternion(x_rot, 0, z_rot))
        return self._create_rotation_track("RightForeArm", times, rotations)

    def _generate_hand_wave(self, times, duration, params):
        rotations = []
        for t in times:
            progress = t / duration
            if 0.2 < progress < 0.8:
                wave_progress = (progress - 0.2) / 0.6
                z_rot = math.sin(wave_progress * 8 * math.pi) * 0.3 * params.intensity
            else:
                z_rot = 0
            rotations.append(self._euler_to_quaternion(0, 0, z_rot))
        return self._create_rotation_track("RightHand", times, rotations)

    def _generate_spine_wave(self, times, duration, params):
        rotations = []
        for t in times:
            progress = t / duration
            if 0.2 < progress < 0.8:
                z_rot = -0.05 * params.intensity
            else:
                z_rot = 0
            rotations.append(self._euler_to_quaternion(0, 0, z_rot))
        return self._create_rotation_track("Spine", times, rotations)


class CheerGenerator(BaseAnimationGenerator):
    """Generates cheer/celebrate animation for humanoid characters."""

    def generate(
        self,
        duration: float = 2.0,
        params: Optional[AnimationParameters] = None,
    ) -> AnimationData:
        """Generate cheering celebration animation."""
        params = params or AnimationParameters()
        times = self._create_times(duration, params)
        adjusted_duration = duration / params.speed

        tracks: list[KeyframeTrack] = []

        # Both arms raise
        for side in ["Left", "Right"]:
            tracks.extend(self._generate_arm_cheer(times, adjusted_duration, params, side))

        # Body bounces
        if self._has_bone("Hips"):
            tracks.append(self._generate_body_bounce(times, adjusted_duration, params))

        # Head looks up
        if self._has_bone("Head"):
            tracks.append(self._generate_head_cheer(times, adjusted_duration, params))

        return AnimationData(
            name="Cheer",
            duration=adjusted_duration,
            frame_rate=self.fps,
            tracks=tracks,
        )

    def _ease_in_out(self, t):
        return t * t * (3 - 2 * t)

    def _generate_arm_cheer(self, times, duration, params, side):
        tracks = []

        arm = f"{side}Arm"
        if self._has_bone(arm):
            rotations = []
            for t in times:
                progress = t / duration
                if progress < 0.2:
                    p = self._ease_in_out(progress / 0.2)
                    x_rot = -p * 2.5 * params.intensity
                    z_rot = (0.3 if side == "Left" else -0.3) * p * params.intensity
                elif progress < 0.8:
                    # Pump fists
                    pump = math.sin((progress - 0.2) / 0.6 * 6 * math.pi) * 0.2
                    x_rot = (-2.5 + pump) * params.intensity
                    z_rot = (0.3 if side == "Left" else -0.3) * params.intensity
                else:
                    p = self._ease_in_out((progress - 0.8) / 0.2)
                    x_rot = -2.5 * (1 - p) * params.intensity
                    z_rot = (0.3 if side == "Left" else -0.3) * (1 - p) * params.intensity
                rotations.append(self._euler_to_quaternion(x_rot, 0, z_rot))
            tracks.append(self._create_rotation_track(arm, times, rotations))

        forearm = f"{side}ForeArm"
        if self._has_bone(forearm):
            rotations = []
            for t in times:
                progress = t / duration
                if progress < 0.2:
                    p = self._ease_in_out(progress / 0.2)
                    x_rot = p * 0.5 * params.intensity
                elif progress < 0.8:
                    x_rot = 0.5 * params.intensity
                else:
                    p = self._ease_in_out((progress - 0.8) / 0.2)
                    x_rot = 0.5 * (1 - p) * params.intensity
                rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
            tracks.append(self._create_rotation_track(forearm, times, rotations))

        return tracks

    def _generate_body_bounce(self, times, duration, params):
        positions = []
        for t in times:
            progress = t / duration
            if 0.15 < progress < 0.85:
                bounce = math.sin((progress - 0.15) / 0.7 * 8 * math.pi)
                y = max(0, bounce) * 0.05 * params.intensity
            else:
                y = 0
            positions.append([0, y, 0])
        return self._create_position_track("Hips", times, positions)

    def _generate_head_cheer(self, times, duration, params):
        rotations = []
        for t in times:
            progress = t / duration
            if progress < 0.2:
                p = self._ease_in_out(progress / 0.2)
                x_rot = -p * 0.2 * params.intensity
            elif progress < 0.8:
                x_rot = -0.2 * params.intensity
            else:
                p = self._ease_in_out((progress - 0.8) / 0.2)
                x_rot = -0.2 * (1 - p) * params.intensity
            rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
        return self._create_rotation_track("Head", times, rotations)


class PickupGenerator(BaseAnimationGenerator):
    """Generates pickup/grab animation for humanoid characters."""

    def generate(
        self,
        duration: float = 1.5,
        params: Optional[AnimationParameters] = None,
    ) -> AnimationData:
        """Generate bending down to pick something up animation."""
        params = params or AnimationParameters()
        times = self._create_times(duration, params)
        adjusted_duration = duration / params.speed

        tracks: list[KeyframeTrack] = []

        # Bend down
        if self._has_bone("Hips"):
            tracks.append(self._generate_hips_bend(times, adjusted_duration, params))

        if self._has_bone("Spine"):
            tracks.append(self._generate_spine_bend(times, adjusted_duration, params))

        if self._has_bone("Spine1"):
            tracks.append(self._generate_upper_spine_bend(times, adjusted_duration, params))

        # Legs bend
        for side in ["Left", "Right"]:
            tracks.extend(self._generate_leg_bend(times, adjusted_duration, params, side))

        # Arms reach
        for side in ["Left", "Right"]:
            tracks.extend(self._generate_arm_reach(times, adjusted_duration, params, side))

        # Head looks down then up
        if self._has_bone("Head"):
            tracks.append(self._generate_head_look(times, adjusted_duration, params))

        return AnimationData(
            name="Pickup",
            duration=adjusted_duration,
            frame_rate=self.fps,
            tracks=tracks,
        )

    def _ease_in_out(self, t):
        return t * t * (3 - 2 * t)

    def _get_phase(self, t, duration):
        progress = t / duration
        if progress < 0.4:
            return "bend", progress / 0.4
        elif progress < 0.6:
            return "grab", (progress - 0.4) / 0.2
        else:
            return "rise", (progress - 0.6) / 0.4

    def _generate_hips_bend(self, times, duration, params):
        positions = []
        rotations = []
        for t in times:
            phase, p = self._get_phase(t, duration)
            if phase == "bend":
                pp = self._ease_in_out(p)
                y = -pp * 0.2 * params.intensity
                x_rot = pp * 0.3 * params.intensity
            elif phase == "grab":
                y = -0.2 * params.intensity
                x_rot = 0.3 * params.intensity
            else:
                pp = self._ease_in_out(p)
                y = -0.2 * (1 - pp) * params.intensity
                x_rot = 0.3 * (1 - pp) * params.intensity
            positions.append([0, y, 0])
            rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
        return self._create_position_track("Hips", times, positions)

    def _generate_spine_bend(self, times, duration, params):
        rotations = []
        for t in times:
            phase, p = self._get_phase(t, duration)
            if phase == "bend":
                pp = self._ease_in_out(p)
                x_rot = pp * 0.6 * params.intensity
            elif phase == "grab":
                x_rot = 0.6 * params.intensity
            else:
                pp = self._ease_in_out(p)
                x_rot = 0.6 * (1 - pp) * params.intensity
            rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
        return self._create_rotation_track("Spine", times, rotations)

    def _generate_upper_spine_bend(self, times, duration, params):
        rotations = []
        for t in times:
            phase, p = self._get_phase(t, duration)
            if phase == "bend":
                pp = self._ease_in_out(p)
                x_rot = pp * 0.4 * params.intensity
            elif phase == "grab":
                x_rot = 0.4 * params.intensity
            else:
                pp = self._ease_in_out(p)
                x_rot = 0.4 * (1 - pp) * params.intensity
            rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
        return self._create_rotation_track("Spine1", times, rotations)

    def _generate_leg_bend(self, times, duration, params, side):
        tracks = []

        upleg = f"{side}UpLeg"
        if self._has_bone(upleg):
            rotations = []
            for t in times:
                phase, p = self._get_phase(t, duration)
                if phase == "bend":
                    pp = self._ease_in_out(p)
                    x_rot = pp * 0.4 * params.intensity
                elif phase == "grab":
                    x_rot = 0.4 * params.intensity
                else:
                    pp = self._ease_in_out(p)
                    x_rot = 0.4 * (1 - pp) * params.intensity
                rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
            tracks.append(self._create_rotation_track(upleg, times, rotations))

        leg = f"{side}Leg"
        if self._has_bone(leg):
            rotations = []
            for t in times:
                phase, p = self._get_phase(t, duration)
                if phase == "bend":
                    pp = self._ease_in_out(p)
                    x_rot = pp * 0.6 * params.intensity
                elif phase == "grab":
                    x_rot = 0.6 * params.intensity
                else:
                    pp = self._ease_in_out(p)
                    x_rot = 0.6 * (1 - pp) * params.intensity
                rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
            tracks.append(self._create_rotation_track(leg, times, rotations))

        return tracks

    def _generate_arm_reach(self, times, duration, params, side):
        tracks = []

        arm = f"{side}Arm"
        if self._has_bone(arm):
            rotations = []
            for t in times:
                phase, p = self._get_phase(t, duration)
                if phase == "bend":
                    pp = self._ease_in_out(p)
                    x_rot = pp * 0.8 * params.intensity
                elif phase == "grab":
                    x_rot = 0.8 * params.intensity
                else:
                    pp = self._ease_in_out(p)
                    x_rot = 0.8 * (1 - pp * 0.7) * params.intensity
                rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
            tracks.append(self._create_rotation_track(arm, times, rotations))

        forearm = f"{side}ForeArm"
        if self._has_bone(forearm):
            rotations = []
            for t in times:
                phase, p = self._get_phase(t, duration)
                if phase == "bend":
                    pp = self._ease_in_out(p)
                    x_rot = pp * 0.3 * params.intensity
                elif phase == "grab":
                    # Grab motion
                    x_rot = 0.3 + p * 0.5 * params.intensity
                else:
                    pp = self._ease_in_out(p)
                    x_rot = (0.8 - pp * 0.3) * params.intensity
                rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
            tracks.append(self._create_rotation_track(forearm, times, rotations))

        return tracks

    def _generate_head_look(self, times, duration, params):
        rotations = []
        for t in times:
            phase, p = self._get_phase(t, duration)
            if phase == "bend":
                pp = self._ease_in_out(p)
                x_rot = pp * 0.3 * params.intensity
            elif phase == "grab":
                x_rot = 0.3 * params.intensity
            else:
                pp = self._ease_in_out(p)
                x_rot = 0.3 * (1 - pp * 1.5) * params.intensity
            rotations.append(self._euler_to_quaternion(x_rot, 0, 0))
        return self._create_rotation_track("Head", times, rotations)
