/**
 * SkeletonVisualization - Renders skeleton bones in the 3D viewer.
 */

import { useMemo, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import type { BoneData, SkeletonData } from '../../stores/riggingStore';

interface SkeletonVisualizationProps {
  skeleton: SkeletonData;
  visible: boolean;
  selectedBone: string | null;
  onBoneSelect?: (boneName: string | null) => void;
}

interface BoneVisualProps {
  bone: BoneData;
  isSelected: boolean;
  isRoot: boolean;
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
};

/**
 * Individual bone visualization as a cylinder/capsule
 */
function BoneVisual({ bone, isSelected, isRoot, onClick }: BoneVisualProps) {
  const meshRef = useRef<THREE.Mesh>(null);
  const jointRef = useRef<THREE.Mesh>(null);

  // Calculate bone geometry
  const { position, quaternion, length } = useMemo(() => {
    const head = new THREE.Vector3(...bone.headPosition);
    const tail = new THREE.Vector3(...bone.tailPosition);

    // Position at midpoint
    const midpoint = head.clone().add(tail).multiplyScalar(0.5);

    // Calculate rotation to align cylinder with bone direction
    const direction = tail.clone().sub(head).normalize();
    const quaternion = new THREE.Quaternion();

    // Default cylinder points up (Y-axis), so we need to rotate to match bone direction
    const up = new THREE.Vector3(0, 1, 0);
    quaternion.setFromUnitVectors(up, direction);

    // Length of the bone
    const length = head.distanceTo(tail);

    return { position: midpoint, quaternion, length };
  }, [bone.headPosition, bone.tailPosition]);

  // Pulsing animation for selected bone
  useFrame((state) => {
    if (isSelected && meshRef.current) {
      const scale = 1 + Math.sin(state.clock.elapsedTime * 4) * 0.1;
      meshRef.current.scale.set(scale, 1, scale);
    }
  });

  const color = isSelected ? BONE_COLORS.selected : isRoot ? BONE_COLORS.root : BONE_COLORS.default;
  const jointColor = isSelected ? BONE_COLORS.selected : BONE_COLORS.joint;

  // Don't render if bone has zero length
  if (length < 0.001) {
    return null;
  }

  return (
    <group>
      {/* Bone shaft (cylinder) */}
      <mesh
        ref={meshRef}
        position={position}
        quaternion={quaternion}
        onClick={(e) => {
          e.stopPropagation();
          onClick?.();
        }}
      >
        <cylinderGeometry args={[0.015, 0.008, length, 8]} />
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
 * Main skeleton visualization component
 */
export function SkeletonVisualization({
  skeleton,
  visible,
  selectedBone,
  onBoneSelect,
}: SkeletonVisualizationProps) {
  if (!visible || !skeleton || skeleton.bones.length === 0) {
    return null;
  }

  return (
    <group name="skeleton-visualization">
      {/* Render bone connections first (behind bones) */}
      <BoneConnections skeleton={skeleton} />

      {/* Render each bone */}
      {skeleton.bones.map((bone) => (
        <BoneVisual
          key={bone.name}
          bone={bone}
          isSelected={selectedBone === bone.name}
          isRoot={bone.name === skeleton.rootBone}
          onClick={() => onBoneSelect?.(bone.name)}
        />
      ))}

      {/* Optional labels */}
      <BoneLabels skeleton={skeleton} showLabels={false} />
    </group>
  );
}

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
