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
import * as SkeletonUtils from 'three/examples/jsm/utils/SkeletonUtils.js';
import { useViewerStore } from '../../stores/viewerStore';
import { useRiggingStore } from '../../stores/riggingStore';
import { useAnimationStore } from '../../stores/animationStore';
import { Spinner } from '../ui/Spinner';
import { SkeletonVisualization } from './SkeletonVisualization';
import { LandmarkVisualization } from './LandmarkVisualization';
import { findNearestPointOnMesh } from '../../utils/meshUtils';

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
 * Model component that loads and displays GLB with animation support
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
  const { settings, isSkinnedPreview } = useViewerStore();
  const { skeletonData } = useRiggingStore();
  const groupRef = useRef<THREE.Group>(null);
  const jsonMixerRef = useRef<THREE.AnimationMixer | null>(null);
  const jsonActionsRef = useRef<Map<string, THREE.AnimationAction>>(new Map());
  const boneGroupsRef = useRef<Map<string, THREE.Object3D>>(new Map());

  // Animation store
  const {
    clips,
    activeClipId,
    isPlaying,
    currentTime,
    setCurrentTime,
    setIsPlaying,
    // Embedded animation state
    activeEmbeddedName,
    setEmbeddedAnimations,
    clearEmbeddedAnimations,
  } = useAnimationStore();

  // Track seek
  const lastTimeRef = useRef<number>(0);

  // Load the GLB model (with animations if present)
  const gltf = useGLTF(url, true, true, (loader) => {
    loader.manager.onError = (errorUrl) => {
      onError?.(new Error(`Failed to load: ${errorUrl}`));
    };
  });

  const { scene, animations: embeddedAnimations } = gltf;

  // Clone the scene to avoid mutation issues
  // Use SkeletonUtils.clone for skinned meshes to preserve skeleton binding
  const clonedScene = useMemo(() => {
    let hasSkinnedMesh = false;
    scene.traverse((child) => {
      if (child instanceof THREE.SkinnedMesh) {
        hasSkinnedMesh = true;
      }
    });

    if (hasSkinnedMesh) {
      console.log('Scene has SkinnedMesh, using SkeletonUtils.clone()');
      return SkeletonUtils.clone(scene) as THREE.Group;
    } else {
      return scene.clone();
    }
  }, [scene]);

  // --- EMBEDDED ANIMATIONS ---
  // Fresh mixer + single action approach: destroy and recreate the mixer each time
  // the selected animation changes. This avoids all Three.js action caching issues.
  const embeddedMixerRef = useRef<THREE.AnimationMixer | null>(null);
  const embeddedActionRef = useRef<THREE.AnimationAction | null>(null);

  // Register available embedded animations in the store (no mixer work here)
  useEffect(() => {
    if (!isSkinnedPreview || !embeddedAnimations?.length) {
      if (!isSkinnedPreview) {
        clearEmbeddedAnimations();
      }
      return;
    }

    const animList = embeddedAnimations.map((clip, index) => {
      const name = clip.name || `Animation_${index}`;
      console.log(`Found embedded animation: "${name}" (${clip.duration.toFixed(2)}s, ${clip.tracks.length} tracks)`);
      // Log first few track names to verify they differ between clips
      const trackSample = clip.tracks.slice(0, 3).map(t => t.name);
      console.log(`  Tracks: [${trackSample.join(', ')}${clip.tracks.length > 3 ? '...' : ''}]`);
      // Log first value of first track to verify data differs
      if (clip.tracks.length > 0 && clip.tracks[0].values.length > 0) {
        console.log(`  First track values[0..3]: [${Array.from(clip.tracks[0].values.slice(0, 4)).map(v => v.toFixed(4)).join(', ')}]`);
      }
      return { name, duration: clip.duration, index };
    });

    setEmbeddedAnimations(animList);
  }, [embeddedAnimations, isSkinnedPreview, setEmbeddedAnimations, clearEmbeddedAnimations]);

  // Create mixer when the selected animation changes (NOT on play/pause)
  useEffect(() => {
    // Destroy previous mixer completely
    if (embeddedMixerRef.current) {
      embeddedMixerRef.current.stopAllAction();
      embeddedMixerRef.current.uncacheRoot(clonedScene);
      embeddedMixerRef.current = null;
      embeddedActionRef.current = null;
    }

    if (!isSkinnedPreview || !activeEmbeddedName || !embeddedAnimations?.length) return;

    // Find the clip by name
    const clip = embeddedAnimations.find(
      (c) => c.name === activeEmbeddedName || (!c.name && activeEmbeddedName === `Animation_${embeddedAnimations.indexOf(c)}`)
    );
    if (!clip) {
      console.warn(`Clip "${activeEmbeddedName}" not found among ${embeddedAnimations.length} clips:`,
        embeddedAnimations.map(c => c.name));
      return;
    }

    // Create a brand new mixer for this specific animation
    const mixer = new THREE.AnimationMixer(clonedScene);
    embeddedMixerRef.current = mixer;

    const action = mixer.clipAction(clip);
    action.setLoop(THREE.LoopRepeat, Infinity);
    action.clampWhenFinished = false;
    embeddedActionRef.current = action;

    console.log(`Created fresh mixer for "${activeEmbeddedName}" (${clip.tracks.length} tracks, ${clip.duration.toFixed(2)}s)`);

    // Start playing immediately
    action.reset().play();

    return () => {
      mixer.stopAllAction();
      mixer.uncacheRoot(clonedScene);
    };
  }, [activeEmbeddedName, isSkinnedPreview, clonedScene, embeddedAnimations]);

  // Handle play/pause without destroying the mixer
  useEffect(() => {
    if (!embeddedActionRef.current || !isSkinnedPreview) return;

    if (isPlaying) {
      embeddedActionRef.current.paused = false;
    } else {
      embeddedActionRef.current.paused = true;
    }
  }, [isPlaying, isSkinnedPreview]);

  // Seek for embedded animations
  useEffect(() => {
    if (!embeddedMixerRef.current || !embeddedActionRef.current || !isSkinnedPreview || isPlaying) return;

    const timeDiff = Math.abs(currentTime - lastTimeRef.current);
    if (timeDiff > 0.05) {
      const action = embeddedActionRef.current;
      action.reset().play();
      action.paused = true;
      action.time = currentTime;
      embeddedMixerRef.current.update(0);
    }
    lastTimeRef.current = currentTime;
  }, [currentTime, isPlaying, isSkinnedPreview]);

  // Analyze model and report info
  useEffect(() => {
    if (!clonedScene) return;

    let vertexCount = 0;
    let faceCount = 0;
    const materials = new Set<string>();
    let hasTextures = false;
    let meshCount = 0;
    let skinnedMeshCount = 0;
    let boneCount = 0;

    clonedScene.traverse((child) => {
      if (child instanceof THREE.SkinnedMesh) {
        skinnedMeshCount++;
      }
      if (child instanceof THREE.Bone) {
        boneCount++;
      }
      if (child instanceof THREE.Mesh) {
        meshCount++;
        const geometry = child.geometry;
        if (geometry) {
          vertexCount += geometry.attributes.position?.count || 0;
          if (geometry.index) {
            faceCount += geometry.index.count / 3;
          } else {
            faceCount += (geometry.attributes.position?.count || 0) / 3;
          }
        }

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

    console.log('Scene analysis:', {
      meshCount, skinnedMeshCount, boneCount, vertexCount, hasTextures,
      materials: Array.from(materials), isSkinnedPreview,
      embeddedAnimationCount: embeddedAnimations?.length || 0,
    });

    onLoad?.({
      vertexCount,
      faceCount: Math.round(faceCount),
      materials: Array.from(materials),
      hasTextures,
      boundingBox,
    });
  }, [clonedScene, onLoad, isSkinnedPreview]);

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

  // Create bone objects from skeleton data for JSON animation targeting
  // Skip when in skinned preview mode - the GLB already has bones
  useEffect(() => {
    if (isSkinnedPreview) {
      boneGroupsRef.current.forEach((group) => {
        group.parent?.remove(group);
      });
      boneGroupsRef.current.clear();
      return;
    }

    if (!clonedScene || !skeletonData?.bones?.length) {
      boneGroupsRef.current.forEach((group) => {
        group.parent?.remove(group);
      });
      boneGroupsRef.current.clear();
      return;
    }

    boneGroupsRef.current.forEach((group) => {
      group.parent?.remove(group);
    });
    boneGroupsRef.current.clear();

    const boneDataMap = new Map(skeletonData.bones.map((b) => [b.name, b]));
    const boneGroups = new Map<string, THREE.Object3D>();
    skeletonData.bones.forEach((bone) => {
      const obj = new THREE.Object3D();
      obj.name = bone.name;
      boneGroups.set(bone.name, obj);
    });

    skeletonData.bones.forEach((bone) => {
      const obj = boneGroups.get(bone.name);
      if (!obj) return;

      if (bone.parent) {
        const parentObj = boneGroups.get(bone.parent);
        const parentBone = boneDataMap.get(bone.parent);
        if (parentObj && parentBone) {
          const parentHead = new THREE.Vector3(...parentBone.headPosition);
          const localPos = new THREE.Vector3(...bone.headPosition).sub(parentHead);
          obj.position.copy(localPos);
          parentObj.add(obj);
        }
      } else {
        obj.position.set(...bone.headPosition);
        clonedScene.add(obj);
      }
    });

    boneGroupsRef.current = boneGroups;
    console.log(`Created ${boneGroups.size} bone objects for animation`);

    return () => {
      boneGroupsRef.current.forEach((group) => {
        group.parent?.remove(group);
      });
      boneGroupsRef.current.clear();
    };
  }, [clonedScene, skeletonData, isSkinnedPreview]);

  // --- JSON-based animations (non-skinned mode) ---
  // Initialize a separate mixer for JSON keyframe animations
  useEffect(() => {
    if (!clonedScene || isSkinnedPreview) {
      jsonMixerRef.current = null;
      jsonActionsRef.current.clear();
      return;
    }

    const mixer = new THREE.AnimationMixer(clonedScene);
    jsonMixerRef.current = mixer;
    jsonActionsRef.current.clear();

    const onFinished = () => {
      setIsPlaying(false);
      setCurrentTime(0);
    };
    mixer.addEventListener('finished', onFinished as any);

    return () => {
      mixer.removeEventListener('finished', onFinished as any);
      mixer.stopAllAction();
      jsonActionsRef.current.clear();
      jsonMixerRef.current = null;
    };
  }, [clonedScene, skeletonData, isSkinnedPreview, setCurrentTime, setIsPlaying]);

  // Load JSON animation clips into mixer
  useEffect(() => {
    if (!jsonMixerRef.current || isSkinnedPreview) return;

    clips.forEach((clip) => {
      if (jsonActionsRef.current.has(clip.id) || !clip.keyframe_data) return;

      try {
        const tracks: THREE.KeyframeTrack[] = [];
        for (const track of clip.keyframe_data.tracks) {
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

          tracks.push(new TrackClass(trackName, track.times, track.values, THREE.InterpolateLinear));
        }

        const animClip = new THREE.AnimationClip(clip.name, clip.keyframe_data.duration, tracks);
        const action = jsonMixerRef.current!.clipAction(animClip);

        switch (clip.loop_mode) {
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

        jsonActionsRef.current.set(clip.id, action);
        console.log(`Loaded JSON animation: ${clip.name} with ${tracks.length} tracks`);
      } catch (error) {
        console.error('Failed to load animation clip:', clip.name, error);
      }
    });
  }, [clips, clonedScene, skeletonData, isSkinnedPreview]);

  // Play/pause JSON-based animations
  useEffect(() => {
    if (!jsonMixerRef.current || !activeClipId || isSkinnedPreview) return;

    const action = jsonActionsRef.current.get(activeClipId);
    if (!action) return;

    jsonActionsRef.current.forEach((a, id) => {
      if (id !== activeClipId) a.stop();
    });

    if (isPlaying) {
      action.reset().play();
    } else {
      action.paused = true;
    }
  }, [activeClipId, isPlaying, isSkinnedPreview]);

  // Seek for JSON animations
  useEffect(() => {
    if (!jsonMixerRef.current || isSkinnedPreview || !activeClipId || isPlaying) return;

    const action = jsonActionsRef.current.get(activeClipId);
    if (!action) return;

    const timeDiff = Math.abs(currentTime - lastTimeRef.current);
    if (timeDiff > 0.05) {
      action.paused = false;
      action.time = currentTime;
      jsonMixerRef.current.update(0);
      action.paused = true;
    }
    lastTimeRef.current = currentTime;
  }, [currentTime, activeClipId, isPlaying, isSkinnedPreview]);

  // Update mixers and current time on each frame
  useFrame((_, delta) => {
    // Auto-rotate (disabled during animation playback)
    if (settings.autoRotate && !isPlaying && groupRef.current) {
      groupRef.current.rotation.y += delta * 0.5;
    }

    // Update JSON mixer
    if (jsonMixerRef.current && isPlaying && !isSkinnedPreview) {
      jsonMixerRef.current.update(delta);
      if (activeClipId) {
        const activeAction = jsonActionsRef.current.get(activeClipId);
        if (activeAction) {
          setCurrentTime(activeAction.time);
        }
      }
    }

    // Update embedded mixer
    if (embeddedMixerRef.current && isPlaying && isSkinnedPreview) {
      embeddedMixerRef.current.update(delta);
      if (embeddedActionRef.current) {
        setCurrentTime(embeddedActionRef.current.time);
      }
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
  const {
    skeletonData,
    showSkeleton,
    selectedBone,
    setSelectedBone,
    floatingBones,
    editedBones,
    dragMode,
    updateBonePosition,
    isTuningMode,
    snapRequest,
    clearSnapRequest,
    // Landmark mode
    isLandmarkMode,
    landmarks,
    landmarkInfo,
    selectedLandmark,
    setSelectedLandmark,
    updateLandmark,
  } = useRiggingStore();
  const { scene: threeScene } = useThree();
  const meshRef = useRef<THREE.Mesh | null>(null);

  // Find and cache mesh reference from scene
  useEffect(() => {
    let foundMesh: THREE.Mesh | null = null;
    threeScene.traverse((child) => {
      if (child instanceof THREE.Mesh && child.geometry && !foundMesh) {
        // Skip very small meshes (likely helpers/gizmos)
        const posAttr = child.geometry.getAttribute('position');
        if (posAttr && posAttr.count > 100) {
          foundMesh = child;
        }
      }
    });
    meshRef.current = foundMesh;
  }, [threeScene, url]);

  // Handle snap-to-mesh requests
  useEffect(() => {
    if (!snapRequest || !meshRef.current || !skeletonData) {
      return;
    }

    const { boneName, target } = snapRequest;
    const bone = skeletonData.bones.find((b) => b.name === boneName);
    if (!bone) {
      clearSnapRequest();
      return;
    }

    // Get current positions (edited or original)
    const edit = editedBones.get(boneName);
    const currentHead = edit?.headPosition || bone.headPosition;
    const currentTail = edit?.tailPosition || bone.tailPosition;

    let newHead = currentHead;
    let newTail = currentTail;

    const mesh = meshRef.current;

    // Snap head position to nearest mesh surface
    if (target === 'head' || target === 'both') {
      const headVec = new THREE.Vector3(...currentHead);
      const nearestHead = findNearestPointOnMesh(mesh, headVec);
      if (nearestHead) {
        newHead = [nearestHead.x, nearestHead.y, nearestHead.z] as [number, number, number];
      }
    }

    // Snap tail position to nearest mesh surface
    if (target === 'tail' || target === 'both') {
      const tailVec = new THREE.Vector3(...currentTail);
      const nearestTail = findNearestPointOnMesh(mesh, tailVec);
      if (nearestTail) {
        newTail = [nearestTail.x, nearestTail.y, nearestTail.z] as [number, number, number];
      }
    }

    // Update bone position
    updateBonePosition(boneName, newHead, newTail);
    clearSnapRequest();

    console.log(`Snapped bone ${boneName} to mesh surface:`, { newHead, newTail });
  }, [snapRequest, skeletonData, editedBones, updateBonePosition, clearSnapRequest]);

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
                floatingBones={floatingBones}
                editedBones={editedBones}
                dragMode={isTuningMode && dragMode}
                onBonePositionChange={updateBonePosition}
              />
            )}
            {/* Landmark overlay for positioning key skeleton points */}
            <LandmarkVisualization
              landmarks={landmarks}
              landmarkInfo={landmarkInfo}
              selectedLandmark={selectedLandmark}
              onLandmarkSelect={setSelectedLandmark}
              onLandmarkMove={updateLandmark}
              visible={isLandmarkMode}
            />
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
  const {
    settings,
    setLoading,
    setLoadError,
    setModelInfo,
    isSkinnedPreview,
    skinnedPreviewUrl,
  } = useViewerStore();

  // Use skinned preview URL when in preview mode
  const effectiveUrl = isSkinnedPreview && skinnedPreviewUrl ? skinnedPreviewUrl : url;

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

  if (!effectiveUrl) {
    return null;
  }

  // Log the URL for debugging
  console.log('Loading model from URL:', effectiveUrl, isSkinnedPreview ? '(skinned preview)' : '');

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
          <Scene url={effectiveUrl} onLoad={handleLoad} onError={handleError} />
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
