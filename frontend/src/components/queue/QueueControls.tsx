/**
 * QueueControls Component - Queue management controls
 */

import { useCallback, useState } from 'react';
import { useQueueStore } from '../../stores/queueStore';
import { useUIStore } from '../../stores/uiStore';
import { pauseQueue, resumeQueue, clearQueue } from '../../services/api/generation';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { cn } from '../../lib/utils';

interface QueueControlsProps {
  className?: string;
}

export function QueueControls({ className }: QueueControlsProps) {
  const {
    jobs,
    isPaused,
    setPaused,
    clearCompleted,
    clearAll,
  } = useQueueStore();
  const { addNotification } = useUIStore();

  const [isClearing, setIsClearing] = useState(false);

  const pendingCount = jobs.filter((j) => j.status === 'pending' || j.status === 'queued').length;
  const processingCount = jobs.filter((j) => j.status === 'processing').length;
  const completedCount = jobs.filter((j) => j.status === 'completed').length;
  const failedCount = jobs.filter((j) => j.status === 'failed').length;

  const handlePauseToggle = useCallback(async () => {
    try {
      if (isPaused) {
        await resumeQueue();
        setPaused(false);
        addNotification({
          type: 'info',
          title: 'Queue Resumed',
          message: 'Processing will continue',
        });
      } else {
        await pauseQueue();
        setPaused(true);
        addNotification({
          type: 'info',
          title: 'Queue Paused',
          message: 'No new jobs will be processed',
        });
      }
    } catch (error) {
      addNotification({
        type: 'error',
        title: 'Queue Control Failed',
        message: error instanceof Error ? error.message : 'Failed to update queue',
      });
    }
  }, [isPaused, setPaused, addNotification]);

  const handleClearCompleted = useCallback(() => {
    clearCompleted();
    addNotification({
      type: 'success',
      title: 'Cleared',
      message: `${completedCount} completed job${completedCount !== 1 ? 's' : ''} removed`,
    });
  }, [clearCompleted, completedCount, addNotification]);

  const handleClearAll = useCallback(async () => {
    const confirmed = window.confirm(
      'Are you sure you want to clear all jobs? This will cancel any pending jobs.'
    );
    if (!confirmed) return;

    setIsClearing(true);
    try {
      await clearQueue();
      clearAll();
      addNotification({
        type: 'success',
        title: 'Queue Cleared',
        message: 'All jobs have been removed',
      });
    } catch (error) {
      addNotification({
        type: 'error',
        title: 'Clear Failed',
        message: error instanceof Error ? error.message : 'Failed to clear queue',
      });
    } finally {
      setIsClearing(false);
    }
  }, [clearAll, addNotification]);

  return (
    <div className={cn('space-y-4', className)}>
      {/* Stats */}
      <div className="flex items-center gap-2 flex-wrap">
        {pendingCount > 0 && (
          <Badge variant="default" size="sm">
            {pendingCount} pending
          </Badge>
        )}
        {processingCount > 0 && (
          <Badge variant="info" size="sm">
            {processingCount} processing
          </Badge>
        )}
        {completedCount > 0 && (
          <Badge variant="success" size="sm">
            {completedCount} completed
          </Badge>
        )}
        {failedCount > 0 && (
          <Badge variant="error" size="sm">
            {failedCount} failed
          </Badge>
        )}
        {jobs.length === 0 && (
          <span className="text-sm text-text-muted">No jobs in queue</span>
        )}
      </div>

      {/* Controls */}
      <div className="flex items-center gap-2 flex-wrap">
        <Button
          variant={isPaused ? 'primary' : 'secondary'}
          size="sm"
          onClick={handlePauseToggle}
        >
          {isPaused ? (
            <>
              <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Resume
            </>
          ) : (
            <>
              <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Pause
            </>
          )}
        </Button>

        {completedCount > 0 && (
          <Button variant="ghost" size="sm" onClick={handleClearCompleted}>
            <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            Clear Completed
          </Button>
        )}

        {jobs.length > 0 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={handleClearAll}
            isLoading={isClearing}
            className="text-error hover:bg-error/10"
          >
            <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
            Clear All
          </Button>
        )}
      </div>
    </div>
  );
}

/**
 * Queue status indicator for header
 */
interface QueueStatusProps {
  className?: string;
}

export function QueueStatus({ className }: QueueStatusProps) {
  const { jobs, isPaused } = useQueueStore();

  const activeCount = jobs.filter(
    (j) => j.status === 'processing' || j.status === 'queued' || j.status === 'pending'
  ).length;

  if (activeCount === 0) {
    return null;
  }

  return (
    <div
      className={cn(
        'flex items-center gap-2 px-3 py-1.5 rounded-full',
        'bg-surface-light border border-border',
        className
      )}
    >
      {isPaused ? (
        <svg className="w-4 h-4 text-warning" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ) : (
        <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
      )}
      <span className="text-sm text-text-secondary">
        {activeCount} job{activeCount !== 1 ? 's' : ''} {isPaused ? 'paused' : 'in queue'}
      </span>
    </div>
  );
}
