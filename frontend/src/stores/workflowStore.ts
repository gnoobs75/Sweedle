/**
 * Workflow Store - Manages the 4-stage wizard workflow state
 *
 * Stages:
 * 1. Upload -> Mesh Generation
 * 2. Texturing
 * 3. Rigging
 * 4. Export
 */

import { create } from 'zustand';

export type WorkflowStage = 'upload' | 'mesh' | 'texture' | 'rigging' | 'export';
export type StageStatus = 'pending' | 'processing' | 'completed' | 'approved' | 'skipped' | 'failed';

interface StageState {
  status: StageStatus;
  error?: string;
}

interface PipelineStatus {
  shapeLoaded: boolean;
  textureLoaded: boolean;
  vramAllocatedGb: number;
  vramFreeGb: number;
}

interface WorkflowState {
  // Workflow tracking
  isActive: boolean;
  activeAssetId: string | null;
  currentStage: WorkflowStage;

  // Stage states
  stages: {
    upload: StageState;
    mesh: StageState;
    texture: StageState;
    rigging: StageState;
    export: StageState;
  };

  // Processing state
  isProcessing: boolean;
  currentJobId: string | null;
  progress: number;
  progressMessage: string;

  // Pipeline/VRAM status
  pipelineStatus: PipelineStatus;

  // Source image for current workflow
  sourceImage: File | null;
  sourceImagePreview: string | null;
  assetName: string;

  // Actions
  startWorkflow: (sourceImage?: File, assetName?: string) => void;
  startWorkflowFromAsset: (assetId: string, stage: WorkflowStage) => void;
  setCurrentStage: (stage: WorkflowStage) => void;
  setStageStatus: (stage: WorkflowStage, status: StageStatus, error?: string) => void;
  approveStage: () => void;
  skipToExport: () => void;
  redoStage: () => void;
  cancelWorkflow: () => void;
  resetWorkflow: () => void;

  // Processing
  setProcessing: (processing: boolean, jobId?: string | null) => void;
  setProgress: (progress: number, message: string) => void;
  setActiveAssetId: (assetId: string | null) => void;

  // Pipeline status
  setPipelineStatus: (status: Partial<PipelineStatus>) => void;

  // Source image
  setSourceImage: (file: File | null) => void;
  setAssetName: (name: string) => void;
}

const defaultStages = {
  upload: { status: 'pending' as StageStatus },
  mesh: { status: 'pending' as StageStatus },
  texture: { status: 'pending' as StageStatus },
  rigging: { status: 'pending' as StageStatus },
  export: { status: 'pending' as StageStatus },
};

const defaultPipelineStatus: PipelineStatus = {
  shapeLoaded: false,
  textureLoaded: false,
  vramAllocatedGb: 0,
  vramFreeGb: 24, // Default assumption
};

// Stage order for navigation
const stageOrder: WorkflowStage[] = ['upload', 'mesh', 'texture', 'rigging', 'export'];

function getNextStage(current: WorkflowStage): WorkflowStage | null {
  const idx = stageOrder.indexOf(current);
  return idx < stageOrder.length - 1 ? stageOrder[idx + 1] : null;
}

function getPrevStage(current: WorkflowStage): WorkflowStage | null {
  const idx = stageOrder.indexOf(current);
  return idx > 0 ? stageOrder[idx - 1] : null;
}

