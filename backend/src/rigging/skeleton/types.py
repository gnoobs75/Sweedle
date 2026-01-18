"""
Core skeleton data types and utilities.
"""

from dataclasses import dataclass, field
from typing import Optional
import numpy as np

from ..schemas import BoneData, SkeletonData, CharacterType


@dataclass
class Bone:
    """Runtime bone representation."""
    name: str
    parent: Optional["Bone"] = None
    children: list["Bone"] = field(default_factory=list)
    head: np.ndarray = field(default_factory=lambda: np.array([0.0, 0.0, 0.0]))
    tail: np.ndarray = field(default_factory=lambda: np.array([0.0, 0.1, 0.0]))
    rotation: np.ndarray = field(default_factory=lambda: np.array([0.0, 0.0, 0.0, 1.0]))
    scale: np.ndarray = field(default_factory=lambda: np.array([1.0, 1.0, 1.0]))
    connected: bool = False
    deform: bool = True

    # Transform matrices (computed)
    local_matrix: Optional[np.ndarray] = None
    world_matrix: Optional[np.ndarray] = None
    bind_matrix: Optional[np.ndarray] = None

    def add_child(self, child: "Bone") -> None:
        """Add a child bone."""
        child.parent = self
        self.children.append(child)

    @property
    def length(self) -> float:
        """Get bone length."""
        return float(np.linalg.norm(self.tail - self.head))

    @property
    def direction(self) -> np.ndarray:
        """Get normalized bone direction."""
        diff = self.tail - self.head
        length = np.linalg.norm(diff)
        if length > 0:
            return diff / length
        return np.array([0.0, 1.0, 0.0])

    def to_bone_data(self) -> BoneData:
        """Convert to Pydantic BoneData."""
        return BoneData(
            name=self.name,
            parent=self.parent.name if self.parent else None,
            head_position=tuple(self.head.tolist()),
            tail_position=tuple(self.tail.tolist()),
            rotation=tuple(self.rotation.tolist()),
            scale=tuple(self.scale.tolist()),
            connected=self.connected,
            deform=self.deform,
        )


