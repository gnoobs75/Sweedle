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

// Bone edit state for tuning
export interface BoneEdit {
  boneName: string;
  headPosition: [number, number, number];
  tailPosition: [number, number, number];
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

  // Bone tuning state
  isTuningMode: boolean;
  editedBones: Map<string, BoneEdit>;
  floatingBones: string[]; // Bones detected outside mesh
  meshBounds: { min: [number, number, number]; max: [number, number, number] } | null;
  dragMode: boolean; // Whether 3D dragging is enabled
  snapRequest: { boneName: string; target: 'head' | 'tail' | 'both' } | null; // Request to snap bone to mesh

  // Landmark mode state
  isLandmarkMode: boolean;
  landmarks: Record<string, [number, number, number]>;
  landmarkInfo: Array<{ name: string; color: string; description?: string }>;
  selectedLandmark: string | null;

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

  // Bone tuning actions
  enterTuningMode: () => void;
  exitTuningMode: () => void;
  updateBonePosition: (boneName: string, head: [number, number, number], tail: [number, number, number]) => void;
  setFloatingBones: (bones: string[]) => void;
  setMeshBounds: (bounds: { min: [number, number, number]; max: [number, number, number] } | null) => void;
  setDragMode: (enabled: boolean) => void;
  requestSnapToMesh: (boneName: string, target: 'head' | 'tail' | 'both') => void;
  clearSnapRequest: () => void;
  applyEdits: () => void; // Apply edits to skeletonData
  revertEdits: () => void; // Discard edits

  // Landmark mode actions
  enterLandmarkMode: () => void;
  exitLandmarkMode: () => void;
  setLandmarks: (landmarks: Record<string, [number, number, number]>) => void;
  setLandmarkInfo: (info: Array<{ name: string; color: string; description?: string }>) => void;
  updateLandmark: (name: string, position: [number, number, number]) => void;
  setSelectedLandmark: (name: string | null) => void;
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
  // Tuning state
  isTuningMode: false,
  editedBones: new Map<string, BoneEdit>(),
  floatingBones: [] as string[],
  meshBounds: null as { min: [number, number, number]; max: [number, number, number] } | null,
  dragMode: false,
  snapRequest: null as { boneName: string; target: 'head' | 'tail' | 'both' } | null,
  // Landmark mode
  isLandmarkMode: false,
  landmarks: {} as Record<string, [number, number, number]>,
  landmarkInfo: [] as Array<{ name: string; color: string; description?: string }>,
  selectedLandmark: null as string | null,
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

  reset: () => set({ ...initialState, editedBones: new Map() }),

  // Bone tuning actions
  enterTuningMode: () => set({ isTuningMode: true, editedBones: new Map(), dragMode: false }),

  exitTuningMode: () => set({ isTuningMode: false, editedBones: new Map(), floatingBones: [], dragMode: false, snapRequest: null }),

  setDragMode: (enabled) => set({ dragMode: enabled }),

  requestSnapToMesh: (boneName, target) => set({ snapRequest: { boneName, target } }),

  clearSnapRequest: () => set({ snapRequest: null }),

  updateBonePosition: (boneName, head, tail) =>
    set((state) => {
      const newEdits = new Map(state.editedBones);
      newEdits.set(boneName, { boneName, headPosition: head, tailPosition: tail });
      return { editedBones: newEdits };
    }),

  setFloatingBones: (bones) => set({ floatingBones: bones }),

  setMeshBounds: (bounds) => set({ meshBounds: bounds }),

  applyEdits: () =>
    set((state) => {
      if (!state.skeletonData || state.editedBones.size === 0) {
        return { isTuningMode: false, editedBones: new Map() };
      }

      // Apply edits to skeleton data
      const updatedBones = state.skeletonData.bones.map((bone) => {
        const edit = state.editedBones.get(bone.name);
        if (edit) {
          return {
            ...bone,
            headPosition: edit.headPosition,
            tailPosition: edit.tailPosition,
          };
        }
        return bone;
      });

      return {
        skeletonData: { ...state.skeletonData, bones: updatedBones },
        isTuningMode: false,
        editedBones: new Map(),
        floatingBones: [],
      };
    }),

  revertEdits: () => set({ editedBones: new Map(), floatingBones: [] }),

  // Landmark mode actions
  enterLandmarkMode: () => set({
    isLandmarkMode: true,
    isTuningMode: false,
    selectedLandmark: null,
  }),

  exitLandmarkMode: () => set({
    isLandmarkMode: false,
    landmarks: {},
    landmarkInfo: [],
    selectedLandmark: null,
  }),

  setLandmarks: (landmarks) => set({ landmarks }),

  setLandmarkInfo: (info) => set({ landmarkInfo: info }),

  updateLandmark: (name, position) =>
    set((state) => ({
      landmarks: {
        ...state.landmarks,
        [name]: position,
      },
    })),

  setSelectedLandmark: (name) => set({ selectedLandmark: name }),
}));
