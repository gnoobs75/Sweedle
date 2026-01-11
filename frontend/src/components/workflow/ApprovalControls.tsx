/**
 * ApprovalControls - Bottom action bar for workflow stage approval
 *
 * Handles:
 * - Stage action buttons (start generation, texturing, rigging)
 * - Progress display during processing
 * - Approval/Redo/Skip buttons after completion
 */

import { useState, useCallback } from 'react';
import { useWorkflowStore } from '../../stores/workflowStore';
import { useGenerationStore } from '../../stores/generationStore';
import { generateFromImage, addTextureToAsset } from '../../services/api/generation';
import { autoRigAsset } from '../../services/api/rigging';

export function ApprovalControls() {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const {
    currentStage,
    stages,
    isProcessing,
    progress,
    progressMessage,
    approveStage,
    skipToExport,
    redoStage,
    cancelWorkflow,
    sourceImage,
    assetName,
    activeAssetId,
    setActiveAssetId,
    setProcessing,
    setStageStatus,
    setCurrentStage,
  } = useWorkflowStore();

  const { parameters } = useGenerationStore();

  const currentStatus = stages[currentStage].status;
  const isCompleted = currentStatus === 'completed';
  const isFailed = currentStatus === 'failed';
  const isPending = currentStatus === 'pending';
  const isExportStage = currentStage === 'export';

  // Start mesh generation
  const handleStartMesh = useCallback(async () => {
    if (!sourceImage) {
      setError('No source image available');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const response = await generateFromImage({
        file: sourceImage,
        name: assetName || sourceImage.name.replace(/\.[^/.]+$/, ''),
        parameters: {
          ...parameters,
          generateTexture: false, // Mesh stage only
        },
        priority: 'normal',
      });

      setActiveAssetId(response.assetId);
      setProcessing(true, response.jobId);
      setStageStatus('mesh', 'processing');
    } catch (err) {
      console.error('Failed to start mesh generation:', err);
      setError(err instanceof Error ? err.message : 'Failed to start generation');
      setStageStatus('mesh', 'failed', 'Failed to submit generation job');
    } finally {
      setIsSubmitting(false);
    }
  }, [sourceImage, assetName, parameters, setActiveAssetId, setProcessing, setStageStatus]);

  // Start texture generation
  const handleStartTexture = useCallback(async () => {
    if (!activeAssetId) {
      setError('No asset available for texturing');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const response = await addTextureToAsset(activeAssetId, 'normal');

      setProcessing(true, response.jobId);
      setStageStatus('texture', 'processing');
    } catch (err) {
      console.error('Failed to start texture generation:', err);
      setError(err instanceof Error ? err.message : 'Failed to start texturing');
      setStageStatus('texture', 'failed', 'Failed to submit texture job');
    } finally {
      setIsSubmitting(false);
    }
  }, [activeAssetId, setProcessing, setStageStatus]);

  // Start rigging
  const handleStartRigging = useCallback(async () => {
    if (!activeAssetId) {
      setError('No asset available for rigging');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const response = await autoRigAsset({
        assetId: activeAssetId,
        characterType: 'auto',
      });

      setProcessing(true, response.jobId);
      setStageStatus('rigging', 'processing');
    } catch (err) {
      console.error('Failed to start rigging:', err);
      setError(err instanceof Error ? err.message : 'Failed to start rigging');
      setStageStatus('rigging', 'failed', 'Failed to submit rigging job');
    } finally {
      setIsSubmitting(false);
    }
  }, [activeAssetId, setProcessing, setStageStatus]);

  // Handle redo with proper re-trigger capability
  const handleRedo = useCallback(() => {
    setError(null);
    redoStage();
  }, [redoStage]);

  // Get the action button for current stage
  const getStageAction = () => {
    if (currentStage === 'upload') {
      return null; // Upload has its own UI in UploadStage
    }
    if (currentStage === 'mesh') {
      return {
        label: 'Generate Mesh',
        onClick: handleStartMesh,
        disabled: !sourceImage,
      };
    }
    if (currentStage === 'texture') {
      return {
        label: 'Generate Texture',
        onClick: handleStartTexture,
        disabled: !activeAssetId,
      };
    }
    if (currentStage === 'rigging') {
      return {
        label: 'Start Rigging',
        onClick: handleStartRigging,
        disabled: !activeAssetId,
      };
    }
    return null;
  };

  // During processing, show progress bar
  if (isProcessing) {
    return (
      <div className="px-4 py-3 bg-gray-800/50 border-t border-gray-700">
        <div className="flex items-center gap-3">
          <div className="flex-1">
            <div className="flex items-center justify-between text-sm mb-1">
              <span className="text-gray-300">{progressMessage || 'Processing...'}</span>
              <span className="text-gray-400">{Math.round(progress * 100)}%</span>
            </div>
            <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-indigo-500 transition-all duration-300"
                style={{ width: `${progress * 100}%` }}
              />
            </div>
          </div>
          <button
            onClick={cancelWorkflow}
            className="px-3 py-1.5 text-sm text-gray-300 hover:text-white bg-gray-700 hover:bg-gray-600 rounded transition-colors"
          >
            Cancel
          </button>
        </div>
      </div>
    );
  }

  // After completion or failure, show approval buttons
  if (isCompleted || isFailed) {
    return (
      <div className="px-4 py-3 bg-gray-800/50 border-t border-gray-700">
        {error && (
          <div className="mb-2 p-2 bg-red-900/20 border border-red-700/30 rounded text-sm text-red-400">
            {error}
          </div>
        )}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {/* Status indicator */}
            <div
              className={`px-2 py-1 text-xs rounded ${
                isCompleted
                  ? 'bg-green-900/50 text-green-400'
                  : 'bg-red-900/50 text-red-400'
              }`}
            >
              {isCompleted ? 'Ready for Review' : 'Stage Failed'}
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Redo button (for failures or re-attempting) */}
            <button
              onClick={handleRedo}
              className="px-3 py-1.5 text-sm text-gray-300 hover:text-white bg-gray-700 hover:bg-gray-600 rounded transition-colors"
            >
              {isFailed ? 'Retry' : 'Redo'}
            </button>

            {/* Skip to export button (only if not already at export) */}
            {!isExportStage && isCompleted && (
              <button
                onClick={skipToExport}
                className="px-3 py-1.5 text-sm text-gray-300 hover:text-white bg-gray-700 hover:bg-gray-600 rounded transition-colors"
              >
                Skip to Export
              </button>
            )}

            {/* Approve / Continue button */}
            {isCompleted && (
              <button
                onClick={approveStage}
                className="px-4 py-1.5 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-500 rounded transition-colors"
              >
                {isExportStage ? 'Complete' : 'Approve & Continue'}
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Pending state - show action button to start the stage
  if (isPending && currentStage !== 'upload') {
    const action = getStageAction();

    return (
      <div className="px-4 py-3 bg-gray-800/50 border-t border-gray-700">
        {error && (
          <div className="mb-2 p-2 bg-red-900/20 border border-red-700/30 rounded text-sm text-red-400">
            {error}
          </div>
        )}
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-400">
            Ready to {currentStage === 'mesh' ? 'generate mesh' :
                      currentStage === 'texture' ? 'generate texture' :
                      currentStage === 'rigging' ? 'start rigging' :
                      'proceed'}
          </span>

          <div className="flex items-center gap-2">
            {/* Skip button for optional stages */}
            {(currentStage === 'texture' || currentStage === 'rigging') && (
              <button
                onClick={skipToExport}
                className="px-3 py-1.5 text-sm text-gray-400 hover:text-gray-300 transition-colors"
              >
                Skip to Export
              </button>
            )}

            {/* Action button */}
            {action && (
              <button
                onClick={action.onClick}
                disabled={action.disabled || isSubmitting}
                className="px-4 py-1.5 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-600 disabled:cursor-not-allowed rounded transition-colors"
              >
                {isSubmitting ? 'Starting...' : action.label}
              </button>
            )}

            {/* Cancel */}
            <button
              onClick={cancelWorkflow}
              className="px-3 py-1.5 text-sm text-gray-400 hover:text-gray-300 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Default state - upload stage (has its own Generate button in UploadStage)
  return (
    <div className="px-4 py-3 bg-gray-800/50 border-t border-gray-700">
      <div className="flex items-center justify-between">
        <span className="text-sm text-gray-400">
          Upload an image to begin
        </span>
        <button
          onClick={cancelWorkflow}
          className="px-3 py-1.5 text-sm text-gray-400 hover:text-gray-300 transition-colors"
        >
          Cancel Workflow
        </button>
      </div>
    </div>
  );
}
