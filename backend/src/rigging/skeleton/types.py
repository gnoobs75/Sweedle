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
