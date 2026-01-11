/**
 * ExportStage - Stage 4: Export and download
 */

import { useState, useCallback } from 'react';
import { useWorkflowStore } from '../../../stores/workflowStore';

const API_BASE = 'http://localhost:8000';

export function ExportStage() {
  const { stages, activeAssetId } = useWorkflowStore();
  const [isDownloading, setIsDownloading] = useState(false);

  const status = stages.export.status;
  const hasTexture = stages.texture.status === 'approved' || stages.texture.status === 'completed';
  const hasRigging = stages.rigging.status === 'approved' || stages.rigging.status === 'completed';

  const handleDownloadGLB = useCallback(async () => {
    if (!activeAssetId) return;

    setIsDownloading(true);
    try {
      // Construct download URL
      const downloadUrl = `${API_BASE}/storage/generated/${activeAssetId}/${activeAssetId}.glb`;

      // Create a temporary link and click it
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = `${activeAssetId}.glb`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (error) {
      console.error('Download failed:', error);
    } finally {
      setIsDownloading(false);
    }
  }, [activeAssetId]);

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-medium text-white">Export</h3>

      <p className="text-sm text-gray-400">
        Your 3D asset is ready for export. Download the GLB file to use in your game engine.
      </p>

      {/* Asset summary */}
      <div className="p-4 bg-gray-800/50 rounded-lg">
        <h4 className="text-sm font-medium text-gray-300 mb-3">Asset Summary</h4>
        <div className="space-y-2 text-sm">
          <div className="flex items-center justify-between">
            <span className="text-gray-500">Mesh</span>
            <span className="text-green-400 flex items-center gap-1">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              Included
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-gray-500">Texture</span>
            {hasTexture ? (
              <span className="text-green-400 flex items-center gap-1">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                Included
              </span>
            ) : (
              <span className="text-gray-500 flex items-center gap-1">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
                </svg>
                Not included
              </span>
            )}
          </div>
          <div className="flex items-center justify-between">
            <span className="text-gray-500">Rigging</span>
            {hasRigging ? (
              <span className="text-green-400 flex items-center gap-1">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                Included
              </span>
            ) : (
              <span className="text-gray-500 flex items-center gap-1">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
                </svg>
                Not included
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Download button */}
      <button
        onClick={handleDownloadGLB}
        disabled={isDownloading || !activeAssetId}
        className="w-full py-3 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-600 disabled:cursor-not-allowed rounded transition-colors flex items-center justify-center gap-2"
      >
        {isDownloading ? (
          <>
            <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            Downloading...
          </>
        ) : (
          <>
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
              />
            </svg>
            Download GLB
          </>
        )}
      </button>

      {/* Format info */}
      <div className="p-3 bg-gray-800/30 rounded text-sm text-gray-400">
        <strong className="text-gray-300">GLB Format:</strong> Binary glTF format compatible with
        Unity, Unreal Engine, Godot, Blender, and other 3D applications.
      </div>

      {/* Future: Animation placeholder */}
      <div className="p-4 bg-indigo-900/10 border border-indigo-700/20 rounded-lg">
        <div className="flex items-center gap-2 text-indigo-400 mb-2">
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <span className="font-medium">Coming Soon: Animations</span>
        </div>
        <p className="text-sm text-gray-500">
          Future updates will include automatic animation generation for rigged models,
          including idle animations and walk cycles.
        </p>
      </div>
    </div>
  );
}
