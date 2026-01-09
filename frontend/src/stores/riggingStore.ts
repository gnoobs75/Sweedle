/**
 * Rigging state management store.
 */

import { create } from 'zustand';

export type CharacterType = 'humanoid' | 'quadruped' | 'auto';
export type RiggingProcessor = 'unirig' | 'blender' | 'auto';
export type RiggingStatus = 'idle' | 'pending' | 'detecting' | 'rigging' | 'completed' | 'failed';

export interface BoneData {
  name: string;
  parent: string | null;
  headPosition: [number, number, number];
  tailPosition: [number, number, number];
  rotation: [number, number, number, number];
}

export interface SkeletonData {
  rootBone: string;
  bones: BoneData[];
  characterType: CharacterType;
  boneCount: number;
}

export interface RiggingJob {
  id: string;
  assetId: string;
  status: RiggingStatus;
  progress: number;
  stage: string;
  detectedType?: CharacterType;
  error?: string;
  createdAt: string;
  startedAt?: string;
  completedAt?: string;
}

interface RiggingState {
  // Current rigging job
  currentJobId: string | null;
  isRigging: boolean;
  progress: number;
  stage: string;
  status: RiggingStatus;

  // Selected options
  selectedAssetId: string | null;
  characterType: CharacterType;
  processor: RiggingProcessor;

  // Results
  detectedType: CharacterType | null;
  skeletonData: SkeletonData | null;
  error: string | null;

  // Viewer state
  showSkeleton: boolean;
  selectedBone: string | null;

  // Actions
  setSelectedAsset: (assetId: string | null) => void;
  setCharacterType: (type: CharacterType) => void;
  setProcessor: (processor: RiggingProcessor) => void;
  setIsRigging: (isRigging: boolean) => void;
  setProgress: (progress: number, stage: string) => void;
  setStatus: (status: RiggingStatus) => void;
  setDetectedType: (type: CharacterType) => void;
  setSkeletonData: (skeleton: SkeletonData | null) => void;
  setCurrentJobId: (jobId: string | null) => void;
  setShowSkeleton: (show: boolean) => void;
  setSelectedBone: (bone: string | null) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

const initialState = {
  currentJobId: null,
  isRigging: false,
  progress: 0,
  stage: '',
  status: 'idle' as RiggingStatus,
  selectedAssetId: null,
  characterType: 'auto' as CharacterType,
  processor: 'auto' as RiggingProcessor,
  detectedType: null,
  skeletonData: null,
  error: null,
  showSkeleton: true,
  selectedBone: null,
};

export const useRiggingStore = create<RiggingState>((set) => ({
  ...initialState,

  setSelectedAsset: (assetId) => set({ selectedAssetId: assetId }),

  setCharacterType: (type) => set({ characterType: type }),

  setProcessor: (processor) => set({ processor }),

  setIsRigging: (isRigging) => set({ isRigging }),

  setProgress: (progress, stage) => set({ progress, stage }),

  setStatus: (status) => set({ status }),

  setDetectedType: (type) => set({ detectedType: type }),

  setSkeletonData: (skeleton) => set({ skeletonData: skeleton }),

  setCurrentJobId: (jobId) => set({ currentJobId: jobId }),

  setShowSkeleton: (show) => set({ showSkeleton: show }),

  setSelectedBone: (bone) => set({ selectedBone: bone }),

  setError: (error) => set({ error }),

  reset: () => set(initialState),
}));
