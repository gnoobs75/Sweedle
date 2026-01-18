/**
 * Generation Log Store - Manages live generation logs for the modal
 */

import { create } from 'zustand';
import type { LogEntry } from '../components/generation/GenerationLogModal';

interface GenerationLogState {
  // Modal state
  isModalOpen: boolean;

  // Log data
  logs: LogEntry[];
  progress: number;
  stage: string;
  isComplete: boolean;
  isFailed: boolean;
  title: string;

  // Current job tracking
  currentJobId: string | null;
  currentAssetId: string | null;

  // Actions
  openModal: (jobId: string, assetId?: string, title?: string) => void;
  closeModal: () => void;
  addLog: (entry: Omit<LogEntry, 'id' | 'timestamp'>) => void;
  addSystemLog: (message: string) => void;
  setProgress: (progress: number, stage?: string) => void;
  setComplete: () => void;
  setFailed: (error?: string) => void;
  reset: () => void;
}

let logIdCounter = 0;

export const useGenerationLogStore = create<GenerationLogState>((set, get) => ({
  // Initial state
  isModalOpen: false,
  logs: [],
  progress: 0,
  stage: 'Initializing',
  isComplete: false,
  isFailed: false,
  title: 'NEURAL PROCESSING',
  currentJobId: null,
  currentAssetId: null,

  openModal: (jobId, assetId, title) => {
    set({
      isModalOpen: true,
      logs: [],
      progress: 0,
      stage: 'Initializing',
      isComplete: false,
      isFailed: false,
      title: title || 'NEURAL PROCESSING',
      currentJobId: jobId,
      currentAssetId: assetId || null,
    });

    // Add initial system log
    get().addSystemLog('Generation sequence initiated');
  },

  closeModal: () => {
    // Full reset to ensure clean state - prevents gray overlay from persisting
    set({
      isModalOpen: false,
      isComplete: false,
      isFailed: false,
      currentJobId: null,
      currentAssetId: null,
    });
  },

  addLog: (entry) => {
    const newEntry: LogEntry = {
      ...entry,
      id: `log-${++logIdCounter}`,
      timestamp: new Date(),
    };

    set((state) => ({
      logs: [...state.logs, newEntry],
    }));
  },

  addSystemLog: (message) => {
    get().addLog({
      level: 'system',
      stage: 'SYSTEM',
      message,
    });
  },

  setProgress: (progress, stage) => {
    set((state) => ({
      progress,
      stage: stage || state.stage,
    }));
  },

  setComplete: () => {
    get().addLog({
      level: 'success',
      stage: 'COMPLETE',
      message: 'Generation sequence completed successfully',
    });
    set({ isComplete: true, progress: 1 });
  },

  setFailed: (error) => {
    get().addLog({
      level: 'error',
      stage: 'ERROR',
      message: error || 'Generation sequence failed',
    });
    set({ isFailed: true });
  },

  reset: () => {
    set({
      isModalOpen: false,
      logs: [],
      progress: 0,
      stage: 'Initializing',
      isComplete: false,
      isFailed: false,
      currentJobId: null,
      currentAssetId: null,
    });
  },
}));
