/**
 * SkeletonVisualization - Renders skeleton bones in the 3D viewer.
 *
 * Creates named groups for each bone that AnimationMixer can target.
 * Supports drag mode for interactive bone positioning.
 */

import { useMemo, useRef, useEffect, useImperativeHandle, forwardRef, useCallback, useState } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { TransformControls } from '@react-three/drei';
import * as THREE from 'three';
import type { BoneData, SkeletonData, BoneEdit } from '../../stores/riggingStore';

interface SkeletonVisualizationProps {
  skeleton: SkeletonData;
  visible: boolean;
  selectedBone: string | null;
  onBoneSelect?: (boneName: string | null) => void;
  floatingBones?: string[];
  editedBones?: Map<string, BoneEdit>;
  dragMode?: boolean;
  onBonePositionChange?: (boneName: string, head: [number, number, number], tail: [number, number, number]) => void;
}

interface BoneVisualProps {
  bone: BoneData;
  isSelected: boolean;
  isRoot: boolean;
  isFloating: boolean;
  onClick?: () => void;
}

/**
 * Colors for different bone states
 */
const BONE_COLORS = {
  default: '#4080ff',     // Blue for normal bones
  selected: '#ffcc00',    // Yellow for selected
  root: '#ff4080',        // Pink for root bone
  joint: '#40ff80',       // Green for joints
  floating: '#ff3030',    // Red for floating bones (outside mesh)
  floatingJoint: '#ff6060', // Light red for floating joints
};

/**
 * Individual bone visualization as a cylinder/capsule
 * Can optionally track an animated Object3D by name
 */
