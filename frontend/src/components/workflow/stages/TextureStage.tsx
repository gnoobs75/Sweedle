/**
 * TextureStage - Stage 2: Texture generation and review
 */

import { useWorkflowStore } from '../../../stores/workflowStore';

export function TextureStage() {
  const { stages, isProcessing, progress, progressMessage } = useWorkflowStore();

  const status = stages.texture.status;
  const isCompleted = status === 'completed' || status === 'approved';
  const isSkipped = status === 'skipped';

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-medium text-white">Texture Generation</h3>

      {isProcessing && (
        <div className="space-y-3">
          {/* Main status message - shows elapsed time from backend */}
          <div className="p-3 bg-indigo-900/20 border border-indigo-700/30 rounded-lg">
            <div className="flex items-center gap-2 text-indigo-400">
              <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              <span className="font-medium">
                {progressMessage || 'Generating textures...'}
              </span>
            </div>
          </div>

          {/* Progress bar */}
          <div className="space-y-1">
            <div className="flex justify-between text-xs text-gray-500">
              <span>Estimated Progress</span>
              <span>{Math.round(progress * 100)}%</span>
            </div>
            <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-indigo-500 transition-all duration-300"
                style={{ width: `${progress * 100}%` }}
              />
            </div>
          </div>

          {/* Info about texture generation */}
          <div className="text-xs text-gray-500 space-y-1">
            <p>Texture generation is computationally intensive and uses ~18GB VRAM.</p>
            <p>Typical time: 60-180 seconds depending on mesh complexity.</p>
          </div>
        </div>
      )}

      {isCompleted && (
        <div className="space-y-4">
          <div className="p-4 bg-green-900/20 border border-green-700/30 rounded-lg">
            <div className="flex items-center gap-2 text-green-400">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <span className="font-medium">Texture Applied Successfully</span>
            </div>
          </div>

          <p className="text-sm text-gray-400">
            Review the textured model in the viewer. Check that colors and details look correct.
          </p>

          <div className="p-3 bg-gray-800/30 rounded text-sm text-gray-400">
            <strong className="text-gray-300">Next:</strong> Click "Approve & Continue" to add rigging,
            or "Skip to Export" to download the textured mesh without rigging.
          </div>
        </div>
      )}

      {isSkipped && (
        <div className="p-4 bg-gray-800/50 border border-gray-700 rounded-lg">
          <div className="flex items-center gap-2 text-gray-400">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7M5 5l7 7-7 7" />
            </svg>
            <span className="font-medium">Stage Skipped</span>
          </div>
          <p className="mt-2 text-sm text-gray-500">
            Texture generation was skipped. The mesh will be exported without textures.
          </p>
        </div>
      )}

      {!isProcessing && !isCompleted && !isSkipped && status === 'pending' && (
        <div className="space-y-3">
          <p className="text-sm text-gray-400">
            Ready to generate textures for your mesh.
          </p>
          <div className="p-3 bg-indigo-900/20 border border-indigo-700/30 rounded text-sm text-indigo-300">
            <strong>Note:</strong> This will unload the shape pipeline and load the texture pipeline (~18GB VRAM).
          </div>
        </div>
      )}

      {status === 'failed' && (
        <div className="p-4 bg-red-900/20 border border-red-700/30 rounded-lg">
          <div className="flex items-center gap-2 text-red-400">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
            <span className="font-medium">Texture Generation Failed</span>
          </div>
          <p className="mt-2 text-sm text-red-300/80">
            {stages.texture.error || 'An error occurred during texture generation.'}
          </p>
          <p className="mt-2 text-xs text-gray-500">
            This may be due to insufficient VRAM. Try closing other applications.
          </p>
        </div>
      )}
    </div>
  );
}
