/**
 * ViewerStates Component - Empty, loading, and error states
 */

import { Button } from '../ui/Button';
import { Spinner } from '../ui/Spinner';
import { cn } from '../../lib/utils';

interface EmptyStateProps {
  className?: string;
}

export function EmptyState({ className }: EmptyStateProps) {
  return (
    <div
      className={cn(
        'absolute inset-0 flex items-center justify-center',
        className
      )}
    >
      <div className="text-center max-w-sm">
        <svg
          className="w-24 h-24 mx-auto text-text-muted opacity-30 mb-4"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1}
            d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"
          />
        </svg>
        <h3 className="text-lg font-medium text-text-secondary mb-2">
          No Model Loaded
        </h3>
        <p className="text-text-muted text-sm">
          Generate a new 3D model or select one from your library to preview it here.
        </p>
      </div>
    </div>
  );
}

interface LoadingStateProps {
  message?: string;
  progress?: number;
  className?: string;
}

export function LoadingState({
  message = 'Loading model...',
  progress,
  className,
}: LoadingStateProps) {
  return (
    <div
      className={cn(
        'absolute inset-0 flex items-center justify-center bg-background/80 backdrop-blur-sm z-10',
        className
      )}
    >
      <div className="text-center">
        <Spinner size="lg" variant="primary" className="mb-4" />
        <p className="text-sm text-text-secondary">{message}</p>
        {progress !== undefined && (
          <p className="text-xs text-text-muted mt-1">
            {Math.round(progress)}%
          </p>
        )}
      </div>
    </div>
  );
}

interface ErrorStateProps {
  error: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorState({ error, onRetry, className }: ErrorStateProps) {
  return (
    <div
      className={cn(
        'absolute inset-0 flex items-center justify-center',
        className
      )}
    >
      <div className="text-center max-w-sm">
        <svg
          className="w-16 h-16 mx-auto text-error mb-4"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          />
        </svg>
        <h3 className="text-lg font-medium text-error mb-2">
          Failed to Load Model
        </h3>
        <p className="text-text-muted text-sm mb-4">{error}</p>
        {onRetry && (
          <Button variant="secondary" onClick={onRetry}>
            <svg
              className="w-4 h-4 mr-2"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            Try Again
          </Button>
        )}
      </div>
    </div>
  );
}

/**
 * Controls hint overlay
 */
export function ControlsHint({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        'absolute bottom-4 left-4 text-xs text-text-muted bg-surface/80 backdrop-blur-sm rounded-lg px-3 py-2',
        className
      )}
    >
      <div className="flex items-center gap-4">
        <span>
          <kbd className="px-1 py-0.5 bg-surface-lighter rounded text-text-secondary">
            LMB
          </kbd>{' '}
          Rotate
        </span>
        <span>
          <kbd className="px-1 py-0.5 bg-surface-lighter rounded text-text-secondary">
            RMB
          </kbd>{' '}
          Pan
        </span>
        <span>
          <kbd className="px-1 py-0.5 bg-surface-lighter rounded text-text-secondary">
            Scroll
          </kbd>{' '}
          Zoom
        </span>
      </div>
    </div>
  );
}
