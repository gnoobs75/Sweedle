/**
 * Queue Store - Manages job queue state
 */

import { create } from 'zustand';
import type { GenerationJob, JobStatus, QueueStatus } from '../types';

interface QueueState {
  // Jobs
  jobs: GenerationJob[];
  currentJobId: string | null;
  selectedJobId: string | null;

  // Queue status
  queueStatus: QueueStatus;
  isPaused: boolean;

  // UI state
  isLoading: boolean;
  error: string | null;
  showCompletedJobs: boolean;

  // Actions
  setJobs: (jobs: GenerationJob[]) => void;
  addJob: (job: GenerationJob) => void;
  updateJob: (id: string, updates: Partial<GenerationJob>) => void;
  removeJob: (id: string) => void;
  clearCompletedJobs: () => void;
  clearCompleted: () => void;
  clearAll: () => void;

  // Job status updates
  updateJobProgress: (id: string, progress: number, stage: string) => void;
  updateJobStatus: (id: string, status: JobStatus, error?: string) => void;

  // Queue status
  setQueueStatus: (status: QueueStatus) => void;
  setCurrentJobId: (id: string | null) => void;
  setSelectedJob: (id: string | null) => void;
  setPaused: (paused: boolean) => void;

  // UI
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setShowCompletedJobs: (show: boolean) => void;

  // Helpers
  getJobById: (id: string) => GenerationJob | undefined;
  getPendingJobs: () => GenerationJob[];
  getProcessingJobs: () => GenerationJob[];
  getCompletedJobs: () => GenerationJob[];
  getFailedJobs: () => GenerationJob[];
}

const defaultQueueStatus: QueueStatus = {
  queueSize: 0,
  currentJobId: undefined,
  pendingCount: 0,
  processingCount: 0,
  completedCount: 0,
  failedCount: 0,
};

export const useQueueStore = create<QueueState>((set, get) => ({
  // Initial state
  jobs: [],
  currentJobId: null,
  selectedJobId: null,
  queueStatus: { ...defaultQueueStatus },
  isPaused: false,
  isLoading: false,
  error: null,
  showCompletedJobs: false,

  // Job actions
  setJobs: (jobs) => set({ jobs, error: null }),

  addJob: (job) =>
    set((state) => ({
      jobs: [job, ...state.jobs],
      queueStatus: {
        ...state.queueStatus,
        queueSize: state.queueStatus.queueSize + 1,
        pendingCount: state.queueStatus.pendingCount + 1,
      },
    })),

  updateJob: (id, updates) =>
    set((state) => ({
      jobs: state.jobs.map((j) => (j.id === id ? { ...j, ...updates } : j)),
    })),

  removeJob: (id) =>
    set((state) => {
      const job = state.jobs.find((j) => j.id === id);
      if (!job) return state;

      const statusCounts = { ...state.queueStatus };
      if (job.status === 'pending') statusCounts.pendingCount--;
      else if (job.status === 'processing') statusCounts.processingCount--;
      else if (job.status === 'completed') statusCounts.completedCount--;
      else if (job.status === 'failed') statusCounts.failedCount--;

      return {
        jobs: state.jobs.filter((j) => j.id !== id),
        queueStatus: {
          ...statusCounts,
          queueSize: statusCounts.pendingCount + statusCounts.processingCount,
        },
      };
    }),

  clearCompletedJobs: () =>
    set((state) => ({
      jobs: state.jobs.filter(
        (j) => j.status !== 'completed' && j.status !== 'failed'
      ),
      queueStatus: {
        ...state.queueStatus,
        completedCount: 0,
        failedCount: 0,
      },
    })),

  clearCompleted: () =>
    set((state) => ({
      jobs: state.jobs.filter(
        (j) => j.status !== 'completed' && j.status !== 'failed' && j.status !== 'cancelled'
      ),
      queueStatus: {
        ...state.queueStatus,
        completedCount: 0,
        failedCount: 0,
      },
    })),

  clearAll: () =>
    set({
      jobs: [],
      queueStatus: { ...defaultQueueStatus },
      currentJobId: null,
      selectedJobId: null,
    }),

  // Progress updates
  updateJobProgress: (id, progress, stage) =>
    set((state) => ({
      jobs: state.jobs.map((j) =>
        j.id === id ? { ...j, progress, stage } : j
      ),
    })),

  updateJobStatus: (id, status, error) =>
    set((state) => {
      const job = state.jobs.find((j) => j.id === id);
      if (!job) return state;

      const oldStatus = job.status;
      const statusCounts = { ...state.queueStatus };

      // Decrement old status count
      if (oldStatus === 'pending') statusCounts.pendingCount--;
      else if (oldStatus === 'processing') statusCounts.processingCount--;
      else if (oldStatus === 'completed') statusCounts.completedCount--;
      else if (oldStatus === 'failed') statusCounts.failedCount--;

      // Increment new status count
      if (status === 'pending') statusCounts.pendingCount++;
      else if (status === 'processing') statusCounts.processingCount++;
      else if (status === 'completed') statusCounts.completedCount++;
      else if (status === 'failed') statusCounts.failedCount++;

      statusCounts.queueSize =
        statusCounts.pendingCount + statusCounts.processingCount;

      return {
        jobs: state.jobs.map((j) =>
          j.id === id
            ? {
                ...j,
                status,
                error,
                ...(status === 'processing' ? { startedAt: new Date().toISOString() } : {}),
                ...(status === 'completed' || status === 'failed'
                  ? { completedAt: new Date().toISOString() }
                  : {}),
              }
            : j
        ),
        queueStatus: statusCounts,
        currentJobId: status === 'processing' ? id : state.currentJobId,
      };
    }),

  // Queue status
  setQueueStatus: (status) => set({ queueStatus: status }),

  setCurrentJobId: (id) =>
    set((state) => ({
      currentJobId: id,
      queueStatus: { ...state.queueStatus, currentJobId: id || undefined },
    })),

  setSelectedJob: (id) => set({ selectedJobId: id }),

  setPaused: (isPaused) => set({ isPaused }),

  // UI actions
  setLoading: (isLoading) => set({ isLoading }),

  setError: (error) => set({ error, isLoading: false }),

  setShowCompletedJobs: (show) => set({ showCompletedJobs: show }),

  // Helpers
  getJobById: (id) => get().jobs.find((j) => j.id === id),

  getPendingJobs: () => get().jobs.filter((j) => j.status === 'pending'),

  getProcessingJobs: () => get().jobs.filter((j) => j.status === 'processing'),

  getCompletedJobs: () => get().jobs.filter((j) => j.status === 'completed'),

  getFailedJobs: () => get().jobs.filter((j) => j.status === 'failed'),
}));