function BoneVisual({ bone, isSelected, isRoot, isFloating, onClick }: BoneVisualProps) {
  const groupRef = useRef<THREE.Group>(null);
  const meshRef = useRef<THREE.Mesh>(null);
  const jointRef = useRef<THREE.Mesh>(null);
  const { scene } = useThree();

  // Calculate initial bone geometry
  const initialGeometry = useMemo(() => {
    const head = new THREE.Vector3(...bone.headPosition);
    const tail = new THREE.Vector3(...bone.tailPosition);
    const midpoint = head.clone().add(tail).multiplyScalar(0.5);
    const direction = tail.clone().sub(head).normalize();
    const quaternion = new THREE.Quaternion();
    const up = new THREE.Vector3(0, 1, 0);
    quaternion.setFromUnitVectors(up, direction);
    const length = head.distanceTo(tail);
    return { head, tail, midpoint, quaternion, length };
  }, [bone.headPosition, bone.tailPosition]);

  // Track animated bone and update visual position
  useFrame((state) => {
    // Find animated bone object in scene by name
    const animatedBone = scene.getObjectByName(bone.name);

    if (animatedBone && groupRef.current) {
      // Get world position of animated bone
      const worldPos = new THREE.Vector3();
      animatedBone.getWorldPosition(worldPos);

      // Get world quaternion
      const worldQuat = new THREE.Quaternion();
      animatedBone.getWorldQuaternion(worldQuat);

      // Apply small offset based on animation rotation to bone visual
      // This creates visible movement even for rotation-only animations
      if (meshRef.current) {
        // Apply rotation from animated bone to the visual
        const baseQuat = initialGeometry.quaternion.clone();
        meshRef.current.quaternion.copy(baseQuat).premultiply(worldQuat);
      }
    }

    // Pulsing animation for selected bone
    if (isSelected && meshRef.current) {
      const scale = 1 + Math.sin(state.clock.elapsedTime * 4) * 0.1;
      meshRef.current.scale.set(scale, 1, scale);
    }
  });

  // Priority: selected > floating > root > default
  const color = isSelected
    ? BONE_COLORS.selected
    : isFloating
    ? BONE_COLORS.floating
    : isRoot
    ? BONE_COLORS.root
    : BONE_COLORS.default;

  const jointColor = isSelected
    ? BONE_COLORS.selected
    : isFloating
    ? BONE_COLORS.floatingJoint
    : BONE_COLORS.joint;

  // Don't render if bone has zero length
  if (initialGeometry.length < 0.001) {
    return null;
  }

  return (
    <group ref={groupRef} name={`visual-${bone.name}`}>
      {/* Bone shaft (cylinder) */}
      <mesh
        ref={meshRef}
        position={initialGeometry.midpoint}
        quaternion={initialGeometry.quaternion}
        onClick={(e) => {
          e.stopPropagation();
          onClick?.();
        }}
      >
        <cylinderGeometry args={[0.015, 0.008, initialGeometry.length, 8]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={isSelected ? 0.5 : 0.2}
          transparent
          opacity={0.8}
        />
      </mesh>

      {/* Joint sphere at head position */}
      <mesh
        ref={jointRef}
        position={bone.headPosition}
        onClick={(e) => {
          e.stopPropagation();
          onClick?.();
        }}
      >
        <sphereGeometry args={[0.02, 16, 16]} />
        <meshStandardMaterial
          color={jointColor}
          emissive={jointColor}
          emissiveIntensity={0.3}
        />
      </mesh>
    </group>
  );
}

/**
 * Draggable bone handle using TransformControls
 */
function BoneDragHandle({
  position,
  label,
  color,
  onDrag,
}: {
  position: [number, number, number];
  label: string;
  color: string;
  onDrag: (newPosition: THREE.Vector3) => void;
}) {
  const [meshObject, setMeshObject] = useState<THREE.Mesh | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  // Update mesh position when prop changes (not during drag)
  useEffect(() => {
    if (meshObject && !isDragging) {
      meshObject.position.set(...position);
    }
  }, [position, isDragging, meshObject]);

  const handleDrag = useCallback(() => {
    if (meshObject) {
      onDrag(meshObject.position.clone());
    }
  }, [onDrag, meshObject]);

  return (
    <>
      <mesh ref={setMeshObject} position={position}>
        <sphereGeometry args={[0.035, 16, 16]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={isDragging ? 0.8 : 0.4}
        />
      </mesh>
      {meshObject && (
        <TransformControls
          object={meshObject}
          mode="translate"
          size={0.6}
          showX
          showY
          showZ
          onMouseDown={() => setIsDragging(true)}
          onMouseUp={() => setIsDragging(false)}
          onChange={handleDrag}
        />
      )}
    </>
  );
}

/**
 * Selected bone drag overlay with head and tail handles
 */
function BoneDragOverlay({
  bone,
  editedBones,
  onPositionChange,
}: {
  bone: BoneData;
  editedBones?: Map<string, BoneEdit>;
  onPositionChange: (boneName: string, head: [number, number, number], tail: [number, number, number]) => void;
}) {
  // Get current positions (edited or original)
  const edit = editedBones?.get(bone.name);
  const headPos = edit?.headPosition || bone.headPosition;
  const tailPos = edit?.tailPosition || bone.tailPosition;

  const handleHeadDrag = useCallback(
    (pos: THREE.Vector3) => {
      onPositionChange(bone.name, [pos.x, pos.y, pos.z], tailPos);
    },
    [bone.name, tailPos, onPositionChange]
  );

  const handleTailDrag = useCallback(
    (pos: THREE.Vector3) => {
      onPositionChange(bone.name, headPos, [pos.x, pos.y, pos.z]);
    },
    [bone.name, headPos, onPositionChange]
  );

  return (
    <group>
      {/* Connection line */}
      <line>
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            count={2}
            array={new Float32Array([...headPos, ...tailPos])}
            itemSize={3}
          />
        </bufferGeometry>
        <lineBasicMaterial color="#ffffff" linewidth={2} />
      </line>

      {/* Head handle (green) */}
      <BoneDragHandle
        position={headPos}
        label="Head"
        color="#00ff00"
        onDrag={handleHeadDrag}
      />

      {/* Tail handle (orange) */}
      <BoneDragHandle
        position={tailPos}
        label="Tail"
        color="#ff8800"
        onDrag={handleTailDrag}
      />
    </group>
  );
}

/**
 * Connection lines between parent and child bones
 */
function BoneConnections({ skeleton }: { skeleton: SkeletonData }) {
  const lines = useMemo(() => {
    const lineData: { start: THREE.Vector3; end: THREE.Vector3 }[] = [];

    skeleton.bones.forEach((bone) => {
      if (bone.parent) {
        const parentBone = skeleton.bones.find((b) => b.name === bone.parent);
        if (parentBone) {
          // Connect parent's tail to this bone's head
          lineData.push({
            start: new THREE.Vector3(...parentBone.tailPosition),
            end: new THREE.Vector3(...bone.headPosition),
          });
        }
      }
    });

    return lineData;
  }, [skeleton.bones]);

  return (
    <group>
      {lines.map((line, index) => (
        <line key={index}>
          <bufferGeometry>
            <bufferAttribute
              attach="attributes-position"
              count={2}
              array={new Float32Array([
                line.start.x, line.start.y, line.start.z,
                line.end.x, line.end.y, line.end.z,
              ])}
              itemSize={3}
            />
          </bufferGeometry>
          <lineBasicMaterial color="#606080" transparent opacity={0.5} />
        </line>
      ))}
    </group>
  );
}

/**
 * Bone labels (optional, for debugging)
 */
function BoneLabels({
  skeleton,
  showLabels = false,
}: {
  skeleton: SkeletonData;
  showLabels?: boolean;
}) {
  if (!showLabels) return null;

  return (
    <group>
      {skeleton.bones.map((bone) => (
        <group key={bone.name} position={bone.headPosition}>
          {/* Simple sprite label would go here */}
        </group>
      ))}
    </group>
  );
}

/**
 * Handle for imperative access to skeleton bones
 */
export interface SkeletonVisualizationHandle {
  getBoneGroup: (boneName: string) => THREE.Group | undefined;
  getAllBones: () => Map<string, THREE.Group>;
  getRootGroup: () => THREE.Group | null;
}

/**
 * Main skeleton visualization component
 *
 * Creates named THREE.Group objects for each bone that can be animated.
 */
export const SkeletonVisualization = forwardRef<SkeletonVisualizationHandle, SkeletonVisualizationProps>(
  function SkeletonVisualization({
    skeleton,
    visible,
    selectedBone,
    onBoneSelect,
    floatingBones,
    editedBones,
    dragMode,
    onBonePositionChange,
  }, ref) {
    const rootGroupRef = useRef<THREE.Group>(null);
    const boneGroupsRef = useRef<Map<string, THREE.Group>>(new Map());

    // Get selected bone data for drag overlay
    const selectedBoneData = useMemo(() => {
      if (!selectedBone) return null;
      return skeleton.bones.find((b) => b.name === selectedBone) || null;
    }, [selectedBone, skeleton.bones]);

    // Create bone hierarchy with named groups
    const boneHierarchy = useMemo(() => {
      if (!skeleton || skeleton.bones.length === 0) return null;

      const boneMap = new Map<string, BoneData>();
      skeleton.bones.forEach(bone => boneMap.set(bone.name, bone));

      // Create groups for each bone
      const groups = new Map<string, THREE.Group>();

      skeleton.bones.forEach(bone => {
        const group = new THREE.Group();
        group.name = bone.name;

        // Set initial position at bone head
        const head = new THREE.Vector3(...bone.headPosition);
        group.position.copy(head);

        groups.set(bone.name, group);
      });

      // Build parent-child relationships
      skeleton.bones.forEach(bone => {
        const group = groups.get(bone.name);
        if (!group) return;

        if (bone.parent) {
          const parentGroup = groups.get(bone.parent);
          if (parentGroup) {
            // Convert to local coordinates relative to parent
            const parentBone = boneMap.get(bone.parent);
            if (parentBone) {
              const parentHead = new THREE.Vector3(...parentBone.headPosition);
              const localPos = new THREE.Vector3(...bone.headPosition).sub(parentHead);
              group.position.copy(localPos);
            }
            parentGroup.add(group);
          }
        }
      });

      // Store refs
      boneGroupsRef.current = groups;

      // Find root bones (no parent)
      const rootBones: THREE.Group[] = [];
      skeleton.bones.forEach(bone => {
        if (!bone.parent) {
          const group = groups.get(bone.name);
          if (group) rootBones.push(group);
        }
      });

      return { groups, rootBones };
    }, [skeleton]);

    // Expose imperative handle for AnimationMixer
    useImperativeHandle(ref, () => ({
      getBoneGroup: (boneName: string) => boneGroupsRef.current.get(boneName),
      getAllBones: () => boneGroupsRef.current,
      getRootGroup: () => rootGroupRef.current,
    }), []);

    if (!visible || !skeleton || skeleton.bones.length === 0) {
      return null;
    }

    return (
      <group ref={rootGroupRef} name="skeleton-root">
        {/* Add bone hierarchy groups */}
        {boneHierarchy?.rootBones.map(rootBone => (
          <primitive key={rootBone.name} object={rootBone} />
        ))}

        {/* Render visual bone connections (behind bones) */}
        <BoneConnections skeleton={skeleton} />

        {/* Render visual bone meshes */}
        {skeleton.bones.map((bone) => (
          <BoneVisual
            key={bone.name}
            bone={bone}
            isSelected={selectedBone === bone.name}
            isRoot={bone.name === skeleton.rootBone}
            isFloating={floatingBones?.includes(bone.name) ?? false}
            onClick={() => onBoneSelect?.(bone.name)}
          />
        ))}

        {/* Optional labels */}
        <BoneLabels skeleton={skeleton} showLabels={false} />

        {/* Drag overlay when drag mode is enabled */}
        {dragMode && selectedBoneData && onBonePositionChange && (
          <BoneDragOverlay
            bone={selectedBoneData}
            editedBones={editedBones}
            onPositionChange={onBonePositionChange}
          />
        )}
      </group>
    );
  }
);

/**
 * Hook to compute skeleton bounding box for camera fitting
 */
export function useSkeletonBounds(skeleton: SkeletonData | null): THREE.Box3 | null {
  return useMemo(() => {
    if (!skeleton || skeleton.bones.length === 0) return null;

    const box = new THREE.Box3();
    skeleton.bones.forEach((bone) => {
      box.expandByPoint(new THREE.Vector3(...bone.headPosition));
      box.expandByPoint(new THREE.Vector3(...bone.tailPosition));
    });

    return box;
  }, [skeleton]);
}
