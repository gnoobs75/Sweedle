/**
 * AdvancedModePanel Component - Full parameter control
 */

import { useCallback, useState } from 'react';
import { useGenerationStore } from '../../stores/generationStore';
import { useQueueStore } from '../../stores/queueStore';
import { useViewerStore } from '../../stores/viewerStore';
import { useUIStore } from '../../stores/uiStore';
import { generateFromImage } from '../../services/api/generation';
import { getAssetModelUrl } from '../../services/api/assets';
import { ImageUploader } from './ImageUploader';
import { ParameterControls } from './ParameterControls';
import { GenerationProgress } from './GenerationProgress';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Select } from '../ui/Select';
import { Toggle } from '../ui/Toggle';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { cn } from '../../lib/utils';

export function AdvancedModePanel() {
  const {
    sourceImage,
    sourceImagePreview,
    setSourceImage,
    assetName,
    setAssetName,
    parameters,
    setParameter,
    isGenerating,
    setIsGenerating,
    currentJobId,
    setCurrentJobId,
    reset,
  } = useGenerationStore();

  const { getJobById, jobs } = useQueueStore();
  const { loadModel } = useViewerStore();
  const { addNotification } = useUIStore();

  const [priority, setPriority] = useState<'low' | 'normal' | 'high'>('normal');
  const [tags, setTags] = useState<string>('');
  const [showRecentJobs, setShowRecentJobs] = useState(true);

  const currentJob = currentJobId ? getJobById(currentJobId) : undefined;
  const recentJobs = jobs.slice(0, 5);

  const handleGenerate = useCallback(async () => {
    if (!sourceImage) return;

    setIsGenerating(true);

    try {
      const response = await generateFromImage({
        file: sourceImage,
        name: assetName || undefined,
        parameters,
        priority,
        tags: tags ? tags.split(',').map((t) => t.trim()).filter(Boolean) : undefined,
      });

      setCurrentJobId(response.jobId);

      addNotification({
        type: 'info',
        title: 'Job Queued',
        message: `Generation job added to queue (Position: ${response.queuePosition || 1})`,
      });
    } catch (error) {
      setIsGenerating(false);
      addNotification({
        type: 'error',
        title: 'Failed to Queue Job',
        message: error instanceof Error ? error.message : 'An error occurred',
      });
    }
  }, [sourceImage, assetName, parameters, priority, tags, setIsGenerating, setCurrentJobId, addNotification]);

  const handleCancel = useCallback(() => {
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
    setPriority('normal');
    setTags('');
  }, [reset]);

  const handleLoadJob = useCallback((jobId: string) => {
    setCurrentJobId(jobId);
  }, [setCurrentJobId]);

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-text-primary">Advanced Generation</h2>
            <p className="text-sm text-text-muted mt-1">
              Full control over generation parameters
            </p>
          </div>
          <Badge variant="primary" size="sm">
            Advanced
          </Badge>
        </div>
      </div>

      {/* Content - Scrollable */}
      <div className="flex-1 overflow-y-auto">
        {/* Current Job Progress */}
        {currentJob && (currentJob.status === 'processing' || currentJob.status === 'pending') && (
          <div className="p-4 border-b border-border bg-surface-light">
            <GenerationProgress
              jobId={currentJob.id}
              status={currentJob.status}
              progress={currentJob.progress}
              stage={currentJob.stage}
              error={currentJob.error}
              startedAt={currentJob.startedAt}
              onCancel={handleCancel}
            />
          </div>
        )}

        <div className="p-4 space-y-6">
          {/* Image Upload Section */}
          <section>
            <h3 className="text-sm font-semibold text-text-secondary mb-3 flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              Source Image
            </h3>
            <ImageUploader
              value={sourceImage}
              preview={sourceImagePreview}
              onChange={setSourceImage}
              disabled={isGenerating}
            />
          </section>

          {/* Asset Details */}
          <section>
            <h3 className="text-sm font-semibold text-text-secondary mb-3 flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
              </svg>
              Asset Details
            </h3>
            <div className="space-y-3">
              <Input
                label="Asset Name"
                value={assetName}
                onChange={(e) => setAssetName(e.target.value)}
                placeholder="Enter asset name"
                disabled={isGenerating}
              />
              <Input
                label="Tags"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                placeholder="character, fantasy, lowpoly"
                hint="Comma-separated tags for organization"
                disabled={isGenerating}
              />
            </div>
          </section>

          {/* Generation Parameters */}
          <section>
            <h3 className="text-sm font-semibold text-text-secondary mb-3 flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
              </svg>
              Generation Parameters
            </h3>
            <ParameterControls disabled={isGenerating} />
          </section>

          {/* Queue Settings */}
          <section>
            <h3 className="text-sm font-semibold text-text-secondary mb-3 flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
              </svg>
              Queue Settings
            </h3>
            <Select
              label="Priority"
              value={priority}
              onChange={(e) => setPriority(e.target.value as 'low' | 'normal' | 'high')}
              disabled={isGenerating}
              options={[
                { value: 'low', label: 'Low - Process after other jobs' },
                { value: 'normal', label: 'Normal - Standard queue position' },
                { value: 'high', label: 'High - Process sooner' },
              ]}
            />
          </section>

          {/* Recent Jobs */}
          {recentJobs.length > 0 && (
            <section>
              <button
                onClick={() => setShowRecentJobs(!showRecentJobs)}
                className="w-full flex items-center justify-between text-sm font-semibold text-text-secondary mb-3"
              >
                <span className="flex items-center gap-2">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Recent Jobs
                </span>
                <svg
                  className={cn('w-4 h-4 transition-transform', showRecentJobs && 'rotate-180')}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              {showRecentJobs && (
                <div className="space-y-2">
                  {recentJobs.map((job) => (
                    <Card
                      key={job.id}
                      variant="outlined"
                      padding="sm"
                      interactive
                      onClick={() => handleLoadJob(job.id)}
                      className={cn(
                        'flex items-center gap-3',
                        job.id === currentJobId && 'ring-2 ring-primary'
                      )}
                    >
                      <div
                        className={cn(
                          'w-2 h-2 rounded-full',
                          job.status === 'completed' && 'bg-success',
                          job.status === 'processing' && 'bg-primary animate-pulse',
                          job.status === 'pending' && 'bg-text-muted',
                          job.status === 'failed' && 'bg-error'
                        )}
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-text-primary truncate">
                          {job.name || 'Generation Job'}
                        </p>
                        <p className="text-xs text-text-muted">
                          {job.status === 'processing'
                            ? `${Math.round(job.progress * 100)}% - ${job.stage}`
                            : job.status}
                        </p>
                      </div>
                    </Card>
                  ))}
                </div>
              )}
            </section>
          )}
        </div>
      </div>

      {/* Footer Actions */}
      <div className="p-4 border-t border-border space-y-2">
        {currentJob?.status === 'completed' && (
          <div className="flex gap-2">
            <Button
              variant="primary"
              className="flex-1"
              onClick={handleViewResult}
            >
              <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
              View Result
            </Button>
            <Button variant="secondary" onClick={handleNewGeneration}>
              New
            </Button>
          </div>
        )}

        {(!currentJob || currentJob.status === 'failed' || currentJob.status === 'cancelled') && (
          <Button
            className="w-full"
            size="lg"
            disabled={!sourceImage || isGenerating}
            isLoading={isGenerating}
            onClick={handleGenerate}
          >
            {isGenerating ? (
              'Adding to Queue...'
            ) : (
              <>
                <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Add to Queue
              </>
            )}
          </Button>
        )}

        {currentJob?.status === 'failed' && (
          <Button
            variant="secondary"
            className="w-full"
            onClick={handleGenerate}
            disabled={!sourceImage}
          >
            <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Retry Generation
          </Button>
        )}
      </div>
    </div>
  );
}