export const useWorkflowStore = create<WorkflowState>()((set, get) => ({
  // Initial state
  isActive: false,
  activeAssetId: null,
  currentStage: 'upload',
  stages: { ...defaultStages },
  isProcessing: false,
  currentJobId: null,
  progress: 0,
  progressMessage: '',
  pipelineStatus: { ...defaultPipelineStatus },
  sourceImage: null,
  sourceImagePreview: null,
  assetName: '',

  // Start a new workflow from image upload
  startWorkflow: (sourceImage, assetName) => {
    // Revoke previous preview URL
    const prevPreview = get().sourceImagePreview;
    if (prevPreview) {
      URL.revokeObjectURL(prevPreview);
    }

    const preview = sourceImage ? URL.createObjectURL(sourceImage) : null;
    const name = assetName || (sourceImage?.name.replace(/\.[^/.]+$/, '') || 'Untitled');

    set({
      isActive: true,
      activeAssetId: null,
      currentStage: 'upload',
      stages: {
        upload: { status: 'completed' },
        mesh: { status: 'pending' },
        texture: { status: 'pending' },
        rigging: { status: 'pending' },
        export: { status: 'pending' },
      },
      isProcessing: false,
      currentJobId: null,
      progress: 0,
      progressMessage: '',
      sourceImage: sourceImage || null,
      sourceImagePreview: preview,
      assetName: name,
    });
  },

  // Start workflow from an existing asset (re-entry)
  startWorkflowFromAsset: (assetId, stage) => {
    // Determine which stages are already complete based on entry stage
    const stageIdx = stageOrder.indexOf(stage);
    const newStages = { ...defaultStages };

    // Mark all previous stages as approved/skipped
    for (let i = 0; i < stageIdx; i++) {
      newStages[stageOrder[i]] = { status: 'approved' };
    }
    newStages[stage] = { status: 'pending' };

    set({
      isActive: true,
      activeAssetId: assetId,
      currentStage: stage,
      stages: newStages,
      isProcessing: false,
      currentJobId: null,
      progress: 0,
      progressMessage: '',
      sourceImage: null,
      sourceImagePreview: null,
      assetName: '',
    });
  },

  setCurrentStage: (stage) => set({ currentStage: stage }),

  setStageStatus: (stage, status, error) =>
    set((state) => ({
      stages: {
        ...state.stages,
        [stage]: { status, error },
      },
    })),

  // Approve current stage and advance to next
  approveStage: () => {
    const state = get();
    const nextStage = getNextStage(state.currentStage);

    set((state) => ({
      stages: {
        ...state.stages,
        [state.currentStage]: { status: 'approved' },
      },
      currentStage: nextStage || state.currentStage,
      isProcessing: false,
      progress: 0,
      progressMessage: '',
    }));
  },

  // Skip remaining stages and go directly to export
  skipToExport: () => {
    const state = get();
    const newStages = { ...state.stages };

    // Mark current stage as approved, skip remaining stages
    for (const stage of stageOrder) {
      if (stage === state.currentStage) {
        newStages[stage] = { status: 'approved' };
      } else if (stageOrder.indexOf(stage) > stageOrder.indexOf(state.currentStage)) {
        if (stage !== 'export') {
          newStages[stage] = { status: 'skipped' };
        }
      }
    }
    newStages.export = { status: 'pending' };

    set({
      stages: newStages,
      currentStage: 'export',
      isProcessing: false,
      progress: 0,
      progressMessage: '',
    });
  },

  // Redo current stage (keep previous stage outputs)
  redoStage: () => {
    const state = get();
    set({
      stages: {
        ...state.stages,
        [state.currentStage]: { status: 'pending' },
      },
      isProcessing: false,
      currentJobId: null,
      progress: 0,
      progressMessage: '',
    });
  },

  // Cancel the entire workflow
  cancelWorkflow: () => {
    const prevPreview = get().sourceImagePreview;
    if (prevPreview) {
      URL.revokeObjectURL(prevPreview);
    }

    set({
      isActive: false,
      activeAssetId: null,
      currentStage: 'upload',
      stages: { ...defaultStages },
      isProcessing: false,
      currentJobId: null,
      progress: 0,
      progressMessage: '',
      sourceImage: null,
      sourceImagePreview: null,
      assetName: '',
    });
  },

  // Full reset
  resetWorkflow: () => {
    const prevPreview = get().sourceImagePreview;
    if (prevPreview) {
      URL.revokeObjectURL(prevPreview);
    }

    set({
      isActive: false,
      activeAssetId: null,
      currentStage: 'upload',
      stages: { ...defaultStages },
      isProcessing: false,
      currentJobId: null,
      progress: 0,
      progressMessage: '',
      pipelineStatus: { ...defaultPipelineStatus },
      sourceImage: null,
      sourceImagePreview: null,
      assetName: '',
    });
  },

  // Processing state
  setProcessing: (processing, jobId = null) =>
    set({
      isProcessing: processing,
      currentJobId: jobId,
    }),

  setProgress: (progress, message) =>
    set({
      progress,
      progressMessage: message,
    }),

  setActiveAssetId: (assetId) => set({ activeAssetId: assetId }),

  // Pipeline status
  setPipelineStatus: (status) =>
    set((state) => ({
      pipelineStatus: { ...state.pipelineStatus, ...status },
    })),

  // Source image
  setSourceImage: (file) => {
    const prevPreview = get().sourceImagePreview;
    if (prevPreview) {
      URL.revokeObjectURL(prevPreview);
    }

    if (file) {
      const preview = URL.createObjectURL(file);
      const name = file.name.replace(/\.[^/.]+$/, '');
      set({
        sourceImage: file,
        sourceImagePreview: preview,
        assetName: get().assetName || name,
      });
    } else {
      set({
        sourceImage: null,
        sourceImagePreview: null,
      });
    }
  },

  setAssetName: (name) => set({ assetName: name }),
}));
