/**
 * ImageQualityIndicator Component - Shows image quality analysis for 3D generation
 */

import { cn } from '../../lib/utils';

export interface QualityCheck {
  name: string;
  passed: boolean;
  score: number;
  message: string;
  suggestion?: string;
}

export interface ImageAnalysis {
  overall_score: number;
  quality_level: 'excellent' | 'good' | 'fair' | 'poor';
  checks: QualityCheck[];
  warnings: string[];
  tips: string[];
}

interface ImageQualityIndicatorProps {
  analysis: ImageAnalysis | null;
  isLoading?: boolean;
  error?: string | null;
  className?: string;
}

const QUALITY_COLORS = {
  excellent: 'text-success',
  good: 'text-primary',
  fair: 'text-warning',
  poor: 'text-error',
};

const QUALITY_BG_COLORS = {
  excellent: 'bg-success/10 border-success/30',
  good: 'bg-primary/10 border-primary/30',
  fair: 'bg-warning/10 border-warning/30',
  poor: 'bg-error/10 border-error/30',
};

const QUALITY_LABELS = {
  excellent: 'Excellent',
  good: 'Good',
  fair: 'Fair',
  poor: 'Poor',
};

const QUALITY_ICONS = {
  excellent: (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  good: (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5" />
    </svg>
  ),
  fair: (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
    </svg>
  ),
  poor: (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
};

const CHECK_ICONS: Record<string, JSX.Element> = {
  resolution: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
    </svg>
  ),
  aspect_ratio: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6z" />
    </svg>
  ),
  background: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01" />
    </svg>
  ),
  centering: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
    </svg>
  ),
  sharpness: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
    </svg>
  ),
  coverage: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v3m0 0v3m0-3h3m-3 0H7" />
    </svg>
  ),
  contrast: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
    </svg>
  ),
};

export function ImageQualityIndicator({
  analysis,
  isLoading,
  error,
  className,
}: ImageQualityIndicatorProps) {
  if (isLoading) {
    return (
      <div className={cn('rounded-lg border border-border p-3 bg-surface', className)}>
        <div className="flex items-center gap-2 text-text-muted">
          <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          <span className="text-sm">Analyzing image...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={cn('rounded-lg border border-error/30 p-3 bg-error/10', className)}>
        <div className="flex items-center gap-2 text-error">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="text-sm">{error}</span>
        </div>
      </div>
    );
  }

  if (!analysis) return null;

  const { overall_score, quality_level, checks, warnings, tips } = analysis;

  return (
    <div className={cn('space-y-3', className)}>
      {/* Overall Score Header */}
      <div className={cn(
        'rounded-lg border p-3 flex items-center justify-between',
        QUALITY_BG_COLORS[quality_level]
      )}>
        <div className="flex items-center gap-2">
          <span className={QUALITY_COLORS[quality_level]}>
            {QUALITY_ICONS[quality_level]}
          </span>
          <div>
            <span className={cn('font-medium', QUALITY_COLORS[quality_level])}>
              {QUALITY_LABELS[quality_level]} for 3D
            </span>
            <span className="text-text-muted text-sm ml-2">
              ({Math.round(overall_score * 100)}% quality score)
            </span>
          </div>
        </div>
      </div>

      {/* Quality Checks */}
      <div className="grid grid-cols-2 gap-2">
        {checks.map((check) => (
          <div
            key={check.name}
            className={cn(
              'flex items-center gap-2 p-2 rounded-md text-sm',
              check.passed ? 'bg-surface' : 'bg-warning/5'
            )}
            title={check.suggestion || check.message}
          >
            <span className={cn(
              'flex-shrink-0',
              check.passed ? 'text-success' : 'text-warning'
            )}>
              {check.passed ? (
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              ) : (
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              )}
            </span>
            <span className="text-text-muted flex-shrink-0">
              {CHECK_ICONS[check.name] || null}
            </span>
            <span className={cn(
              'truncate',
              check.passed ? 'text-text-secondary' : 'text-text-primary'
            )}>
              {check.message}
            </span>
          </div>
        ))}
      </div>

      {/* Warnings */}
      {warnings.length > 0 && (
        <div className="space-y-1">
          {warnings.map((warning, i) => (
            <div key={i} className="flex items-start gap-2 text-sm text-warning">
              <svg className="w-4 h-4 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>{warning}</span>
            </div>
          ))}
        </div>
      )}

      {/* Tips */}
      {tips.length > 0 && quality_level !== 'poor' && (
        <div className="text-xs text-text-muted italic">
          {tips[0]}
        </div>
      )}
    </div>
  );
}

/**
 * Compact quality badge for minimal display
 */
export function ImageQualityBadge({
  analysis,
  isLoading,
  className,
}: {
  analysis: ImageAnalysis | null;
  isLoading?: boolean;
  className?: string;
}) {
  if (isLoading) {
    return (
      <div className={cn('inline-flex items-center gap-1 text-xs text-text-muted', className)}>
        <svg className="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        <span>Analyzing...</span>
      </div>
    );
  }

  if (!analysis) return null;

  const { quality_level, overall_score } = analysis;

  return (
    <div className={cn(
      'inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium',
      QUALITY_BG_COLORS[quality_level],
      QUALITY_COLORS[quality_level],
      className
    )}>
      {QUALITY_ICONS[quality_level]}
      <span>{QUALITY_LABELS[quality_level]}</span>
      <span className="opacity-70">({Math.round(overall_score * 100)}%)</span>
    </div>
  );
}
