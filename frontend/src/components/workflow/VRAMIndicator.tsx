/**
 * VRAMIndicator - Shows current pipeline status and VRAM usage
 *
 * Updated for lazy loading mode - shows which model is currently loaded
 * and the current pipeline stage.
 */

import { useWorkflowStore } from '../../stores/workflowStore';

export function VRAMIndicator() {
  const { pipelineStatus } = useWorkflowStore();
  const {
    shapeLoaded,
    textureLoaded,
    vramAllocatedGb,
    vramFreeGb,
    currentStage,
    shapeState,
    textureState,
    statusMessage,
  } = pipelineStatus;

  const totalVram = vramAllocatedGb + vramFreeGb || 24;
  const usagePercent = totalVram > 0 ? (vramAllocatedGb / totalVram) * 100 : 0;

  // Determine warning level
  const isWarning = usagePercent > 80;
  const isCritical = usagePercent > 95;

  // Check if any model is loading
  const isLoading = shapeState === 'loading' || textureState === 'loading';

  // Get current pipeline state display
  let pipelineDisplay = 'Idle (Lazy Loading)';
  let stateColor = 'bg-gray-500';

  if (isLoading) {
    pipelineDisplay = shapeState === 'loading' ? 'Loading Shape (~21GB)...' : 'Loading Texture (~18GB)...';
    stateColor = 'bg-yellow-500 animate-pulse';
  } else if (shapeState === 'ready') {
    pipelineDisplay = 'Shape Ready';
    stateColor = 'bg-green-500';
  } else if (textureState === 'ready') {
    pipelineDisplay = 'Texture Ready';
    stateColor = 'bg-green-500';
  }

  // Current stage icons
  const stageIcons: Record<string, string> = {
    idle: '\u23F8',
    mesh: '\u25B2',
    texture: '\u2B50',
    rigging: '\u2699',
    animation: '\u25B6',
    export: '\u2B07',
  };

  return (
    <div className="px-4 py-2 bg-gray-800/30 border-b border-gray-700/50">
      <div className="flex items-center justify-between text-xs">
        <div className="flex items-center gap-3">
          {/* Stage indicator */}
          {currentStage && currentStage !== 'idle' && (
            <div className="flex items-center gap-1.5">
              <span className="text-base">{stageIcons[currentStage] || '\u2699'}</span>
              <span className="text-gray-400 capitalize">{currentStage}</span>
            </div>
          )}

          {/* Pipeline state indicator */}
          <div className="flex items-center gap-1.5">
            <div className={`w-2 h-2 rounded-full ${stateColor}`} />
            <span className="text-gray-400">
              <span className="text-gray-300">{pipelineDisplay}</span>
            </span>
          </div>
        </div>

        {/* VRAM usage */}
        <div className="flex items-center gap-2">
          <span className="text-gray-400">VRAM:</span>
          <div className="flex items-center gap-1.5">
            <div className="w-24 h-1.5 bg-gray-700 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all duration-300 ${
                  isCritical
                    ? 'bg-red-500'
                    : isWarning
                    ? 'bg-yellow-500'
                    : 'bg-indigo-500'
                }`}
                style={{ width: `${Math.min(usagePercent, 100)}%` }}
              />
            </div>
            <span
              className={`tabular-nums ${
                isCritical
                  ? 'text-red-400'
                  : isWarning
                  ? 'text-yellow-400'
                  : 'text-gray-300'
              }`}
            >
              {vramAllocatedGb.toFixed(1)}GB / {totalVram.toFixed(0)}GB
            </span>
          </div>
        </div>
      </div>

      {/* Status message during loading */}
      {isLoading && statusMessage && (
        <div className="mt-1 text-xs text-gray-500 truncate">
          {statusMessage}
        </div>
      )}
    </div>
  );
}
