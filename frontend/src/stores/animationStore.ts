/**
 * Animation state management store.
 */

import { create } from 'zustand';

export type AnimationType =
  // Common animations (both humanoid and quadruped)
  | 'idle'
  | 'walk'
  | 'run'
  | 'attack'
  | 'jump'
  | 'die'
  | 'sit'
  | 'lie_down'
  // Humanoid-specific
  | 'crouch'
  | 'dodge'
  | 'wave'
  | 'cheer'
  | 'pickup'
  // Quadruped-specific
  | 'trot'
  | 'gallop'
  | 'tail_wag'
  | 'bite'
  | 'shake'
  | 'pounce'
  | 'howl'
  | 'roll_over'
  | 'play_dead';

export type LoopMode = 'loop' | 'once' | 'pingpong';

export interface AnimationParameters {
  speed: number;
  intensity: number;
  blendFactor: number;
}

export interface AnimationPreset {
  id: string;
  name: string;
  description: string;
  animationType: AnimationType;
  characterType: 'humanoid' | 'quadruped';
  defaultParameters: AnimationParameters;
  duration: number;
  thumbnailUrl?: string;
  tags: string[];
}

export interface AnimationClip {
  id: string;
  assetId: string;
  name: string;
  animationType: AnimationType;
  duration: number;
  parameters: AnimationParameters;
  loop_mode: LoopMode;
  createdAt: string;
  // Keyframe data for playback (loaded from backend)
  keyframe_data?: {
    tracks: Array<{
      bone_name: string;
      property: 'rotation' | 'position' | 'scale';
      times: number[];
      values: number[];
      interpolation?: string;
    }>;
    duration: number;
    frame_rate: number;
  };
}

export interface KeyframeTrack {
  boneName: string;
  times: number[];
  rotations?: number[][];
  positions?: number[][];
  scales?: number[][];
}

export interface AnimationData {
  name: string;
  duration: number;
  frameRate: number;
  tracks: KeyframeTrack[];
}

interface AnimationState {
  // Available presets
  presets: AnimationPreset[];
  selectedPresetId: string | null;

  // Applied animations
  clips: AnimationClip[];
  activeClipId: string | null;

  // Playback state
  isPlaying: boolean;
  currentTime: number;

  // Parameters being edited
  parameters: AnimationParameters;

  // Loading state
  isLoading: boolean;
  isApplying: boolean;
  error: string | null;

  // Actions
  setPresets: (presets: AnimationPreset[]) => void;
  selectPreset: (presetId: string | null) => void;
  setClips: (clips: AnimationClip[]) => void;
  addClip: (clip: AnimationClip) => void;
  removeClip: (clipId: string) => void;
  setActiveClip: (clipId: string | null) => void;
  setParameters: (params: Partial<AnimationParameters>) => void;
  resetParameters: () => void;
  play: () => void;
  pause: () => void;
  stop: () => void;
  seek: (time: number) => void;
  setCurrentTime: (time: number) => void;
  setIsPlaying: (playing: boolean) => void;
  setIsLoading: (loading: boolean) => void;
  setIsApplying: (applying: boolean) => void;
  setError: (error: string | null) => void;
  clearError: () => void;
  reset: () => void;
}

const defaultParameters: AnimationParameters = {
  speed: 1.0,
  intensity: 1.0,
  blendFactor: 1.0,
};

const initialState = {
  presets: [] as AnimationPreset[],
  selectedPresetId: null as string | null,
  clips: [] as AnimationClip[],
  activeClipId: null as string | null,
  isPlaying: false,
  currentTime: 0,
  parameters: { ...defaultParameters },
  isLoading: false,
  isApplying: false,
  error: null as string | null,
};

export const useAnimationStore = create<AnimationState>((set, get) => ({
  ...initialState,

  setPresets: (presets) => set({ presets }),

  selectPreset: (presetId) => {
    // When selecting a preset, reset parameters to preset defaults
    const { presets } = get();
    const preset = presets.find((p) => p.id === presetId);
    set({
      selectedPresetId: presetId,
      parameters: preset ? { ...preset.defaultParameters } : { ...defaultParameters },
    });
  },

  setClips: (clips) => set({ clips }),

  addClip: (clip) =>
    set((state) => ({
      clips: [...state.clips, clip],
      activeClipId: clip.id, // Auto-select new clip
    })),

  removeClip: (clipId) =>
    set((state) => ({
      clips: state.clips.filter((c) => c.id !== clipId),
      activeClipId: state.activeClipId === clipId ? null : state.activeClipId,
    })),

  setActiveClip: (clipId) => set({ activeClipId: clipId, currentTime: 0 }),

  setParameters: (params) =>
    set((state) => ({
      parameters: { ...state.parameters, ...params },
    })),

  resetParameters: () => set({ parameters: { ...defaultParameters } }),

  play: () => set({ isPlaying: true }),

  pause: () => set({ isPlaying: false }),

  stop: () => set({ isPlaying: false, currentTime: 0 }),

  seek: (time) => set({ currentTime: time }),

  setCurrentTime: (time) => set({ currentTime: time }),

  setIsPlaying: (playing) => set({ isPlaying: playing }),

  setIsLoading: (loading) => set({ isLoading: loading }),

  setIsApplying: (applying) => set({ isApplying: applying }),

  setError: (error) => set({ error }),

  clearError: () => set({ error: null }),

  reset: () => set(initialState),
}));
