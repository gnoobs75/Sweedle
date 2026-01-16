/**
 * ExportStage - Final stage: Export and download
 */

import { useState, useCallback, useEffect } from 'react';
import { useWorkflowStore } from '../../../stores/workflowStore';
import { useAnimationStore } from '../../../stores/animationStore';
import { exportWithAnimations } from '../../../services/api/animation';

const API_BASE = 'http://localhost:8000';

export function ExportStage() {
  const { stages, activeAssetId } = useWorkflowStore();
  const { clips } = useAnimationStore();
  const [isDownloading, setIsDownloading] = useState(false);
  const [isExportingWithAnimations, setIsExportingWithAnimations] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [fileExists, setFileExists] = useState<boolean | null>(null);
  const [exportSuccess, setExportSuccess] = useState<string | null>(null);

  const hasTexture = stages.texture.status === 'approved' || stages.texture.status === 'completed';
  const hasRigging = stages.rigging.status === 'approved' || stages.rigging.status === 'completed';
  const hasAnimations = stages.animation.status === 'approved' || stages.animation.status === 'completed';
  const animationCount = clips.length;

  // Check if file exists when component mounts or assetId changes
  useEffect(() => {
    async function checkFileExists() {
      if (!activeAssetId) {
        setFileExists(false);
        return;
      }

      try {
        const response = await fetch(
          `${API_BASE}/storage/generated/${activeAssetId}/${activeAssetId}.glb`,
          { method: 'HEAD' }
        );
        setFileExists(response.ok);
      } catch {
        setFileExists(false);
      }
    }

    checkFileExists();
  }, [activeAssetId]);

  const handleDownloadGLB = useCallback(async () => {
    if (!activeAssetId) return;

    setIsDownloading(true);
    setDownloadError(null);
    setExportSuccess(null);

    try {
      // Verify file exists first
      const checkResponse = await fetch(
        `${API_BASE}/storage/generated/${activeAssetId}/${activeAssetId}.glb`,
        { method: 'HEAD' }
      );

      if (!checkResponse.ok) {
        throw new Error('File not found. The model may not have been generated successfully.');
      }

      // Construct download URL
      const downloadUrl = `${API_BASE}/storage/generated/${activeAssetId}/${activeAssetId}.glb`;

      // Create a temporary link and click it
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = `${activeAssetId}.glb`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      setExportSuccess('Download started');
    } catch (error) {
      console.error('Download failed:', error);
      setDownloadError(error instanceof Error ? error.message : 'Download failed');
    } finally {
      setIsDownloading(false);
    }
  }, [activeAssetId]);

  const handleExportWithAnimations = useCallback(async () => {
    if (!activeAssetId || animationCount === 0) return;

    setIsExportingWithAnimations(true);
    setDownloadError(null);
    setExportSuccess(null);

    try {
      const result = await exportWithAnimations({ assetId: activeAssetId });

      if (result.success) {
        // Download the animated file
        const link = document.createElement('a');
        link.href = `${API_BASE}${result.outputPath.replace(/\\/g, '/')}`;
        link.download = result.outputPath.split(/[/\\]/).pop() || 'animated.glb';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        setExportSuccess(
          `Exported with ${result.animationsEmbedded} animation${result.animationsEmbedded > 1 ? 's' : ''}`
        );
      } else {
        throw new Error(result.error || 'Export failed');
      }
    } catch (error) {
      console.error('Animation export failed:', error);
      setDownloadError(error instanceof Error ? error.message : 'Export with animations failed');
    } finally {
      setIsExportingWithAnimations(false);
    }
  }, [activeAssetId, animationCount]);

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
          <div className="flex items-center justify-between">
            <span className="text-gray-500">Animations</span>
            {hasAnimations && animationCount > 0 ? (
              <span className="text-green-400 flex items-center gap-1">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                {animationCount} clip{animationCount > 1 ? 's' : ''}
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

      {/* Error display */}
      {downloadError && (
        <div className="p-3 bg-red-900/20 border border-red-700/30 rounded text-sm text-red-400 flex items-center gap-2">
          <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          {downloadError}
        </div>
      )}

      {/* Success display */}
      {exportSuccess && (
        <div className="p-3 bg-green-900/20 border border-green-700/30 rounded text-sm text-green-400 flex items-center gap-2">
          <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          {exportSuccess}
        </div>
      )}

      {/* File status warning */}
      {fileExists === false && (
        <div className="p-3 bg-yellow-900/20 border border-yellow-700/30 rounded text-sm text-yellow-400 flex items-center gap-2">
          <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          Model file not found. Generation may have failed.
        </div>
      )}

      {/* Download buttons */}
      <div className="space-y-2">
        <button
          onClick={handleDownloadGLB}
          disabled={isDownloading || !activeAssetId || fileExists === false}
          className="w-full py-3 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-600 disabled:cursor-not-allowed rounded transition-colors flex items-center justify-center gap-2"
        >
          {isDownloading ? (
            <>
              <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              Downloading...
            </>
          ) : (
            <>
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Download GLB
            </>
          )}
        </button>

        {/* Export with animations button - only show if animations exist */}
        {hasAnimations && animationCount > 0 && (
          <button
            onClick={handleExportWithAnimations}
            disabled={isExportingWithAnimations || !activeAssetId}
            className="w-full py-3 text-sm font-medium text-white bg-purple-600 hover:bg-purple-500 disabled:bg-gray-600 disabled:cursor-not-allowed rounded transition-colors flex items-center justify-center gap-2"
          >
            {isExportingWithAnimations ? (
              <>
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Embedding Animations...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Export with Animations ({animationCount})
              </>
            )}
          </button>
        )}
      </div>

      {/* Format info */}
      <div className="p-3 bg-gray-800/30 rounded text-sm text-gray-400">
        <strong className="text-gray-300">GLB Format:</strong> Binary glTF format compatible with
        Unity, Unreal Engine, Godot, Blender, and other 3D applications.
        {hasAnimations && animationCount > 0 && (
          <span className="block mt-1 text-purple-400">
            Tip: Use "Export with Animations" to embed animation clips directly in the GLB file.
          </span>
        )}
      </div>
    </div>
  );
}
