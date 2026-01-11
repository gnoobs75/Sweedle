/**
 * MeshStage - Stage 1b: Mesh generation and review
 */

import { useWorkflowStore } from '../../../stores/workflowStore';
import { useViewerStore } from '../../../stores/viewerStore';

export function MeshStage() {
  const {
    stages,
    isProcessing,
    progress,
    progressMessage,
    sourceImagePreview,
    assetName,
  } = useWorkflowStore();
  const { modelInfo } = useViewerStore();

  const status = stages.mesh.status;
  const isCompleted = status === 'completed' || status === 'approved';

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-medium text-white">Mesh Generation</h3>

      {/* Reference image - always visible during mesh stage */}
      {sourceImagePreview && (
        <div className="p-3 bg-gray-800/50 rounded-lg">
          <div className="flex items-center gap-2 mb-2">
            <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            <span className="text-sm text-gray-400">Reference Image</span>
          </div>
          <img
            src={sourceImagePreview}
            alt={assetName || 'Source'}
            className="w-full max-h-32 object-contain rounded"
          />
          {assetName && (
            <p className="mt-1 text-xs text-gray-500 truncate">{assetName}</p>
          )}
        </div>
      )}

      {isProcessing && (
        <div className="space-y-3">
          <p className="text-sm text-gray-400">
            {progressMessage || 'Generating 3D mesh from your image...'}
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
          <p className="text-xs text-gray-500">
            This typically takes 30-90 seconds depending on settings.
          </p>
        </div>
      )}

      {isCompleted && (
        <div className="space-y-4">
          <div className="p-4 bg-green-900/20 border border-green-700/30 rounded-lg">
            <div className="flex items-center gap-2 text-green-400">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <span className="font-medium">Mesh Generated Successfully</span>
            </div>
          </div>

          <p className="text-sm text-gray-400">
            Review the generated mesh in the viewer. Rotate and zoom to inspect from all angles.
          </p>

          {/* Mesh stats */}
          {modelInfo && (modelInfo.vertexCount || modelInfo.faceCount) && (
            <div className="p-3 bg-gray-800/50 rounded-lg">
              <h4 className="text-sm font-medium text-gray-300 mb-2">Mesh Statistics</h4>
              <div className="grid grid-cols-2 gap-3 text-sm">
                {modelInfo.vertexCount && (
                  <div>
                    <span className="text-gray-500">Vertices</span>
                    <p className="text-white">{modelInfo.vertexCount.toLocaleString()}</p>
                  </div>
                )}
                {modelInfo.faceCount && (
                  <div>
                    <span className="text-gray-500">Faces</span>
                    <p className="text-white">{modelInfo.faceCount.toLocaleString()}</p>
                  </div>
                )}
              </div>
            </div>
          )}

          <div className="p-3 bg-gray-800/30 rounded text-sm text-gray-400">
            <strong className="text-gray-300">Next:</strong> Click "Approve & Continue" to add texture,
            or "Skip to Export" to download the untextured mesh.
          </div>
        </div>
      )}

      {!isProcessing && !isCompleted && status === 'pending' && (
        <p className="text-sm text-gray-400">
          Waiting to start mesh generation...
        </p>
      )}

      {status === 'failed' && (
        <div className="p-4 bg-red-900/20 border border-red-700/30 rounded-lg">
          <div className="flex items-center gap-2 text-red-400">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
            <span className="font-medium">Mesh Generation Failed</span>
          </div>
          <p className="mt-2 text-sm text-red-300/80">
            {stages.mesh.error || 'An error occurred during mesh generation.'}
          </p>
          <p className="mt-2 text-xs text-gray-500">
            Try with a different image or check the backend logs.
          </p>
        </div>
      )}
    </div>
  );
}
