/**
 * GalleryViewer - Self-contained 3D viewer with animation playback for gallery.
 *
 * Shows the model inline in AssetDetailView. For rigged assets with animations,
 * generates a skinned GLB on demand and provides animation selection + playback.
 * Fully self-contained: owns its AnimationMixer and doesn't touch global stores.
 */

import { Suspense, useEffect, useRef, useState, useMemo, useCallback } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import {
  OrbitControls,
  Environment,
  useGLTF,
  Center,
  Bounds,
  useBounds,
  Html,
  useProgress,
} from '@react-three/drei';
import * as THREE from 'three';
import * as SkeletonUtils from 'three/examples/jsm/utils/SkeletonUtils.js';
import { Spinner } from '../ui/Spinner';
import { getAssetModelUrl, getStorageBase } from '../../services/api/assets';
import { exportSkinnedGLB } from '../../services/api/export';
import type { AnimationClip } from '../../stores/animationStore';

const API_BASE = 'http://localhost:8001';

const ANIMATION_EMOJIS: Record<string, string> = {
  idle: '🧘', walk: '🚶', run: '🏃', attack: '⚔️', jump: '🦘', die: '💀',
  sit: '🪑', lie_down: '🛏️', crouch: '🦆', dodge: '💨', wave: '👋',
  cheer: '🎉', pickup: '🤲', trot: '🐕', gallop: '🏇', tail_wag: '🐕',
  bite: '🦴', shake: '🐕‍🦺', pounce: '🐱', howl: '🐺', roll_over: '🔄', play_dead: '😵',
};

interface GalleryViewerProps {
  assetId: string;
  isRigged?: boolean;
  animationCount?: number;
  animations?: AnimationClip[];
  thumbnailUrl?: string;
}

/** Loading indicator inside the canvas */
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

/** Internal model with self-contained animation mixer */
function GalleryModel({
  url,
  activeAnimationName,
  isPlaying,
  onAnimationsFound,
  onTimeUpdate,
}: {
  url: string;
  activeAnimationName: string | null;
  isPlaying: boolean;
  onAnimationsFound: (anims: Array<{ name: string; duration: number; index: number }>) => void;
  onTimeUpdate: (time: number) => void;
}) {
  const gltf = useGLTF(url, true, true);
  const { scene, animations: embeddedAnimations } = gltf;

  const clonedScene = useMemo(() => {
    let hasSkinnedMesh = false;
    scene.traverse((child) => {
      if (child instanceof THREE.SkinnedMesh) hasSkinnedMesh = true;
    });
    return hasSkinnedMesh
      ? (SkeletonUtils.clone(scene) as THREE.Group)
      : scene.clone();
  }, [scene]);

  // Report available animations once
  const reportedRef = useRef(false);
  useEffect(() => {
    if (reportedRef.current || !embeddedAnimations?.length) return;
    reportedRef.current = true;
    const animList = embeddedAnimations.map((clip, i) => ({
      name: clip.name || `Animation_${i}`,
      duration: clip.duration,
      index: i,
    }));
    onAnimationsFound(animList);
  }, [embeddedAnimations, onAnimationsFound]);

  // Own mixer + action
  const mixerRef = useRef<THREE.AnimationMixer | null>(null);
  const actionRef = useRef<THREE.AnimationAction | null>(null);

  // Create/destroy mixer when selected animation changes
  useEffect(() => {
    if (mixerRef.current) {
      mixerRef.current.stopAllAction();
      mixerRef.current.uncacheRoot(clonedScene);
      mixerRef.current = null;
      actionRef.current = null;
    }

    if (!activeAnimationName || !embeddedAnimations?.length) return;

    const clip = embeddedAnimations.find(
      (c, i) => c.name === activeAnimationName || (!c.name && activeAnimationName === `Animation_${i}`)
    );
    if (!clip) return;

    const mixer = new THREE.AnimationMixer(clonedScene);
    mixerRef.current = mixer;

    const action = mixer.clipAction(clip);
    action.setLoop(THREE.LoopRepeat, Infinity);
    action.clampWhenFinished = false;
    actionRef.current = action;

    action.reset().play();
    if (!isPlaying) action.paused = true;

    return () => {
      mixer.stopAllAction();
      mixer.uncacheRoot(clonedScene);
    };
  }, [activeAnimationName, clonedScene, embeddedAnimations]);

  // Handle play/pause
  useEffect(() => {
    if (!actionRef.current) return;
    actionRef.current.paused = !isPlaying;
  }, [isPlaying]);

  // Update mixer each frame
  useFrame((_, delta) => {
    if (mixerRef.current && isPlaying) {
      mixerRef.current.update(delta);
      if (actionRef.current) {
        onTimeUpdate(actionRef.current.time);
      }
    }
  });

  return <primitive object={clonedScene} />;
}

