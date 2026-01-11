/**
 * RiggingStage - Stage 3: Auto-rigging and review
 */

import { useWorkflowStore } from '../../../stores/workflowStore';
import { useRiggingStore } from '../../../stores/riggingStore';

export function RiggingStage() {
  const { stages, isProcessing, progress, progressMessage } = useWorkflowStore();
  const { skeletonData, detectedType, showSkeleton } = useRiggingStore();

  const status = stages.rigging.status;
  const isCompleted = status === 'completed' || status === 'approved';
  const isSkipped = status === 'skipped';

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-medium text-white">Auto-Rigging</h3>

      {isProcessing && (
        <div className="space-y-3">
          <p className="text-sm text-gray-400">
            {progressMessage || 'Analyzing mesh and creating skeleton...'}
          </p>
          <div className="space-y-1">
            <div className="flex justify-between text-xs text-gray-500">
              <span>Progress</span>
              <span>{Math.round(progress * 100)}%</span>
            </div>
            <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-indigo-500 transition-all duration-300"
                style={{ width: `${progress * 100}%` }}
              />
            </div>
          </div>
          {detectedType && (
            <p className="text-xs text-indigo-400">
              Detected: {detectedType} skeleton
            </p>
          )}
        </div>
      )}

      {isCompleted && (
        <div className="space-y-4">
          <div className="p-4 bg-green-900/20 border border-green-700/30 rounded-lg">
            <div className="flex items-center gap-2 text-green-400">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <span className="font-medium">Rigging Complete</span>
            </div>
          </div>

          {/* Skeleton info */}
          {skeletonData && (
            <div className="p-3 bg-gray-800/50 rounded-lg">
              <h4 className="text-sm font-medium text-gray-300 mb-2">Skeleton Info</h4>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <span className="text-gray-500">Type</span>
                  <p className="text-white capitalize">{detectedType || 'Unknown'}</p>
                </div>
                <div>
                  <span className="text-gray-500">Bones</span>
                  <p className="text-white">{skeletonData.boneCount || 0}</p>
                </div>
              </div>
            </div>
          )}

          <p className="text-sm text-gray-400">
            {showSkeleton
              ? 'Skeleton is visible in the viewer. Press S to toggle.'
              : 'Press S to show the skeleton overlay in the viewer.'}
          </p>

          <div className="p-3 bg-gray-800/30 rounded text-sm text-gray-400">
            <strong className="text-gray-300">Next:</strong> Click "Approve & Continue" to proceed to export.
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
            Rigging was skipped. The mesh will be exported without a skeleton.
          </p>
        </div>
      )}

      {!isProcessing && !isCompleted && !isSkipped && status === 'pending' && (
        <div className="space-y-3">
          <p className="text-sm text-gray-400">
            Ready to auto-rig your model. The system will:
          </p>
          <ul className="text-sm text-gray-500 list-disc list-inside space-y-1">
            <li>Detect character type (humanoid or quadruped)</li>
            <li>Create an appropriate skeleton (45-65 bones)</li>
            <li>Apply automatic weight painting</li>
          </ul>
          <div className="p-3 bg-green-900/20 border border-green-700/30 rounded text-sm text-green-300">
            <strong>Godot-Ready:</strong> Your mesh is already optimized for game engines via the quality preset.
          </div>
          <div className="p-3 bg-indigo-900/20 border border-indigo-700/30 rounded text-sm text-indigo-300">
            <strong>Tip:</strong> Rigging works best on character models with clear limbs and a T-pose or A-pose.
          </div>
        </div>
      )}

      {status === 'failed' && (
        <div className="p-4 bg-red-900/20 border border-red-700/30 rounded-lg">
          <div className="flex items-center gap-2 text-red-400">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
            <span className="font-medium">Rigging Failed</span>
          </div>
          <p className="mt-2 text-sm text-red-300/80">
            {stages.rigging.error || 'An error occurred during rigging.'}
          </p>
          <p className="mt-2 text-xs text-gray-500">
            The model may not be suitable for auto-rigging. You can skip to export.
          </p>
        </div>
      )}
    </div>
  );
}
