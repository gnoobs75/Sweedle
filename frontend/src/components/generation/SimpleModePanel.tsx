/**
 * SimpleModePanel Component - 3-click generation workflow
 */

import { useCallback } from 'react';
import { useGenerationStore } from '../../stores/generationStore';
import { useQueueStore } from '../../stores/queueStore';
import { useViewerStore } from '../../stores/viewerStore';
import { useUIStore } from '../../stores/uiStore';
import { generateFromImage } from '../../services/api/generation';
import { getAssetModelUrl } from '../../services/api/assets';
import { ImageUploader } from './ImageUploader';
import { SimpleParameterControls } from './ParameterControls';
import { GenerationProgress } from './GenerationProgress';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { cn } from '../../lib/utils';
import { logger } from '../../lib/logger';

export function SimpleModePanel() {
  const {
    sourceImage,
    sourceImagePreview,
    setSourceImage,
    assetName,
    setAssetName,
    parameters,
    isGenerating,
    setIsGenerating,
    currentJobId,
    setCurrentJobId,
    reset,
  } = useGenerationStore();

  const { getJobById } = useQueueStore();
  const { loadModel } = useViewerStore();
  const { addNotification } = useUIStore();

  const currentJob = currentJobId ? getJobById(currentJobId) : undefined;

  const handleGenerate = useCallback(async () => {
    if (!sourceImage) {
      logger.warn('Generation', 'No source image selected');
      return;
    }

    logger.info('Generation', 'Starting generation request', {
      fileName: sourceImage.name,
      fileSize: sourceImage.size,
      assetName,
      mode: parameters.mode,
      inferenceSteps: parameters.inferenceSteps
    });

    setIsGenerating(true);

    try {
      const response = await generateFromImage({
        file: sourceImage,
        name: assetName || undefined,
        parameters,
        priority: 'normal',
      });

      logger.info('Generation', 'Job queued successfully', {
        jobId: response.jobId,
        assetId: response.assetId,
        queuePosition: response.queuePosition
      });

      setCurrentJobId(response.jobId);

      addNotification({
        type: 'info',
        title: 'Generation Started',
        message: `Your 3D model is being generated (Queue position: ${response.queuePosition || 1})`,
      });
    } catch (error) {
      logger.error('Generation', 'Generation request failed', error);
      setIsGenerating(false);
      addNotification({
        type: 'error',
        title: 'Generation Failed',
        message: error instanceof Error ? error.message : 'Failed to start generation',
      });
    }
  }, [sourceImage, assetName, parameters, setIsGenerating, setCurrentJobId, addNotification]);

  const handleCancel = useCallback(() => {
    // Cancel logic will be implemented when we have the cancel API
    setIsGenerating(false);
    setCurrentJobId(null);
  }, [setIsGenerating, setCurrentJobId]);

  const handleViewResult = useCallback(() => {
    if (currentJob?.assetId) {
      loadModel(getAssetModelUrl(currentJob.assetId), currentJob.assetId);
    }
  }, [currentJob, loadModel]);

  const handleNewGeneration = useCallback(() => {
    reset();
  }, [reset]);

  // Show progress if generating
  if (currentJob && (isGenerating || currentJob.status === 'completed' || currentJob.status === 'failed')) {
    return (
      <div className="h-full flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-border">
          <h2 className="text-lg font-semibold text-text-primary">Generate</h2>
          <p className="text-sm text-text-muted mt-1">
            {currentJob.status === 'completed'
              ? 'Your 3D model is ready!'
              : currentJob.status === 'failed'
              ? 'Generation failed'
              : 'Creating your 3D model...'}
          </p>
        </div>

        {/* Progress */}
        <div className="flex-1 overflow-y-auto p-4">
          {/* Source Image Preview */}
          {sourceImagePreview && (
            <div className="mb-4">
              <img
                src={sourceImagePreview}
                alt="Source"
                className="w-full rounded-xl object-contain max-h-40"
              />
            </div>
          )}

          <GenerationProgress
            jobId={currentJob.id}
            status={currentJob.status}
            progress={currentJob.progress}
            stage={currentJob.stage}
            error={currentJob.error}
            startedAt={currentJob.startedAt}
            onCancel={handleCancel}
            onViewResult={handleViewResult}
          />
        </div>

        {/* Actions */}
        <div className="p-4 border-t border-border">
          {(currentJob.status === 'completed' || currentJob.status === 'failed') && (
            <Button
              variant="secondary"
              className="w-full"
              onClick={handleNewGeneration}
            >
              <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              New Generation
            </Button>
          )}
        </div>
      </div>
    );
  }

  // Show upload and generate form
  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-border">
        <h2 className="text-lg font-semibold text-text-primary">Generate</h2>
        <p className="text-sm text-text-muted mt-1">
          Drop an image to create a 3D model
        </p>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Step 1: Upload Image */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <div className="w-6 h-6 rounded-full bg-primary flex items-center justify-center text-xs font-bold text-white">
              1
            </div>
            <span className="text-sm font-medium text-text-primary">
              Upload Image
            </span>
          </div>
          <ImageUploader
            value={sourceImage}
            preview={sourceImagePreview}
            onChange={setSourceImage}
            disabled={isGenerating}
          />
        </div>

        {/* Step 2: Name (Optional) */}
        {sourceImagePreview && (
          <div className="animate-fadeIn">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-6 h-6 rounded-full bg-primary flex items-center justify-center text-xs font-bold text-white">
                2
              </div>
              <span className="text-sm font-medium text-text-primary">
                Name Your Asset
              </span>
              <span className="text-xs text-text-muted">(optional)</span>
            </div>
            <Input
              value={assetName}
              onChange={(e) => setAssetName(e.target.value)}
              placeholder="Enter asset name"
              disabled={isGenerating}
            />
          </div>
        )}

        {/* Step 3: Quality */}
        {sourceImagePreview && (
          <div className="animate-fadeIn">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-6 h-6 rounded-full bg-primary flex items-center justify-center text-xs font-bold text-white">
                3
              </div>
              <span className="text-sm font-medium text-text-primary">
                Choose Quality
              </span>
            </div>
            <SimpleParameterControls disabled={isGenerating} />
          </div>
        )}
      </div>

      {/* Generate Button */}
      <div className="p-4 border-t border-border">
        <Button
          className="w-full"
          size="lg"
          disabled={!sourceImage || isGenerating}
          isLoading={isGenerating}
          onClick={handleGenerate}
        >
          {isGenerating ? (
            'Generating...'
          ) : (
            <>
              <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
              </svg>
              Generate 3D Model
            </>
          )}
        </Button>
        {sourceImage && (
          <p className="text-xs text-text-muted text-center mt-2">
            Estimated time: ~{parameters.mode === 'fast' ? '30 seconds' : parameters.mode === 'quality' ? '2 minutes' : '1 minute'}
          </p>
        )}
      </div>
    </div>
  );
}
