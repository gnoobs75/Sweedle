/**
 * VRAMIndicator - Shows current pipeline status and VRAM usage
 */

import { useWorkflowStore } from '../../stores/workflowStore';

export function VRAMIndicator() {
  const { pipelineStatus } = useWorkflowStore();
  const { shapeLoaded, textureLoaded, vramAllocatedGb, vramFreeGb } = pipelineStatus;

  const totalVram = vramAllocatedGb + vramFreeGb;
  const usagePercent = totalVram > 0 ? (vramAllocatedGb / totalVram) * 100 : 0;

  // Determine warning level
  const isWarning = usagePercent > 80;
  const isCritical = usagePercent > 95;

  // Get current pipeline name
  let pipelineName = 'None';
  if (shapeLoaded && textureLoaded) {
    pipelineName = 'Shape + Texture';
  } else if (shapeLoaded) {
    pipelineName = 'Shape';
  } else if (textureLoaded) {
    pipelineName = 'Texture';
  }

  return (
    <div className="px-4 py-2 bg-gray-800/30 border-b border-gray-700/50">
      <div className="flex items-center justify-between text-xs">
        <div className="flex items-center gap-3">
          {/* Pipeline indicator */}
          <div className="flex items-center gap-1.5">
            <div
              className={`w-2 h-2 rounded-full ${
                shapeLoaded || textureLoaded
                  ? 'bg-green-500'
                  : 'bg-gray-500'
              }`}
            />
            <span className="text-gray-400">
              Pipeline: <span className="text-gray-300">{pipelineName}</span>
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
    </div>
  );
}
