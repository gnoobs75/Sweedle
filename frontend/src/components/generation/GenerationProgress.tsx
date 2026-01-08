/**
 * GenerationProgress Component - Job progress display with stages
 */

import { useMemo } from 'react';
import { ProgressBar } from '../ui/ProgressBar';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { cn } from '../../lib/utils';
import { formatDuration } from '../../lib/utils';
import type { JobStatus } from '../../types';

interface GenerationProgressProps {
  jobId: string;
  status: JobStatus;
  progress: number;
  stage?: string;
  error?: string;
  startedAt?: string;
  onCancel?: () => void;
  onRetry?: () => void;
  onViewResult?: () => void;
  className?: string;
}

const STAGES = [
  { id: 'preprocessing', label: 'Preprocessing', icon: '1' },
  { id: 'shape', label: 'Shape Generation', icon: '2' },
  { id: 'texture', label: 'Texture Generation', icon: '3' },
  { id: 'export', label: 'Exporting', icon: '4' },
];

function getStageIndex(stage: string): number {
  const stageLower = stage.toLowerCase();
  if (stageLower.includes('preprocess') || stageLower.includes('background')) {
    return 0;
  }
  if (stageLower.includes('shape') || stageLower.includes('mesh') || stageLower.includes('geometry')) {
    return 1;
  }
  if (stageLower.includes('texture') || stageLower.includes('material')) {
    return 2;
  }
  if (stageLower.includes('export') || stageLower.includes('saving') || stageLower.includes('complete')) {
    return 3;
  }
  return -1;
}

export function GenerationProgress({
  jobId,
  status,
  progress,
  stage,
  error,
  startedAt,
  onCancel,
  onRetry,
  onViewResult,
  className,
}: GenerationProgressProps) {
  const currentStageIndex = useMemo(() => getStageIndex(stage || ''), [stage]);

  const elapsedTime = useMemo(() => {
    if (!startedAt) return null;
    const start = new Date(startedAt).getTime();
    const now = Date.now();
    return Math.floor((now - start) / 1000);
  }, [startedAt]);

  const statusBadgeVariant = useMemo(() => {
    switch (status) {
      case 'pending':
        return 'default';
      case 'processing':
        return 'primary';
      case 'completed':
        return 'success';
      case 'failed':
        return 'error';
      case 'cancelled':
        return 'warning';
      default:
        return 'default';
    }
  }, [status]);

  const isActive = status === 'pending' || status === 'processing';
  const isComplete = status === 'completed';
  const isFailed = status === 'failed' || status === 'cancelled';

  return (
    <div className={cn('rounded-xl bg-surface border border-border p-4', className)}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Badge variant={statusBadgeVariant} dot>
            {status === 'processing' ? 'Generating' : status}
          </Badge>
          {elapsedTime !== null && isActive && (
            <span className="text-xs text-text-muted">
              {formatDuration(elapsedTime)}
            </span>
          )}
        </div>
        {isActive && onCancel && (
          <Button variant="ghost" size="sm" onClick={onCancel}>
            Cancel
          </Button>
        )}
      </div>

      {/* Stage Indicators */}
      <div className="flex items-center gap-2 mb-4">
        {STAGES.map((stageItem, index) => {
          const isCurrentStage = index === currentStageIndex;
          const isPastStage = index < currentStageIndex;
          const isFutureStage = index > currentStageIndex;

          return (
            <div key={stageItem.id} className="flex-1 flex items-center">
              {/* Stage Dot */}
              <div
                className={cn(
                  'w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium transition-all',
                  isPastStage && 'bg-success text-white',
                  isCurrentStage && isActive && 'bg-primary text-white animate-pulse',
                  isCurrentStage && isComplete && 'bg-success text-white',
                  isCurrentStage && isFailed && 'bg-error text-white',
                  isFutureStage && 'bg-surface-lighter text-text-muted'
                )}
              >
                {isPastStage ? (
                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  stageItem.icon
                )}
              </div>
              {/* Connector Line */}
              {index < STAGES.length - 1 && (
                <div
                  className={cn(
                    'flex-1 h-0.5 mx-1 transition-all',
                    isPastStage ? 'bg-success' : 'bg-surface-lighter'
                  )}
                />
              )}
            </div>
          );
        })}
      </div>

      {/* Stage Labels */}
      <div className="flex items-center gap-2 mb-4">
        {STAGES.map((stageItem, index) => {
          const isCurrentStage = index === currentStageIndex;
          return (
            <div key={stageItem.id} className="flex-1">
              <p
                className={cn(
                  'text-xs text-center transition-colors',
                  isCurrentStage ? 'text-text-primary font-medium' : 'text-text-muted'
                )}
              >
                {stageItem.label}
              </p>
            </div>
          );
        })}
      </div>

      {/* Progress Bar */}
      {isActive && (
        <ProgressBar
          value={progress * 100}
          showValue
          size="md"
          animated={status === 'processing'}
          className="mb-3"
        />
      )}

      {/* Current Stage Description */}
      {isActive && (
        <p className="text-sm text-text-secondary text-center">
          {stage || 'Starting...'}
        </p>
      )}

      {/* Error Message */}
      {isFailed && error && (
        <div className="mt-3 p-3 rounded-lg bg-error/10 border border-error/20">
          <div className="flex items-start gap-2">
            <svg
              className="w-5 h-5 text-error flex-shrink-0 mt-0.5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <div>
              <p className="text-sm font-medium text-error">Generation Failed</p>
              <p className="text-sm text-text-muted mt-1">{error}</p>
            </div>
          </div>
          {onRetry && (
            <Button
              variant="secondary"
              size="sm"
              onClick={onRetry}
              className="mt-3 w-full"
            >
              <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Retry
            </Button>
          )}
        </div>
      )}

      {/* Success State */}
      {isComplete && (
        <div className="mt-3 p-3 rounded-lg bg-success/10 border border-success/20">
          <div className="flex items-center gap-2">
            <svg
              className="w-5 h-5 text-success"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <p className="text-sm font-medium text-success">Generation Complete!</p>
          </div>
          {onViewResult && (
            <Button
              variant="primary"
              size="sm"
              onClick={onViewResult}
              className="mt-3 w-full"
            >
              <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
              View Result
            </Button>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Compact progress indicator for queue/list view
 */
export function CompactProgress({
  status,
  progress,
  stage,
  className,
}: Pick<GenerationProgressProps, 'status' | 'progress' | 'stage' | 'className'>) {
  return (
    <div className={cn('space-y-1', className)}>
      <div className="flex items-center justify-between text-xs">
        <span className="text-text-muted">{stage || 'Waiting...'}</span>
        <span className="text-text-secondary font-mono">
          {Math.round(progress * 100)}%
        </span>
      </div>
      <ProgressBar
        value={progress * 100}
        size="sm"
        variant={status === 'failed' ? 'error' : 'default'}
        animated={status === 'processing'}
      />
    </div>
  );
}
