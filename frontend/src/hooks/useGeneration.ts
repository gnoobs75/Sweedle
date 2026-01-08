/**
 * useGeneration Hook - Generation workflow management
 */

import { useCallback, useEffect } from 'react';
import { useGenerationStore } from '../stores/generationStore';
import { useQueueStore } from '../stores/queueStore';
import { useViewerStore } from '../stores/viewerStore';
import { useUIStore } from '../stores/uiStore';
import {
  generateFromImage,
  cancelJob as cancelJobApi,
  getJobStatus,
} from '../services/api/generation';
import { getAssetModelUrl } from '../services/api/assets';
import type { GenerationParameters } from '../types';

interface UseGenerationOptions {
  onSuccess?: (jobId: string, assetId: string) => void;
  onError?: (error: Error) => void;
  onProgress?: (progress: number, stage: string) => void;
}

export function useGeneration(options: UseGenerationOptions = {}) {
  const {
    sourceImage,
    sourceImagePreview,
    assetName,
    parameters,
    isGenerating,
    currentJobId,
    setSourceImage,
    setAssetName,
    setIsGenerating,
    setCurrentJobId,
    reset: resetGeneration,
  } = useGenerationStore();

  const { getJobById, updateJobStatus } = useQueueStore();
  const { loadModel } = useViewerStore();
  const { addNotification } = useUIStore();

  const currentJob = currentJobId ? getJobById(currentJobId) : undefined;

  // Start generation
  const generate = useCallback(
    async (overrides?: Partial<GenerationParameters>) => {
      if (!sourceImage) {
        addNotification({
          type: 'error',
          title: 'No Image',
          message: 'Please upload an image first',
        });
        return null;
      }

      setIsGenerating(true);

      try {
        const response = await generateFromImage({
          file: sourceImage,
          name: assetName || undefined,
          parameters: { ...parameters, ...overrides },
          priority: 'normal',
        });

        setCurrentJobId(response.jobId);

        addNotification({
          type: 'info',
          title: 'Generation Started',
          message: `Added to queue (Position: ${response.queuePosition || 1})`,
        });

        return response;
      } catch (error) {
        setIsGenerating(false);
        const err = error instanceof Error ? error : new Error('Generation failed');

        addNotification({
          type: 'error',
          title: 'Generation Failed',
          message: err.message,
        });

        options.onError?.(err);
        return null;
      }
    },
    [sourceImage, assetName, parameters, setIsGenerating, setCurrentJobId, addNotification, options]
  );

  // Cancel current job
  const cancel = useCallback(async () => {
    if (!currentJobId) return;

    try {
      await cancelJobApi(currentJobId);
      updateJobStatus(currentJobId, 'cancelled');
      setIsGenerating(false);

      addNotification({
        type: 'warning',
        title: 'Generation Cancelled',
        message: 'The job has been cancelled',
      });
    } catch (error) {
      addNotification({
        type: 'error',
        title: 'Cancel Failed',
        message: error instanceof Error ? error.message : 'Failed to cancel job',
      });
    }
  }, [currentJobId, updateJobStatus, setIsGenerating, addNotification]);

  // View generated result
  const viewResult = useCallback(() => {
    if (currentJob?.assetId) {
      loadModel(getAssetModelUrl(currentJob.assetId), currentJob.assetId);
    }
  }, [currentJob, loadModel]);

  // Reset and start new generation
  const reset = useCallback(() => {
    resetGeneration();
  }, [resetGeneration]);

  // Poll job status if needed (backup for WebSocket)
  useEffect(() => {
    if (!currentJobId || !isGenerating) return;

    const pollStatus = async () => {
      try {
        const status = await getJobStatus(currentJobId);
        options.onProgress?.(status.progress, status.stage);

        if (status.status === 'completed') {
          setIsGenerating(false);
          options.onSuccess?.(currentJobId, status.assetId || '');
        } else if (status.status === 'failed') {
          setIsGenerating(false);
          options.onError?.(new Error(status.error || 'Generation failed'));
        }
      } catch (error) {
        console.error('Failed to poll job status:', error);
      }
    };

    // Poll every 5 seconds as backup
    const interval = setInterval(pollStatus, 5000);
    return () => clearInterval(interval);
  }, [currentJobId, isGenerating, setIsGenerating, options]);

  return {
    // State
    sourceImage,
    sourceImagePreview,
    assetName,
    parameters,
    isGenerating,
    currentJob,

    // Actions
    setSourceImage,
    setAssetName,
    generate,
    cancel,
    viewResult,
    reset,

    // Computed
    canGenerate: !!sourceImage && !isGenerating,
    isComplete: currentJob?.status === 'completed',
    isFailed: currentJob?.status === 'failed',
    isProcessing: currentJob?.status === 'processing',
    isPending: currentJob?.status === 'pending',
  };
}
