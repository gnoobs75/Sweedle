/**
 * GLBViewer Component - 3D model viewer using React Three Fiber
 */

import { Suspense, useEffect, useRef, useMemo, Component, ErrorInfo, ReactNode } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import {
  OrbitControls,
  Environment,
  useGLTF,
  Grid,
  GizmoHelper,
  GizmoViewport,
  Center,
  Bounds,
  useBounds,
  Html,
  useProgress,
} from '@react-three/drei';
import * as THREE from 'three';
import { useViewerStore } from '../../stores/viewerStore';
import { useRiggingStore } from '../../stores/riggingStore';
import { Spinner } from '../ui/Spinner';
import { SkeletonVisualization } from './SkeletonVisualization';

interface GLBViewerProps {
  url: string | null;
  onLoad?: (info: ModelInfo) => void;
  onError?: (error: Error) => void;
}

interface ModelInfo {
  vertexCount: number;
  faceCount: number;
  materials: string[];
  hasTextures: boolean;
  boundingBox: THREE.Box3;
}

/**
 * Loading indicator inside the canvas
 */
function Loader() {
  const { progress } = useProgress();
  return (
    <Html center>
      <div className="flex flex-col items-center gap-2">
        <Spinner size="lg" variant="primary" />
        <p className="text-sm text-text-secondary">
          Loading... {progress.toFixed(0)}%
        </p>
      </div>
    </Html>
  );
}

/**
 * Model component that loads and displays GLB
 */
function Model({
  url,
  onLoad,
  onError,
}: {
  url: string;
  onLoad?: (info: ModelInfo) => void;
  onError?: (error: Error) => void;
}) {
  const { settings } = useViewerStore();
  const groupRef = useRef<THREE.Group>(null);

  // Load the GLB model
  const { scene } = useGLTF(url, true, true, (loader) => {
    loader.manager.onError = (url) => {
      onError?.(new Error(`Failed to load: ${url}`));
    };
  });

  // Clone the scene to avoid mutation issues
  const clonedScene = useMemo(() => scene.clone(), [scene]);

  // Analyze model and report info
  useEffect(() => {
    if (!clonedScene) return;

    let vertexCount = 0;
    let faceCount = 0;
    const materials = new Set<string>();
    let hasTextures = false;

    clonedScene.traverse((child) => {
      if (child instanceof THREE.Mesh) {
        const geometry = child.geometry;
        if (geometry) {
          vertexCount += geometry.attributes.position?.count || 0;
          if (geometry.index) {
            faceCount += geometry.index.count / 3;
          } else {
            faceCount += (geometry.attributes.position?.count || 0) / 3;
          }
        }

        // Check materials
        const meshMaterials = Array.isArray(child.material)
          ? child.material
          : [child.material];

        meshMaterials.forEach((mat) => {
          if (mat) {
            materials.add(mat.name || 'Unnamed Material');
            if (mat instanceof THREE.MeshStandardMaterial) {
              if (mat.map || mat.normalMap || mat.roughnessMap || mat.metalnessMap) {
                hasTextures = true;
              }
            }
          }
        });
      }
    });

    const boundingBox = new THREE.Box3().setFromObject(clonedScene);

    onLoad?.({
      vertexCount,
      faceCount: Math.round(faceCount),
      materials: Array.from(materials),
      hasTextures,
      boundingBox,
    });
  }, [clonedScene, onLoad]);

  // Apply wireframe mode
  useEffect(() => {
    clonedScene.traverse((child) => {
      if (child instanceof THREE.Mesh) {
        const materials = Array.isArray(child.material)
          ? child.material
          : [child.material];
        materials.forEach((mat) => {
          if (mat) {
            mat.wireframe = settings.showWireframe;
          }
        });
      }
    });
  }, [clonedScene, settings.showWireframe]);

  // Auto-rotate
  useFrame((_, delta) => {
    if (settings.autoRotate && groupRef.current) {
      groupRef.current.rotation.y += delta * 0.5;
    }
  });

  return (
    <group ref={groupRef}>
      <primitive object={clonedScene} />
    </group>
  );
}

/**
 * Bounds handler for auto-fitting camera
 */
function BoundsHandler({ children }: { children: React.ReactNode }) {
  const bounds = useBounds();

  useEffect(() => {
    bounds.refresh().clip().fit();
  }, [bounds]);

  return <>{children}</>;
}

/**
 * Scene setup with lights and environment
 */
