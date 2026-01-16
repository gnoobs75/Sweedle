/**
 * useAnimationMixer - Hook for playing animations in the 3D viewer
 *
 * Converts backend keyframe data to Three.js AnimationClips and manages playback
 */

import { useEffect, useRef, useCallback } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { useAnimationStore, type AnimationClip as BackendClip } from '../stores/animationStore';

interface KeyframeTrack {
  bone_name: string;
  property: 'rotation' | 'position' | 'scale';
  times: number[];
  values: number[];
  interpolation?: 'LINEAR' | 'STEP' | 'CATMULLROM';
}

interface KeyframeData {
  tracks: KeyframeTrack[];
  duration: number;
  frame_rate: number;
}

/**
 * Convert backend keyframe data to Three.js AnimationClip
 */
function createAnimationClip(clip: BackendClip, keyframeData: KeyframeData): THREE.AnimationClip {
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

    // Determine interpolation mode
    let interpolation: THREE.InterpolationModes = THREE.InterpolateLinear;
    if (track.interpolation === 'STEP') {
      interpolation = THREE.InterpolateDiscrete;
    } else if (track.interpolation === 'CATMULLROM') {
      interpolation = THREE.InterpolateSmooth;
    }

    const keyframeTrack = new TrackClass(
      trackName,
      track.times,
      track.values,
      interpolation
    );

    tracks.push(keyframeTrack);
  }

  return new THREE.AnimationClip(clip.name, keyframeData.duration, tracks);
}

/**
 * Hook to manage animation playback for a Three.js scene
 */
export function useAnimationMixer(scene: THREE.Object3D | null) {
  const mixerRef = useRef<THREE.AnimationMixer | null>(null);
  const actionsRef = useRef<Map<string, THREE.AnimationAction>>(new Map());
  const clockRef = useRef<THREE.Clock>(new THREE.Clock());

  const {
    clips,
    activeClipId,
    isPlaying,
    currentTime,
    setCurrentTime,
    setIsPlaying,
  } = useAnimationStore();

  // Create mixer when scene is available
  useEffect(() => {
    if (!scene) {
      mixerRef.current = null;
      actionsRef.current.clear();
      return;
    }

    // Create new mixer for this scene
    const mixer = new THREE.AnimationMixer(scene);
    mixerRef.current = mixer;
    actionsRef.current.clear();

    // Handle animation loop/completion
    const onLoop = (event: { action: THREE.AnimationAction }) => {
      // Animation looped - reset time display
      setCurrentTime(0);
    };

    const onFinished = (event: { action: THREE.AnimationAction }) => {
      // Animation finished (non-looping)
      setIsPlaying(false);
      setCurrentTime(0);
    };

    mixer.addEventListener('loop', onLoop as any);
    mixer.addEventListener('finished', onFinished as any);

    return () => {
      mixer.removeEventListener('loop', onLoop as any);
      mixer.removeEventListener('finished', onFinished as any);
      mixer.stopAllAction();
      actionsRef.current.clear();
    };
  }, [scene, setCurrentTime, setIsPlaying]);

  // Load animation clips
  const loadClip = useCallback(async (clip: BackendClip) => {
    if (!mixerRef.current || !clip.keyframe_data) return;

    // Check if already loaded
    if (actionsRef.current.has(clip.id)) return;

    try {
      const animClip = createAnimationClip(clip, clip.keyframe_data as unknown as KeyframeData);
      const action = mixerRef.current.clipAction(animClip);

      // Configure loop mode
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

      actionsRef.current.set(clip.id, action);
    } catch (error) {
      console.error('Failed to load animation clip:', clip.name, error);
    }
  }, []);

  // Load all clips when they change
  useEffect(() => {
    clips.forEach(loadClip);
  }, [clips, loadClip]);

  // Handle play/pause state
  useEffect(() => {
    if (!mixerRef.current || !activeClipId) return;

    const action = actionsRef.current.get(activeClipId);
    if (!action) return;

    // Stop all other actions
    actionsRef.current.forEach((a, id) => {
      if (id !== activeClipId) {
        a.stop();
      }
    });

    if (isPlaying) {
      action.reset();
      action.play();
      clockRef.current.start();
    } else {
      action.paused = true;
    }
  }, [activeClipId, isPlaying]);

  // Seek to specific time
  const seekTo = useCallback((time: number) => {
    if (!mixerRef.current || !activeClipId) return;

    const action = actionsRef.current.get(activeClipId);
    if (!action) return;

    action.time = time;
    mixerRef.current.update(0);
    setCurrentTime(time);
  }, [activeClipId, setCurrentTime]);

  // Update mixer on each frame
  useFrame((_, delta) => {
    if (!mixerRef.current || !isPlaying) return;

    mixerRef.current.update(delta);

    // Update current time in store (throttled to avoid too many updates)
    const activeAction = activeClipId ? actionsRef.current.get(activeClipId) : null;
    if (activeAction) {
      setCurrentTime(activeAction.time);
    }
  });

  // Get current animation duration
  const getActiveDuration = useCallback(() => {
    if (!activeClipId) return 0;
    const clip = clips.find(c => c.id === activeClipId);
    return clip?.duration || 0;
  }, [activeClipId, clips]);

  return {
    mixer: mixerRef.current,
    seekTo,
    getActiveDuration,
  };
}

export default useAnimationMixer;