/** Bounds auto-fit handler */
function BoundsHandler({ children }: { children: React.ReactNode }) {
  const bounds = useBounds();
  useEffect(() => {
    bounds.refresh().clip().fit();
  }, [bounds]);
  return <>{children}</>;
}

export function GalleryViewer({
  assetId,
  isRigged,
  animationCount = 0,
  animations = [],
  thumbnailUrl,
}: GalleryViewerProps) {
  const [mode, setMode] = useState<'thumbnail' | '3d' | 'animated'>('thumbnail');
  const [modelUrl, setModelUrl] = useState<string | null>(null);
  const [skinnedUrl, setSkinnedUrl] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generateError, setGenerateError] = useState<string | null>(null);

  // Animation state (self-contained)
  const [embeddedAnims, setEmbeddedAnims] = useState<Array<{ name: string; duration: number; index: number }>>([]);
  const [activeAnimName, setActiveAnimName] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [imageError, setImageError] = useState(false);

  // Reset when asset changes
  useEffect(() => {
    setMode('thumbnail');
    setModelUrl(null);
    setSkinnedUrl(null);
    setEmbeddedAnims([]);
    setActiveAnimName(null);
    setIsPlaying(false);
    setCurrentTime(0);
    setGenerateError(null);
    setImageError(false);
  }, [assetId]);

  const hasAnimations = isRigged && animationCount > 0;

  /** Switch to basic 3D view */
  const handleView3D = useCallback(() => {
    const url = getAssetModelUrl(assetId);
    setModelUrl(url);
    setMode('3d');
  }, [assetId]);

  /** Generate skinned GLB and switch to animated view */
  const handleLoadAnimations = useCallback(async () => {
    setIsGenerating(true);
    setGenerateError(null);

    try {
      const result = await exportSkinnedGLB({
        assetId,
        includeAnimations: true,
      });

      if (result.success && result.outputPath) {
        const cleanPath = result.outputPath.replace(/\\/g, '/');
        const urlPath = cleanPath.startsWith('/') ? cleanPath : `/${cleanPath}`;
        const fullUrl = `${API_BASE}${urlPath}?t=${Date.now()}`;
        setSkinnedUrl(fullUrl);
        setMode('animated');
        setIsPlaying(true);
      } else {
        throw new Error(result.error || 'Failed to generate animated model');
      }
    } catch (error) {
      setGenerateError(error instanceof Error ? error.message : 'Failed to generate');
    } finally {
      setIsGenerating(false);
    }
  }, [assetId]);

  const handleAnimationsFound = useCallback((anims: Array<{ name: string; duration: number; index: number }>) => {
    setEmbeddedAnims(anims);
    if (anims.length > 0 && !activeAnimName) {
      setActiveAnimName(anims[0].name);
    }
  }, [activeAnimName]);

  const handleSelectAnimation = useCallback((name: string) => {
    setActiveAnimName(name);
    setCurrentTime(0);
    setIsPlaying(true);
  }, []);

  const activeClipDuration = embeddedAnims.find(a => a.name === activeAnimName)?.duration || 0;

  // Thumbnail mode
  if (mode === 'thumbnail') {
    return (
      <div className="aspect-square rounded-2xl overflow-hidden bg-surface-light border border-border relative group">
        {thumbnailUrl && !imageError ? (
          <img
            src={thumbnailUrl}
            alt="Asset preview"
            className="w-full h-full object-cover"
            onError={() => setImageError(true)}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <svg className="w-16 h-16 text-text-muted/40" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
            </svg>
          </div>
        )}

        {/* Overlay buttons */}
        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-colors flex items-center justify-center gap-3 opacity-0 group-hover:opacity-100">
          <button
            onClick={handleView3D}
            className="px-4 py-2 bg-white/90 hover:bg-white text-gray-900 text-sm font-medium rounded-lg shadow-lg transition-colors"
          >
            View 3D
          </button>
          {hasAnimations && (
            <button
              onClick={handleLoadAnimations}
              disabled={isGenerating}
              className="px-4 py-2 bg-purple-600/90 hover:bg-purple-500 text-white text-sm font-medium rounded-lg shadow-lg transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              {isGenerating ? (
                <>
                  <Spinner size="sm" variant="white" />
                  Generating...
                </>
              ) : (
                <>Play Animations</>
              )}
            </button>
          )}
        </div>

        {generateError && (
          <div className="absolute bottom-2 left-2 right-2 px-3 py-2 bg-red-900/90 text-red-200 text-xs rounded-lg">
            {generateError}
          </div>
        )}
      </div>
    );
  }

  // 3D / Animated mode
  const effectiveUrl = mode === 'animated' && skinnedUrl ? skinnedUrl : modelUrl;

  return (
    <div className="space-y-3">
      {/* Viewer Canvas */}
      <div className="aspect-square rounded-2xl overflow-hidden bg-[#1a1a2e] border border-border relative">
        {effectiveUrl ? (
          <Canvas
            shadows
            camera={{ position: [3, 3, 3], fov: 50 }}
            gl={{
              antialias: true,
              toneMapping: THREE.ACESFilmicToneMapping,
              toneMappingExposure: 1.0,
              powerPreference: 'high-performance',
              failIfMajorPerformanceCaveat: false,
            }}
          >
            <Suspense fallback={<Loader />}>
              {/* Lighting */}
              <ambientLight intensity={0.4} />
              <directionalLight position={[10, 10, 5]} intensity={1} />
              <directionalLight position={[-10, -10, -5]} intensity={0.3} />
              <Environment preset="studio" background={false} />

              <Bounds fit clip observe margin={1.2}>
                <BoundsHandler>
                  <Center>
                    <GalleryModel
                      url={effectiveUrl}
                      activeAnimationName={mode === 'animated' ? activeAnimName : null}
                      isPlaying={isPlaying}
                      onAnimationsFound={handleAnimationsFound}
                      onTimeUpdate={setCurrentTime}
                    />
                  </Center>
                </BoundsHandler>
              </Bounds>
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
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <Spinner size="lg" />
          </div>
        )}

        {/* Back to thumbnail button */}
        <button
          onClick={() => setMode('thumbnail')}
          className="absolute top-3 left-3 p-1.5 bg-black/60 hover:bg-black/80 text-white rounded-lg transition-colors"
          title="Back to thumbnail"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        {/* Load animations button (in 3D mode, if available) */}
        {mode === '3d' && hasAnimations && (
          <button
            onClick={handleLoadAnimations}
            disabled={isGenerating}
            className="absolute bottom-3 right-3 px-3 py-1.5 bg-purple-600/90 hover:bg-purple-500 text-white text-xs font-medium rounded-lg shadow-lg transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            {isGenerating ? (
              <>
                <Spinner size="sm" variant="white" />
                Loading Animations...
              </>
            ) : (
              <>Play Animations</>
            )}
          </button>
        )}
      </div>

      {/* Animation Controls (only in animated mode with animations) */}
      {mode === 'animated' && embeddedAnims.length > 0 && (
        <div className="bg-surface-light rounded-xl border border-border p-3 space-y-3">
          {/* Play/Pause + Time */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsPlaying(!isPlaying)}
              className="p-2 bg-purple-600 hover:bg-purple-500 text-white rounded-lg transition-colors"
            >
              {isPlaying ? (
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                  <rect x="6" y="4" width="4" height="16" />
                  <rect x="14" y="4" width="4" height="16" />
                </svg>
              ) : (
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                  <polygon points="5,3 19,12 5,21" />
                </svg>
              )}
            </button>

            <div className="flex-1">
              <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-purple-500 rounded-full transition-all duration-100"
                  style={{
                    width: activeClipDuration > 0
                      ? `${((currentTime % activeClipDuration) / activeClipDuration) * 100}%`
                      : '0%',
                  }}
                />
              </div>
            </div>

            <span className="text-xs text-text-muted font-mono min-w-[4rem] text-right">
              {currentTime.toFixed(1)}s / {activeClipDuration.toFixed(1)}s
            </span>
          </div>

          {/* Animation selector buttons */}
          <div className="flex flex-wrap gap-1.5">
            {embeddedAnims.map((anim) => {
              const isActive = activeAnimName === anim.name;
              // Try to find a matching animation type for emoji
              const clip = animations?.find(c => anim.name.toLowerCase().includes(c.animationType));
              const emoji = clip ? ANIMATION_EMOJIS[clip.animationType] : null;

              return (
                <button
                  key={anim.name}
                  onClick={() => handleSelectAnimation(anim.name)}
                  className={`px-2.5 py-1.5 text-xs rounded-lg transition-colors flex items-center gap-1.5 ${
                    isActive
                      ? 'bg-purple-600 text-white'
                      : 'bg-surface border border-border text-text-secondary hover:text-text-primary hover:border-purple-500/50'
                  }`}
                >
                  {emoji && <span>{emoji}</span>}
                  <span className="truncate max-w-[8rem]">{anim.name}</span>
                  <span className="text-[10px] opacity-60">{anim.duration.toFixed(1)}s</span>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {generateError && (
        <div className="px-3 py-2 bg-red-900/30 border border-red-700/30 rounded-lg text-xs text-red-400">
          {generateError}
        </div>
      )}
    </div>
  );
}