@dataclass
class Skeleton:
    """Complete skeleton structure."""
    root: Bone
    bones: dict[str, Bone] = field(default_factory=dict)
    character_type: CharacterType = CharacterType.HUMANOID

    def __post_init__(self):
        """Build bone dictionary after initialization."""
        if not self.bones:
            self._build_bone_dict(self.root)

    def _build_bone_dict(self, bone: Bone) -> None:
        """Recursively build bone dictionary."""
        self.bones[bone.name] = bone
        for child in bone.children:
            self._build_bone_dict(child)

    def get_bone(self, name: str) -> Optional[Bone]:
        """Get bone by name."""
        return self.bones.get(name)

    def get_all_bones(self) -> list[Bone]:
        """Get all bones in order (root first, depth-first)."""
        result = []
        self._collect_bones(self.root, result)
        return result

    def _collect_bones(self, bone: Bone, result: list[Bone]) -> None:
        """Recursively collect bones."""
        result.append(bone)
        for child in bone.children:
            self._collect_bones(child, result)

    @property
    def bone_count(self) -> int:
        """Get total bone count."""
        return len(self.bones)

    def to_skeleton_data(self) -> SkeletonData:
        """Convert to Pydantic SkeletonData."""
        bones = [bone.to_bone_data() for bone in self.get_all_bones()]
        return SkeletonData(
            root_bone=self.root.name,
            bones=bones,
            character_type=self.character_type,
            bone_count=len(bones),
        )

    def scale_to_mesh(self, mesh_height: float, mesh_center: np.ndarray) -> None:
        """
        Scale and position skeleton to fit a mesh.

        Args:
            mesh_height: Height of the mesh bounding box
            mesh_center: Center of the mesh bounding box
        """
        # Calculate current skeleton height
        all_bones = self.get_all_bones()
        if not all_bones:
            return

        # Find skeleton bounds
        all_positions = []
        for bone in all_bones:
            all_positions.append(bone.head)
            all_positions.append(bone.tail)

        positions = np.array(all_positions)
        skeleton_min = positions.min(axis=0)
        skeleton_max = positions.max(axis=0)
        skeleton_height = skeleton_max[1] - skeleton_min[1]  # Y is up

        if skeleton_height <= 0:
            return

        # Calculate scale factor
        scale_factor = mesh_height / skeleton_height

        # Scale and translate all bones
        skeleton_center = (skeleton_min + skeleton_max) / 2
        offset = mesh_center - skeleton_center * scale_factor

        for bone in all_bones:
            bone.head = bone.head * scale_factor + offset
            bone.tail = bone.tail * scale_factor + offset

    def fit_arms_to_mesh(self, mesh_vertices: np.ndarray, mesh_bounds: tuple) -> None:
        """
        Adjust arm bone positions based on actual mesh geometry.

        Analyzes mesh vertices to find where arms actually are and adjusts
        the arm bones to follow the mesh pose (T-pose, A-pose, etc).

        Args:
            mesh_vertices: Numpy array of mesh vertex positions (N, 3)
            mesh_bounds: Tuple of (min_bound, max_bound) arrays
        """
        bbox_min, bbox_max = mesh_bounds
        mesh_width = bbox_max[0] - bbox_min[0]
        mesh_height = bbox_max[1] - bbox_min[1]
        mesh_center_x = (bbox_max[0] + bbox_min[0]) / 2

        # Arm bone names for humanoid
        left_arm_bones = ["LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand"]
        right_arm_bones = ["RightShoulder", "RightArm", "RightForeArm", "RightHand"]

        # Check if we have these bones
        if not all(self.get_bone(b) for b in left_arm_bones + right_arm_bones):
            return

        # Find shoulder height from skeleton (should already be scaled)
        left_shoulder = self.get_bone("LeftShoulder")
        if not left_shoulder:
            return

        shoulder_height = left_shoulder.head[1]

        # Analyze left arm
        left_arm_info = self._find_arm_trajectory(
            mesh_vertices, mesh_center_x, shoulder_height, mesh_width, side="left"
        )
        if left_arm_info:
            self._adjust_arm_bones(left_arm_bones, left_arm_info, side="left")

        # Analyze right arm
        right_arm_info = self._find_arm_trajectory(
            mesh_vertices, mesh_center_x, shoulder_height, mesh_width, side="right"
        )
        if right_arm_info:
            self._adjust_arm_bones(right_arm_bones, right_arm_info, side="right")

    def _find_arm_trajectory(
        self,
        vertices: np.ndarray,
        center_x: float,
        shoulder_height: float,
        mesh_width: float,
        side: str,
    ) -> Optional[dict]:
        """
        Find the arm trajectory by analyzing mesh vertices.

        Args:
            vertices: Mesh vertices
            center_x: X coordinate of mesh center
            shoulder_height: Estimated shoulder Y coordinate
            mesh_width: Total mesh width
            side: "left" or "right"

        Returns:
            Dict with shoulder_pos, elbow_pos, hand_pos, arm_direction
        """
        # Determine which side we're analyzing
        if side == "left":
            # Left arm: X > center (positive X direction)
            side_vertices = vertices[vertices[:, 0] > center_x + mesh_width * 0.05]
        else:
            # Right arm: X < center (negative X direction)
            side_vertices = vertices[vertices[:, 0] < center_x - mesh_width * 0.05]

        if len(side_vertices) < 10:
            return None

        # Find vertices in the arm region (near shoulder height, extending outward)
        # Shoulder region: Y within 15% of shoulder height
        height_tolerance = mesh_width * 0.4  # Allow significant Y variation for A-pose
        arm_region = side_vertices[
            np.abs(side_vertices[:, 1] - shoulder_height) < height_tolerance
        ]

        if len(arm_region) < 5:
            return None

        # Find the extremity (hand position) - furthest point from center on this side
        if side == "left":
            distances = arm_region[:, 0] - center_x
        else:
            distances = center_x - arm_region[:, 0]

        # Get the most extreme points (top 5% by distance)
        extreme_threshold = np.percentile(distances, 95)
        extreme_vertices = arm_region[distances >= extreme_threshold]

        if len(extreme_vertices) < 2:
            return None

        # Hand position: average of extreme vertices
        hand_pos = np.mean(extreme_vertices, axis=0)

        # Shoulder position: find vertices closest to skeleton shoulder
        shoulder_bone = self.get_bone(f"{'Left' if side == 'left' else 'Right'}Shoulder")
        if not shoulder_bone:
            return None

        shoulder_region_center = shoulder_bone.head.copy()
        dists_to_shoulder = np.linalg.norm(arm_region - shoulder_region_center, axis=1)
        closest_to_shoulder = arm_region[np.argsort(dists_to_shoulder)[:max(5, len(arm_region) // 10)]]
        shoulder_pos = np.mean(closest_to_shoulder, axis=0)

        # Calculate arm direction vector
        arm_direction = hand_pos - shoulder_pos
        arm_length = np.linalg.norm(arm_direction)

        if arm_length < mesh_width * 0.1:
            return None

        arm_direction = arm_direction / arm_length

        # Elbow position: midpoint along arm, slightly below direct line for natural bend
        elbow_pos = shoulder_pos + arm_direction * arm_length * 0.45
        # Add slight backward bend for more natural elbow position
        elbow_pos[2] -= arm_length * 0.02

        return {
            "shoulder_pos": shoulder_pos,
            "elbow_pos": elbow_pos,
            "hand_pos": hand_pos,
            "arm_direction": arm_direction,
            "arm_length": arm_length,
        }

    def _adjust_arm_bones(self, bone_names: list, arm_info: dict, side: str) -> None:
        """
        Adjust arm bone positions based on detected arm trajectory.

        Args:
            bone_names: List of bone names [Shoulder, Arm, ForeArm, Hand]
            arm_info: Dict with shoulder_pos, elbow_pos, hand_pos
            side: "left" or "right"
        """
        shoulder_bone = self.get_bone(bone_names[0])
        upper_arm_bone = self.get_bone(bone_names[1])
        forearm_bone = self.get_bone(bone_names[2])
        hand_bone = self.get_bone(bone_names[3])

        if not all([shoulder_bone, upper_arm_bone, forearm_bone, hand_bone]):
            return

        shoulder_pos = arm_info["shoulder_pos"]
        elbow_pos = arm_info["elbow_pos"]
        hand_pos = arm_info["hand_pos"]
        arm_length = arm_info["arm_length"]

        # Keep shoulder head in place (connected to spine), adjust tail
        shoulder_direction = (shoulder_pos - shoulder_bone.head)
        if np.linalg.norm(shoulder_direction) > 0.001:
            shoulder_direction = shoulder_direction / np.linalg.norm(shoulder_direction)
            shoulder_bone.tail = shoulder_bone.head + shoulder_direction * shoulder_bone.length

        # Upper arm: from shoulder tail to elbow
        upper_arm_bone.head = shoulder_bone.tail.copy()
        upper_arm_direction = elbow_pos - upper_arm_bone.head
        upper_arm_length = arm_length * 0.35  # Upper arm is about 35% of total arm
        if np.linalg.norm(upper_arm_direction) > 0.001:
            upper_arm_direction = upper_arm_direction / np.linalg.norm(upper_arm_direction)
        upper_arm_bone.tail = upper_arm_bone.head + upper_arm_direction * upper_arm_length

        # Forearm: from elbow to wrist
        forearm_bone.head = upper_arm_bone.tail.copy()
        forearm_direction = hand_pos - forearm_bone.head
        forearm_length = arm_length * 0.35  # Forearm is about 35% of total arm
        if np.linalg.norm(forearm_direction) > 0.001:
            forearm_direction = forearm_direction / np.linalg.norm(forearm_direction)
        forearm_bone.tail = forearm_bone.head + forearm_direction * forearm_length

        # Hand: from wrist extending in same direction
        hand_bone.head = forearm_bone.tail.copy()
        hand_length = arm_length * 0.15  # Hand is about 15% of arm length
        hand_bone.tail = hand_bone.head + forearm_direction * hand_length

        # Update finger bones if they exist
        self._adjust_finger_bones(hand_bone, forearm_direction, side)

    def _adjust_finger_bones(self, hand_bone: Bone, arm_direction: np.ndarray, side: str) -> None:
        """
        Adjust finger bone positions to follow the hand direction.

        Args:
            hand_bone: The hand bone
            arm_direction: Direction the arm is pointing
            side: "left" or "right"
        """
        prefix = "Left" if side == "left" else "Right"
        finger_names = ["Thumb", "Index", "Middle", "Ring", "Pinky"]

        # Calculate a perpendicular direction for thumb spread
        up = np.array([0, 1, 0])
        side_dir = np.cross(arm_direction, up)
        if np.linalg.norm(side_dir) > 0.001:
            side_dir = side_dir / np.linalg.norm(side_dir)
        else:
            side_dir = np.array([0, 0, 1])

        for i, finger in enumerate(finger_names):
            # Get finger bones (3 segments per finger)
            bone1 = self.get_bone(f"{prefix}Hand{finger}1")
            bone2 = self.get_bone(f"{prefix}Hand{finger}2")
            bone3 = self.get_bone(f"{prefix}Hand{finger}3")

            if not all([bone1, bone2, bone3]):
                continue

            # Calculate finger direction (spread slightly from arm direction)
            spread_angle = (i - 2) * 0.1  # -0.2 to +0.2 radians spread
            finger_dir = arm_direction + side_dir * spread_angle
            if np.linalg.norm(finger_dir) > 0.001:
                finger_dir = finger_dir / np.linalg.norm(finger_dir)

            # Thumb points more to the side
            if finger == "Thumb":
                thumb_dir = side_dir * (1 if side == "left" else -1) + arm_direction * 0.5
                if np.linalg.norm(thumb_dir) > 0.001:
                    finger_dir = thumb_dir / np.linalg.norm(thumb_dir)

            # Position finger bones starting from hand tail
            base_pos = hand_bone.tail.copy()

            # Finger segment lengths (proportional to hand)
            hand_length = np.linalg.norm(hand_bone.tail - hand_bone.head)
            seg1_len = hand_length * 0.5
            seg2_len = hand_length * 0.35
            seg3_len = hand_length * 0.25

            # First segment
            bone1.head = base_pos.copy()
            bone1.tail = bone1.head + finger_dir * seg1_len

            # Second segment
            bone2.head = bone1.tail.copy()
            bone2.tail = bone2.head + finger_dir * seg2_len

            # Third segment
            bone3.head = bone2.tail.copy()
            bone3.tail = bone3.head + finger_dir * seg3_len


def create_bone(
    name: str,
    head: tuple[float, float, float],
    tail: tuple[float, float, float],
    parent: Optional[Bone] = None,
    connected: bool = False,
    deform: bool = True,
) -> Bone:
    """
    Create a new bone.

    Args:
        name: Bone name
        head: Head position (x, y, z)
        tail: Tail position (x, y, z)
        parent: Parent bone (optional)
        connected: Whether bone connects to parent's tail
        deform: Whether bone deforms mesh

    Returns:
        New Bone instance
    """
    bone = Bone(
        name=name,
        head=np.array(head),
        tail=np.array(tail),
        connected=connected,
        deform=deform,
    )
    if parent:
        parent.add_child(bone)
    return bone


def create_skeleton_from_template(
    template: dict,
    character_type: CharacterType,
) -> Skeleton:
    """
    Create a skeleton from a template dictionary.

    Args:
        template: Template with bone definitions
        character_type: Character type

    Returns:
        Skeleton instance
    """
    bones_by_name: dict[str, Bone] = {}
    root_bone = None

    # First pass: create all bones
    for bone_def in template["bones"]:
        bone = Bone(
            name=bone_def["name"],
            head=np.array(bone_def["head"]),
            tail=np.array(bone_def["tail"]),
            connected=bone_def.get("connected", False),
            deform=bone_def.get("deform", True),
        )
        bones_by_name[bone.name] = bone

        if bone_def.get("parent") is None:
            root_bone = bone

    # Second pass: set up parent-child relationships
    for bone_def in template["bones"]:
        bone = bones_by_name[bone_def["name"]]
        parent_name = bone_def.get("parent")
        if parent_name and parent_name in bones_by_name:
            parent = bones_by_name[parent_name]
            parent.add_child(bone)

    if root_bone is None:
        raise ValueError("No root bone found in template")

    return Skeleton(root=root_bone, bones=bones_by_name, character_type=character_type)
