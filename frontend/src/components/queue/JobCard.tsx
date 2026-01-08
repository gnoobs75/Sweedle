/**
 * JobCard Component - Individual job display with progress and actions
 */

import { useCallback, memo } from 'react';
import { useQueueStore } from '../../stores/queueStore';
import { useUIStore } from '../../stores/uiStore';
import { cancelJob, retryJob } from '../../services/api/generation';
import { Button } from '../ui/Button';
import { ProgressBar } from '../ui/ProgressBar';
import { Badge } from '../ui/Badge';
import { cn, formatRelativeTime, formatDuration } from '../../lib/utils';
import type { GenerationJob } from '../../types';

interface JobCardProps {
  job: GenerationJob;
  className?: string;
}

const STATUS_CONFIG = {
  pending: { label: 'Pending', variant: 'default' as const, color: 'text-text-muted' },
  queued: { label: 'Queued', variant: 'default' as const, color: 'text-text-muted' },
  processing: { label: 'Processing', variant: 'info' as const, color: 'text-info' },
  completed: { label: 'Completed', variant: 'success' as const, color: 'text-success' },
  failed: { label: 'Failed', variant: 'error' as const, color: 'text-error' },
  cancelled: { label: 'Cancelled', variant: 'warning' as const, color: 'text-warning' },
};

const STAGE_LABELS: Record<string, string> = {
  preprocessing: 'Preprocessing image...',
  'shape-generation': 'Generating 3D shape...',
  'texture-generation': 'Generating textures...',
  'post-processing': 'Post-processing...',
};