function Scene({
  url,
  onLoad,
  onError,
}: {
  url: string;
  onLoad?: (info: ModelInfo) => void;
  onError?: (error: Error) => void;
}) {
  const { settings } = useViewerStore();
  const { skeletonData, showSkeleton, selectedBone, setSelectedBone } = useRiggingStore();

  return (
    <>
      {/* Lighting */}
      <ambientLight intensity={0.4} />
      <directionalLight
        position={[10, 10, 5]}
        intensity={1}
        castShadow
        shadow-mapSize={[2048, 2048]}
      />
      <directionalLight position={[-10, -10, -5]} intensity={0.3} />

      {/* Environment map for reflections */}
      <Environment
        preset={settings.environmentMap as any}
        background={false}
      />

      {/* Grid */}
      {settings.showGrid && (
        <Grid
          args={[20, 20]}
          cellSize={0.5}
          cellThickness={0.5}
          cellColor="#404060"
          sectionSize={2}
          sectionThickness={1}
          sectionColor="#606080"
          fadeDistance={30}
          fadeStrength={1}
          followCamera={false}
          infiniteGrid
        />
      )}

      {/* Model with auto-centering and bounds fitting */}
      <Bounds fit clip observe margin={1.2}>
        <BoundsHandler>
          <Center>
            <Model url={url} onLoad={onLoad} onError={onError} />
            {/* Skeleton overlay */}
            {skeletonData && (
              <SkeletonVisualization
                skeleton={skeletonData}
                visible={showSkeleton}
                selectedBone={selectedBone}
                onBoneSelect={setSelectedBone}
              />
            )}
          </Center>
        </BoundsHandler>
      </Bounds>

      {/* Axes helper */}
      {settings.showAxes && (
        <GizmoHelper alignment="bottom-right" margin={[80, 80]}>
          <GizmoViewport
            axisColors={['#ff4060', '#40ff60', '#4060ff']}
            labelColor="white"
          />
        </GizmoHelper>
      )}
    </>
  );
}

/**
 * Error Boundary for Canvas crashes
 */
class CanvasErrorBoundary extends Component<
  { children: ReactNode; onError?: (error: Error) => void },
  { hasError: boolean; error: Error | null }
> {
  constructor(props: { children: ReactNode; onError?: (error: Error) => void }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Canvas error:', error, errorInfo);
    this.props.onError?.(error);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex items-center justify-center h-full bg-surface p-4">
          <div className="text-center">
            <p className="text-error mb-2">Failed to render 3D view</p>
            <p className="text-text-secondary text-sm">{this.state.error?.message}</p>
            <button
              className="mt-4 px-4 py-2 bg-primary text-white rounded"
              onClick={() => this.setState({ hasError: false, error: null })}
            >
              Retry
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

/**
 * Main GLB Viewer component
 */
export function GLBViewer({ url, onLoad, onError }: GLBViewerProps) {
  const { settings, setLoading, setLoadError, setModelInfo } = useViewerStore();

  const handleLoad = (info: ModelInfo) => {
    setLoading(false);
    setModelInfo({
      vertexCount: info.vertexCount,
      faceCount: info.faceCount,
      materials: info.materials,
      hasTextures: info.hasTextures,
    });
    onLoad?.(info);
  };

  const handleError = (error: Error) => {
    console.error('Model load error:', error);
    setLoading(false);
    setLoadError(error.message);
    onError?.(error);
  };

  if (!url) {
    return null;
  }

  // Log the URL for debugging
  console.log('Loading model from URL:', url);

  return (
    <CanvasErrorBoundary onError={handleError}>
      <Canvas
        shadows
        camera={{ position: [3, 3, 3], fov: 50 }}
        gl={{
          antialias: true,
          toneMapping: THREE.ACESFilmicToneMapping,
          toneMappingExposure: settings.exposure,
          powerPreference: 'high-performance',
          failIfMajorPerformanceCaveat: false,
        }}
        style={{ background: settings.backgroundColor }}
        onCreated={({ gl }) => {
          console.log('WebGL context created:', gl.getContext().getParameter(gl.getContext().VERSION));
        }}
      >
        <Suspense fallback={<Loader />}>
          <Scene url={url} onLoad={handleLoad} onError={handleError} />
        </Suspense>

        <OrbitControls
          makeDefault
          enableDamping
          dampingFactor={0.05}
          minDistance={0.5}
          maxDistance={50}
          enablePan
          panSpeed={0.5}
          rotateSpeed={0.5}
          zoomSpeed={0.5}
        />
      </Canvas>
    </CanvasErrorBoundary>
  );
}

// Preload helper
export function preloadModel(url: string) {
  useGLTF.preload(url);
}
