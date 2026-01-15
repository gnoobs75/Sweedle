/**
 * GLBViewer Component - 3D model viewer using React Three Fiber
 */

import { Suspense, useEffect, useRef, useMemo, Component, ErrorInfo, ReactNode, useCallback } from 'react';
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
import { useAnimationStore } from '../../stores/animationStore';
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
 * Animation mixer hook for use inside Model component
 */
function useModelAnimationMixer(scene: THREE.Object3D | null) {
  const mixerRef = useRef<THREE.AnimationMixer | null>(null);
  const actionsRef = useRef<Map<string, THREE.AnimationAction>>(new Map());
  const lastTimeRef = useRef<number>(0);

  const {
    clips,
    activeClipId,
    isPlaying,
    setCurrentTime,
  } = useAnimationStore();

  // Create mixer when scene is available
  useEffect(() => {
    if (!scene) {
      mixerRef.current = null;
      actionsRef.current.clear();
      return;
    }

    const mixer = new THREE.AnimationMixer(scene);
    mixerRef.current = mixer;
    actionsRef.current.clear();

    return () => {
      mixer.stopAllAction();
      actionsRef.current.clear();
    };
  }, [scene]);

  // Convert backend keyframe data to Three.js AnimationClip
  const createAnimationClip = useCallback((clip: typeof clips[0]) => {
    if (!clip.keyframe_data) return null;

    const keyframeData = clip.keyframe_data as {
      tracks: Array<{
        bone_name: string;
        property: 'rotation' | 'position' | 'scale';
        times: number[];
        values: number[];
        interpolation?: string;
      }>;
      duration: number;
    };

    const tracks: THREE.KeyframeTrack[] = [];

    for (const track of keyframeData.tracks) {
      const targetName = track.bone_name;
      let trackName: string;
      let TrackClass: typeof THREE.KeyframeTrack;

      switch (track.property) {
        case 'rotation':
          trackName = `${targetName}.quaternion`;
          TrackClass = THREE.QuaternionKeyframeTrack;
          break;
        case 'position':
          trackName = `${targetName}.position`;
          TrackClass = THREE.VectorKeyframeTrack;
          break;
        case 'scale':
          trackName = `${targetName}.scale`;
          TrackClass = THREE.VectorKeyframeTrack;
          break;
        default:
          continue;
      }

      let interpolation: THREE.InterpolationModes = THREE.InterpolateLinear;
      if (track.interpolation === 'STEP') {
        interpolation = THREE.InterpolateDiscrete;
      } else if (track.interpolation === 'CATMULLROM') {
        interpolation = THREE.InterpolateSmooth;
      }

      tracks.push(new TrackClass(trackName, track.times, track.values, interpolation));
    }

    return new THREE.AnimationClip(clip.name, keyframeData.duration, tracks);
  }, []);

  // Load animation clips
  useEffect(() => {
    if (!mixerRef.current) return;

    clips.forEach((clip) => {
      if (actionsRef.current.has(clip.id)) return;

      const animClip = createAnimationClip(clip);
      if (!animClip) return;

      const action = mixerRef.current!.clipAction(animClip);

      const loopMode = clip.loop_mode || 'loop';
      switch (loopMode) {
        case 'loop':
          action.setLoop(THREE.LoopRepeat, Infinity);
          break;
        case 'once':
          action.setLoop(THREE.LoopOnce, 1);
          action.clampWhenFinished = true;
          break;
        case 'pingpong':
          action.setLoop(THREE.LoopPingPong, Infinity);
          break;
      }

      actionsRef.current.set(clip.id, action);
    });
  }, [clips, createAnimationClip]);

  // Handle active clip changes
  useEffect(() => {
    if (!mixerRef.current || !activeClipId) return;

    // Stop all actions first
    actionsRef.current.forEach((action, id) => {
      if (id !== activeClipId) {
        action.stop();
      }
    });

    const action = actionsRef.current.get(activeClipId);
    if (!action) return;

    if (isPlaying) {
      action.reset();
      action.play();
    } else {
      action.paused = true;
    }
  }, [activeClipId, isPlaying]);

  // Update mixer each frame
  useFrame((_, delta) => {
    if (!mixerRef.current) return;

    if (isPlaying) {
      mixerRef.current.update(delta);

      // Update current time in store (throttled)
      const now = Date.now();
      if (now - lastTimeRef.current > 50) {
        const action = activeClipId ? actionsRef.current.get(activeClipId) : null;
        if (action) {
          setCurrentTime(action.time);
        }
        lastTimeRef.current = now;
      }
    }
  });

  return mixerRef.current;
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
  const { isPlaying } = useAnimationStore();
  const groupRef = useRef<THREE.Group>(null);

  // Load the GLB model
  const { scene } = useGLTF(url, true, true, (loader) => {
    loader.manager.onError = (url) => {
      onError?.(new Error(`Failed to load: ${url}`));
    };
  });

  // Clone the scene to avoid mutation issues
  const clonedScene = useMemo(() => scene.clone(), [scene]);

  // Set up animation mixer for this model
  useModelAnimationMixer(clonedScene);

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

  // Auto-rotate (disabled when animation is playing)
  useFrame((_, delta) => {
    if (settings.autoRotate && !isPlaying && groupRef.current) {
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
 * Dusk atmosphere background - gradient from floor to ceiling
 */
function DuskAtmosphere() {
  const meshRef = useRef<THREE.Mesh>(null);

  // Create gradient shader for smooth floor-wall-ceiling transitions
  const gradientShader = useMemo(() => ({
    uniforms: {
      topColor: { value: new THREE.Color('#3d4466') },     // Ceiling - dusky blue
      horizonColor: { value: new THREE.Color('#4a4a6a') }, // Horizon - lighter purple
      bottomColor: { value: new THREE.Color('#2a2a3e') },  // Floor - darker base
      offset: { value: 0 },
      exponent: { value: 0.6 },
    },
    vertexShader: `
      varying vec3 vWorldPosition;
      void main() {
        vec4 worldPosition = modelMatrix * vec4(position, 1.0);
        vWorldPosition = worldPosition.xyz;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: `
      uniform vec3 topColor;
      uniform vec3 horizonColor;
      uniform vec3 bottomColor;
      uniform float offset;
      uniform float exponent;
      varying vec3 vWorldPosition;

      void main() {
        float h = normalize(vWorldPosition + offset).y;

        // Smooth transitions using smoothstep
        float horizonBlend = smoothstep(-0.2, 0.3, h);
        float topBlend = smoothstep(0.2, 0.8, h);

        // Blend from bottom -> horizon -> top
        vec3 color = mix(bottomColor, horizonColor, horizonBlend);
        color = mix(color, topColor, topBlend);

        gl_FragColor = vec4(color, 1.0);
      }
    `,
  }), []);

  return (
    <mesh ref={meshRef} scale={[100, 100, 100]}>
      <sphereGeometry args={[1, 32, 32]} />
      <shaderMaterial
        args={[gradientShader]}
        side={THREE.BackSide}
        depthWrite={false}
      />
    </mesh>
  );
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
  const { scene } = useThree();

  // Add fog for smooth distance falloff
  useEffect(() => {
    scene.fog = new THREE.FogExp2('#2e2e48', 0.04);
    return () => {
      scene.fog = null;
    };
  }, [scene]);

  return (
    <>
      {/* Dusk atmosphere background */}
      <DuskAtmosphere />

      {/* Lighting - dusk ambiance */}
      <ambientLight intensity={0.6} color="#9090b0" />
      <hemisphereLight
        args={['#6070a0', '#303040', 0.5]}
        position={[0, 10, 0]}
      />
      <directionalLight
        position={[10, 10, 5]}
        intensity={0.8}
        color="#d0c0a0"
        castShadow
        shadow-mapSize={[2048, 2048]}
      />
      <directionalLight
        position={[-10, -10, -5]}
        intensity={0.3}
        color="#8090b0"
      />

      {/* Environment map for reflections */}
      <Environment
        preset={settings.environmentMap as any}
        background={false}
      />

      {/* Grid - more visible in dusk lighting */}
      {settings.showGrid && (
        <Grid
          args={[20, 20]}
          cellSize={0.5}
          cellThickness={0.6}
          cellColor="#505070"
          sectionSize={2}
          sectionThickness={1.2}
          sectionColor="#707090"
          fadeDistance={25}
          fadeStrength={1.5}
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
