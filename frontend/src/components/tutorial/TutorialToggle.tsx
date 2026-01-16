/**
 * TutorialToggle - Toggle button for enabling/disabling Tutorial Mode
 */

import { useSettingsStore } from '../../stores/settingsStore';

interface TutorialToggleProps {
  /** Compact mode shows just an icon button */
  compact?: boolean;
  /** Show label text */
  showLabel?: boolean;
  /** Additional CSS classes */
  className?: string;
}

export function TutorialToggle({
  compact = false,
  showLabel = true,
  className = '',
}: TutorialToggleProps) {
  const { tutorialMode, toggleTutorialMode, resetDismissedTutorials, dismissedTutorials } =
    useSettingsStore();

  if (compact) {
    return (
      <button
        onClick={toggleTutorialMode}
        className={`p-2 rounded-lg transition-colors ${
          tutorialMode
            ? 'bg-indigo-600/20 text-indigo-400 hover:bg-indigo-600/30'
            : 'bg-gray-700/50 text-gray-400 hover:bg-gray-700 hover:text-white'
        } ${className}`}
        title={tutorialMode ? 'Tutorial Mode: ON (click to disable)' : 'Tutorial Mode: OFF (click to enable)'}
      >
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
          />
        </svg>
      </button>
    );
  }

  return (
    <div className={`space-y-3 ${className}`}>
      {/* Main Toggle */}
      <div className="flex items-center justify-between">
        {showLabel && (
          <div className="flex items-center gap-2">
            <svg
              className="w-5 h-5 text-indigo-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
              />
            </svg>
            <span className="text-sm font-medium text-white">Tutorial Mode</span>
          </div>
        )}

        <button
          onClick={toggleTutorialMode}
          className={`relative w-11 h-6 rounded-full transition-colors ${
            tutorialMode ? 'bg-indigo-600' : 'bg-gray-600'
          }`}
          role="switch"
          aria-checked={tutorialMode}
          aria-label="Toggle tutorial mode"
        >
          <span
            className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${
              tutorialMode ? 'translate-x-5' : 'translate-x-0'
            }`}
          />
        </button>
      </div>

      {/* Description */}
      <p className="text-xs text-gray-400">
        {tutorialMode
          ? 'Detailed guides and terminology are shown for each workflow stage.'
          : 'Enable to see step-by-step guides and terminology explanations.'}
      </p>

      {/* Reset dismissed tutorials */}
      {tutorialMode && dismissedTutorials.length > 0 && (
        <button
          onClick={resetDismissedTutorials}
          className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
        >
          Reset {dismissedTutorials.length} dismissed tutorial(s)
        </button>
      )}
    </div>
  );
}

/**
 * Floating tutorial mode indicator
 */
export function TutorialModeIndicator() {
  const { tutorialMode, toggleTutorialMode } = useSettingsStore();

  if (!tutorialMode) return null;

  return (
    <button
      onClick={toggleTutorialMode}
      className="fixed bottom-4 right-4 z-50 flex items-center gap-2 px-3 py-2 bg-indigo-600/90 text-white text-sm font-medium rounded-full shadow-lg hover:bg-indigo-500 transition-colors"
      title="Click to disable Tutorial Mode"
    >
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
        />
      </svg>
      Tutorial Mode
    </button>
  );
}