export const JobCard = memo(function JobCard({ job, className }: JobCardProps) {
  const { removeJob, updateJob } = useQueueStore();
  const { addNotification } = useUIStore();

  const config = STATUS_CONFIG[job.status] || STATUS_CONFIG.pending;

  const handleCancel = useCallback(async () => {
    try {
      await cancelJob(job.id);
      updateJob(job.id, { status: 'cancelled' });
      addNotification({
        type: 'info',
        title: 'Job Cancelled',
        message: `Generation job has been cancelled`,
      });
    } catch (error) {
      addNotification({
        type: 'error',
        title: 'Cancel Failed',
        message: error instanceof Error ? error.message : 'Failed to cancel job',
      });
    }
  }, [job.id, updateJob, addNotification]);

  const handleRetry = useCallback(async () => {
    try {
      await retryJob(job.id);
      updateJob(job.id, { status: 'queued', progress: 0, error: undefined });
      addNotification({
        type: 'info',
        title: 'Job Requeued',
        message: 'Generation job has been added back to the queue',
      });
    } catch (error) {
      addNotification({
        type: 'error',
        title: 'Retry Failed',
        message: error instanceof Error ? error.message : 'Failed to retry job',
      });
    }
  }, [job.id, updateJob, addNotification]);

  const handleRemove = useCallback(() => {
    removeJob(job.id);
  }, [job.id, removeJob]);

  const isActive = job.status === 'processing' || job.status === 'queued';
  const canCancel = job.status === 'pending' || job.status === 'queued' || job.status === 'processing';
  const canRetry = job.status === 'failed' || job.status === 'cancelled';
  const canRemove = job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled';

  return (
    <div
      className={cn(
        'p-4 bg-surface-light rounded-xl border border-border',
        'transition-all duration-200',
        isActive && 'border-primary/30 shadow-lg shadow-primary/5',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <Badge variant={config.variant} size="sm">
              {config.label}
            </Badge>
            <Badge variant="default" size="sm">
              {job.type === 'image_to_3d' ? 'Image to 3D' : 'Text to 3D'}
            </Badge>
          </div>
          <h4 className="text-sm font-medium text-text-primary truncate">
            {job.type === 'image_to_3d' ? 'Image Generation' : job.prompt?.slice(0, 50) || 'Text Generation'}
          </h4>
          <p className="text-xs text-text-muted">
            {formatRelativeTime(job.createdAt)}
          </p>
        </div>

        {/* Thumbnail */}
        {job.sourceImagePath && (
          <div className="w-12 h-12 rounded-lg overflow-hidden bg-surface flex-shrink-0 ml-3">
            <img
              src={job.sourceImagePath}
              alt="Source"
              className="w-full h-full object-cover"
            />
          </div>
        )}
      </div>

      {/* Progress */}
      {job.status === 'processing' && (
        <div className="mb-3">
          <div className="flex items-center justify-between text-xs mb-1">
            <span className="text-text-muted">
              {job.stage ? STAGE_LABELS[job.stage] || job.stage : 'Processing...'}
            </span>
            <span className="text-text-secondary font-mono">
              {Math.round(job.progress)}%
            </span>
          </div>
          <ProgressBar
            value={job.progress}
            max={100}
            variant="primary"
            size="sm"
            animated
          />
          {job.eta && (
            <p className="text-xs text-text-muted mt-1">
              ETA: {formatDuration(job.eta)}
            </p>
          )}
        </div>
      )}

      {/* Error Message */}
      {job.error && (
        <div className="mb-3 p-2 bg-error/10 border border-error/20 rounded-lg">
          <p className="text-xs text-error">{job.error}</p>
        </div>
      )}

      {/* Completed Info */}
      {job.status === 'completed' && job.completedAt && (
        <div className="mb-3 text-xs text-text-muted">
          Completed {formatRelativeTime(job.completedAt)}
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2">
        {canCancel && (
          <Button variant="ghost" size="sm" onClick={handleCancel}>
            <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
            Cancel
          </Button>
        )}

        {canRetry && (
          <Button variant="secondary" size="sm" onClick={handleRetry}>
            <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Retry
          </Button>
        )}

        {canRemove && (
          <Button variant="ghost" size="sm" onClick={handleRemove}>
            <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
            Remove
          </Button>
        )}

        {job.status === 'completed' && job.assetId && (
          <Button variant="primary" size="sm" className="ml-auto">
            <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
            </svg>
            View
          </Button>
        )}
      </div>
    </div>
  );
});

/**
 * Compact job item for queue list
 */
interface JobListItemProps {
  job: GenerationJob;
  onClick?: () => void;
  className?: string;
}

export const JobListItem = memo(function JobListItem({
  job,
  onClick,
  className,
}: JobListItemProps) {
  const config = STATUS_CONFIG[job.status] || STATUS_CONFIG.pending;
  const isActive = job.status === 'processing';

  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full flex items-center gap-3 p-3 rounded-lg',
        'hover:bg-surface-light transition-colors text-left',
        isActive && 'bg-surface-light',
        className
      )}
    >
      {/* Status Indicator */}
      <div
        className={cn(
          'w-2 h-2 rounded-full flex-shrink-0',
          job.status === 'processing' && 'bg-info animate-pulse',
          job.status === 'queued' && 'bg-text-muted',
          job.status === 'completed' && 'bg-success',
          job.status === 'failed' && 'bg-error',
          job.status === 'cancelled' && 'bg-warning'
        )}
      />

      {/* Thumbnail */}
      {job.sourceImagePath ? (
        <div className="w-8 h-8 rounded overflow-hidden bg-surface flex-shrink-0">
          <img
            src={job.sourceImagePath}
            alt=""
            className="w-full h-full object-cover"
          />
        </div>
      ) : (
        <div className="w-8 h-8 rounded bg-surface flex items-center justify-center flex-shrink-0">
          <svg className="w-4 h-4 text-text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
          </svg>
        </div>
      )}

      {/* Info */}
      <div className="flex-1 min-w-0">
        <p className="text-sm text-text-primary truncate">
          {job.type === 'image_to_3d' ? 'Image to 3D' : job.prompt?.slice(0, 30) || 'Text to 3D'}
        </p>
        <p className={cn('text-xs', config.color)}>
          {isActive ? `${Math.round(job.progress)}%` : config.label}
        </p>
      </div>

      {/* Progress for active jobs */}
      {isActive && (
        <div className="w-16">
          <ProgressBar value={job.progress} max={100} size="xs" variant="primary" />
        </div>
      )}
    </button>
  );
});
