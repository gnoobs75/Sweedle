/**
 * RiggingStage - Stage 3: Landmark-based skeleton rigging
 *
 * Users position 8 key landmark points and the system generates
 * the full skeleton with all bones between them.
 */

import { useEffect, useCallback } from 'react';
import { useWorkflowStore } from '../../../stores/workflowStore';
import { useRiggingStore } from '../../../stores/riggingStore';
import { LandmarkEditor } from '../../rigging/LandmarkEditor';

export function RiggingStage() {
  const { stages, setStageStatus } = useWorkflowStore();
  const {
    skeletonData,
    detectedType,
    showSkeleton,
    isLandmarkMode,
    enterLandmarkMode,
    exitLandmarkMode,
  } = useRiggingStore();

  const status = stages.rigging.status;
  const isCompleted = status === 'completed' || status === 'approved';
  const isSkipped = status === 'skipped';
  const isPending = status === 'pending';

  // Auto-enter landmark mode when stage becomes active
  useEffect(() => {
    if (isPending && !isLandmarkMode) {
      enterLandmarkMode();
    }
  }, [isPending, isLandmarkMode, enterLandmarkMode]);

  // Handle landmark complete - mark stage as completed
  const handleLandmarkComplete = useCallback(() => {
    exitLandmarkMode();
    setStageStatus('rigging', 'completed');
  }, [exitLandmarkMode, setStageStatus]);

  // Handle landmark cancel - skip rigging stage
  const handleLandmarkCancel = useCallback(() => {
    exitLandmarkMode();
    // If no skeleton generated yet, skip the stage
    if (!skeletonData) {
      setStageStatus('rigging', 'skipped');
    }
  }, [exitLandmarkMode, skeletonData, setStageStatus]);

  // Re-enter landmark mode to adjust skeleton
  const handleAdjustSkeleton = useCallback(() => {
    enterLandmarkMode();
  }, [enterLandmarkMode]);

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-medium text-white">Skeleton Rigging</h3>

      {/* Show LandmarkEditor when in landmark mode (default for pending) */}
      {isLandmarkMode && (
        <LandmarkEditor onComplete={handleLandmarkComplete} onCancel={handleLandmarkCancel} />
      )}

      {/* Completed view - show skeleton info and option to adjust */}
      {isCompleted && !isLandmarkMode && (
        <div className="space-y-4">
          <div className="p-4 bg-green-900/20 border border-green-700/30 rounded-lg">
            <div className="flex items-center gap-2 text-green-400">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <span className="font-medium">Skeleton Generated</span>
            </div>
          </div>

          {/* Skeleton info */}
          {skeletonData && (
            <div className="p-3 bg-gray-800/50 rounded-lg">
              <h4 className="text-sm font-medium text-gray-300 mb-2">Skeleton Info</h4>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <span className="text-gray-500">Type</span>
                  <p className="text-white capitalize">{detectedType || skeletonData.characterType || 'Unknown'}</p>
                </div>
                <div>
                  <span className="text-gray-500">Bones</span>
                  <p className="text-white">{skeletonData.boneCount || skeletonData.bones?.length || 0}</p>
                </div>
              </div>
            </div>
          )}

          {/* Adjust button */}
          <button
            onClick={handleAdjustSkeleton}
            className="w-full py-2.5 bg-purple-700 hover:bg-purple-600 text-white
                       font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            Adjust Landmarks
          </button>

          <p className="text-sm text-gray-400">
            {showSkeleton
              ? 'Skeleton is visible in the viewer. Press S to toggle.'
              : 'Press S to show the skeleton overlay in the viewer.'}
          </p>

          <div className="p-3 bg-gray-800/30 rounded text-sm text-gray-400">
            <strong className="text-gray-300">Next:</strong> Click "Approve & Continue" to proceed to animation.
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

      {/* Pending but not in landmark mode yet - show brief loading */}
      {isPending && !isLandmarkMode && (
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500"></div>
          <span className="ml-3 text-gray-400">Loading landmarks...</span>
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
            You can skip to export without rigging.
          </p>
        </div>
      )}
    </div>
  );
}
