/**
 * LandmarkVisualization - Renders draggable landmark markers in the 3D viewer
 *
 * Shows large, easy-to-grab spheres for each landmark position.
 * Users can drag these to position the skeleton landmarks.
 */

import { useRef, useState, useCallback, useEffect } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { TransformControls, Html } from '@react-three/drei';
import * as THREE from 'three';

interface LandmarkData {
  name: string;
  position: [number, number, number];
  color: string;
  description?: string;
}

interface LandmarkVisualizationProps {
  landmarks: Record<string, [number, number, number]>;
  landmarkInfo: Array<{ name: string; color: string; description?: string }>;
  selectedLandmark: string | null;
  onLandmarkSelect: (name: string | null) => void;
  onLandmarkMove: (name: string, position: [number, number, number]) => void;
  visible: boolean;
}

/**
 * Individual landmark marker
 */
function LandmarkMarker({
  name,
  position,
  color,
  isSelected,
  onSelect,
  onMove,
}: {
  name: string;
  position: [number, number, number];
  color: string;
  isSelected: boolean;
  onSelect: () => void;
  onMove: (pos: [number, number, number]) => void;
}) {
  const [meshObject, setMeshObject] = useState<THREE.Mesh | null>(null);
  const [isHovered, setIsHovered] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  // Update mesh position when prop changes (not during drag)
  useEffect(() => {
    if (meshObject && !isDragging) {
      meshObject.position.set(...position);
    }
  }, [position, isDragging, meshObject]);

  const handleDrag = useCallback(() => {
    if (meshObject) {
      const pos = meshObject.position;
      onMove([pos.x, pos.y, pos.z]);
    }
  }, [meshObject, onMove]);

  // Pulsing animation for selected marker
  useFrame((state) => {
    if (meshObject && isSelected) {
      const scale = 1 + Math.sin(state.clock.elapsedTime * 3) * 0.15;
      meshObject.scale.setScalar(scale);
    } else if (meshObject) {
      meshObject.scale.setScalar(1);
    }
  });

  const markerSize = isSelected ? 0.06 : isHovered ? 0.055 : 0.05;
  const emissiveIntensity = isSelected ? 0.8 : isHovered ? 0.5 : 0.3;

  return (
    <>
      {/* Main marker sphere */}
      <mesh
        ref={setMeshObject}
        position={position}
        onClick={(e) => {
          e.stopPropagation();
          onSelect();
        }}
        onPointerOver={(e) => {
          e.stopPropagation();
          setIsHovered(true);
          document.body.style.cursor = 'pointer';
        }}
        onPointerOut={() => {
          setIsHovered(false);
          document.body.style.cursor = 'auto';
        }}
      >
        <sphereGeometry args={[markerSize, 24, 24]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={emissiveIntensity}
          transparent
          opacity={0.9}
        />
      </mesh>

      {/* Label */}
      {(isSelected || isHovered) && (
        <Html position={position} center style={{ pointerEvents: 'none' }}>
          <div
            className="px-2 py-1 bg-black/80 text-white text-xs rounded whitespace-nowrap"
            style={{
              transform: 'translateY(-40px)',
              borderColor: color,
              borderWidth: '1px',
            }}
          >
            {name}
          </div>
        </Html>
      )}

      {/* Transform controls for selected marker */}
      {isSelected && meshObject && (
        <TransformControls
          object={meshObject}
          mode="translate"
          size={0.8}
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
 * Connection lines between related landmarks
 */
function LandmarkConnections({
  landmarks,
}: {
  landmarks: Record<string, [number, number, number]>;
}) {
  // Define connections for quadruped
  const connections: Array<[string, string]> = [
    // Body
    ['Hips', 'Chest'],
    // Head
    ['Chest', 'Head'],
    // Tail
    ['Hips', 'TailTip'],
    // Front legs
    ['Chest', 'FrontLeftPaw'],
    ['Chest', 'FrontRightPaw'],
    // Back legs
    ['Hips', 'BackLeftPaw'],
    ['Hips', 'BackRightPaw'],
  ];

  const lines = connections
    .filter(([a, b]) => landmarks[a] && landmarks[b])
    .map(([a, b]) => ({
      start: new THREE.Vector3(...landmarks[a]),
      end: new THREE.Vector3(...landmarks[b]),
    }));

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
          <lineBasicMaterial color="#8855ff" transparent opacity={0.5} linewidth={2} />
        </line>
      ))}
    </group>
  );
}

/**
 * Main landmark visualization component
 */
export function LandmarkVisualization({
  landmarks,
  landmarkInfo,
  selectedLandmark,
  onLandmarkSelect,
  onLandmarkMove,
  visible,
}: LandmarkVisualizationProps) {
  if (!visible || Object.keys(landmarks).length === 0) {
    return null;
  }

  // Get color for a landmark
  const getColor = (name: string): string => {
    const info = landmarkInfo.find((l) => l.name === name);
    return info?.color || '#ffffff';
  };

  return (
    <group name="landmark-visualization">
      {/* Connection lines (behind markers) */}
      <LandmarkConnections landmarks={landmarks} />

      {/* Landmark markers */}
      {Object.entries(landmarks).map(([name, position]) => (
        <LandmarkMarker
          key={name}
          name={name}
          position={position}
          color={getColor(name)}
          isSelected={selectedLandmark === name}
          onSelect={() => onLandmarkSelect(selectedLandmark === name ? null : name)}
          onMove={(pos) => onLandmarkMove(name, pos)}
        />
      ))}
    </group>
  );
}
