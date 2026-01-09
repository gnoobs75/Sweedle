/**
 * RiggingProgress - Display rigging progress with stages.
 */

import type { CharacterType } from '../../stores/riggingStore';

interface RiggingProgressProps {
  progress: number;
  stage: string;
  detectedType?: CharacterType | null;
}

const STAGES = [
  { key: 'loading', label: 'Loading mesh', range: [0, 0.15] },
  { key: 'analyzing', label: 'Analyzing character', range: [0.15, 0.25] },
  { key: 'skeleton', label: 'Creating skeleton', range: [0.25, 0.50] },
  { key: 'weights', label: 'Computing weights', range: [0.50, 0.75] },
  { key: 'exporting', label: 'Exporting mesh', range: [0.75, 1.0] },
];

export function RiggingProgress({ progress, stage, detectedType }: RiggingProgressProps) {
  const progressPercent = Math.round(progress * 100);

  // Determine current stage index
  const currentStageIndex = STAGES.findIndex(
    (s) => progress >= s.range[0] && progress < s.range[1]
  );

  return (
    <div className="py-8">
      {/* Progress Circle */}
      <div className="relative w-32 h-32 mx-auto mb-6">
        <svg className="w-full h-full transform -rotate-90">
          {/* Background circle */}
          <circle
            cx="64"
            cy="64"
            r="56"
            fill="none"
            stroke="currentColor"
            strokeWidth="8"
            className="text-surface-light"
          />
          {/* Progress circle */}
          <circle
            cx="64"
            cy="64"
            r="56"
            fill="none"
            stroke="currentColor"
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={`${progress * 352} 352`}
            className="text-primary transition-all duration-300"
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-2xl font-bold text-text-primary">{progressPercent}%</span>
        </div>
      </div>

      {/* Current Stage */}
      <div className="text-center mb-6">
        <p className="text-lg font-medium text-text-primary">{stage || 'Preparing...'}</p>
        {detectedType && (
          <p className="text-sm text-text-muted mt-1">
            Detected: <span className="text-primary capitalize">{detectedType}</span>
          </p>
        )}
      </div>

      {/* Stage Indicators */}
      <div className="max-w-sm mx-auto">
        {STAGES.map((s, index) => {
          const isComplete = progress >= s.range[1];
          const isCurrent = index === currentStageIndex;

          return (
            <div key={s.key} className="flex items-center gap-3 py-2">
              {/* Status icon */}
              <div
                className={`w-6 h-6 rounded-full flex items-center justify-center ${
                  isComplete
                    ? 'bg-success text-white'
                    : isCurrent
                    ? 'bg-primary text-white'
                    : 'bg-surface-light text-text-muted'
                }`}
              >
                {isComplete ? (
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                ) : isCurrent ? (
                  <div className="w-2 h-2 bg-white rounded-full animate-pulse" />
                ) : (
                  <div className="w-2 h-2 bg-current rounded-full opacity-50" />
                )}
              </div>

              {/* Label */}
              <span
                className={`text-sm ${
                  isComplete || isCurrent ? 'text-text-primary' : 'text-text-muted'
                }`}
              >
                {s.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
