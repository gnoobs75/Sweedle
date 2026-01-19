/**
 * ExportStage - Final stage: Export, download, and preview
 */

import { useState, useCallback, useEffect } from 'react';
import { useWorkflowStore } from '../../../stores/workflowStore';
import { useAnimationStore } from '../../../stores/animationStore';
import { useViewerStore } from '../../../stores/viewerStore';
import { exportWithAnimations } from '../../../services/api/animation';
import { exportSkinnedGLB } from '../../../services/api/export';

const API_BASE = 'http://localhost:8001';

export function ExportStage() {
  const { stages, activeAssetId } = useWorkflowStore();
  const { clips, isPlaying, setIsPlaying } = useAnimationStore();
  const {
    setSkinnedPreviewUrl,
    setIsSkinnedPreview,
    isSkinnedPreview,
    clearSkinnedPreview,
  } = useViewerStore();

  const [isDownloading, setIsDownloading] = useState(false);
  const [isExportingWithAnimations, setIsExportingWithAnimations] = useState(false);
  const [isExportingSkinned, setIsExportingSkinned] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [fileExists, setFileExists] = useState<boolean | null>(null);
  const [exportSuccess, setExportSuccess] = useState<string | null>(null);
  const [exportedFilePath, setExportedFilePath] = useState<string | null>(null);
  const [exportedAnimCount, setExportedAnimCount] = useState(0);

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

  // Clean up preview when leaving stage
  useEffect(() => {
    return () => {
      if (isSkinnedPreview) {
        clearSkinnedPreview();
        setIsPlaying(false);
      }
    };
  }, []);

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

      if (result.success && result.outputPath) {
        // Construct download URL
        const cleanPath = result.outputPath.replace(/\\/g, '/');
        const urlPath = cleanPath.startsWith('/') ? cleanPath : `/${cleanPath}`;
        const downloadUrl = `${API_BASE}${urlPath}`;
        const fileName = result.outputPath.split(/[/\\]/).pop() || 'animated.glb';

        // Fetch file as blob for reliable download
        const response = await fetch(downloadUrl);
        if (!response.ok) {
          throw new Error(`Failed to download file: ${response.statusText}`);
        }
        const blob = await response.blob();

        // Create blob URL and trigger download
        const blobUrl = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = blobUrl;
        link.download = fileName;
        link.style.display = 'none';
        document.body.appendChild(link);
        link.click();

        // Cleanup
        setTimeout(() => {
          document.body.removeChild(link);
          URL.revokeObjectURL(blobUrl);
        }, 100);

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

  const handleExportSkinnedGLB = useCallback(async () => {
    if (!activeAssetId) return;

    setIsExportingSkinned(true);
    setDownloadError(null);
    setExportSuccess(null);
    setExportedFilePath(null);

    try {
      const result = await exportSkinnedGLB({
        assetId: activeAssetId,
        includeAnimations: animationCount > 0,
      });

      if (result.success && result.outputPath) {
        // Construct download URL
        const cleanPath = result.outputPath.replace(/\\/g, '/');
        const urlPath = cleanPath.startsWith('/') ? cleanPath : `/${cleanPath}`;
        const downloadUrl = `${API_BASE}${urlPath}`;
        const fileName = result.outputPath.split(/[/\\]/).pop() || 'skinned.glb';

        // Fetch file as blob for reliable download
        const response = await fetch(downloadUrl);
        if (!response.ok) {
          throw new Error(`Failed to download file: ${response.statusText}`);
        }
        const blob = await response.blob();

        // Create blob URL and trigger download
        const blobUrl = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = blobUrl;
        link.download = fileName;
        link.style.display = 'none';
        document.body.appendChild(link);
        link.click();

        // Cleanup
        setTimeout(() => {
          document.body.removeChild(link);
          URL.revokeObjectURL(blobUrl);
        }, 100);

        // Store the exported file path for preview
        setExportedFilePath(downloadUrl);
        setExportedAnimCount(result.animationCount);

        setExportSuccess(
          `Exported skinned GLB with ${result.boneCount} bones${result.animationCount > 0 ? ` and ${result.animationCount} animation${result.animationCount > 1 ? 's' : ''}` : ''}`
        );
      } else {
        throw new Error(result.error || 'Export failed - no output path');
      }
    } catch (error) {
      console.error('Skinned GLB export failed:', error);
      setDownloadError(error instanceof Error ? error.message : 'Skinned GLB export failed');
    } finally {
      setIsExportingSkinned(false);
    }
  }, [activeAssetId, animationCount]);

  // Preview the exported skinned GLB with animations
  const handlePreviewAnimations = useCallback(() => {
    if (!exportedFilePath) return;

    // Add cache-buster to force useGLTF to reload the model
    const cacheBuster = `?t=${Date.now()}`;
    const previewUrl = exportedFilePath + cacheBuster;
    console.log('Loading skinned preview from:', previewUrl);

    // Load the skinned GLB into the viewer
    setSkinnedPreviewUrl(previewUrl);
    setIsSkinnedPreview(true);
    // Auto-play animations
    setIsPlaying(true);
  }, [exportedFilePath, setSkinnedPreviewUrl, setIsSkinnedPreview, setIsPlaying]);

  // Stop preview and return to normal view
  const handleStopPreview = useCallback(() => {
    clearSkinnedPreview();
    setIsPlaying(false);
  }, [clearSkinnedPreview, setIsPlaying]);

  // Toggle play/pause
  const handleTogglePlay = useCallback(() => {
    setIsPlaying(!isPlaying);
  }, [isPlaying, setIsPlaying]);

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

      {/* Animation Preview Controls - show after export */}
      {exportedFilePath && exportedAnimCount > 0 && (
        <div className="p-4 bg-purple-900/20 border border-purple-700/30 rounded-lg">
          <h4 className="text-sm font-medium text-purple-300 mb-3 flex items-center gap-2">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Animation Preview
          </h4>

          {!isSkinnedPreview ? (
            <button
              onClick={handlePreviewAnimations}
              className="w-full py-2.5 bg-purple-600 hover:bg-purple-500 text-white font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
              Preview in 3D Viewer ({exportedAnimCount} animation{exportedAnimCount > 1 ? 's' : ''})
            </button>
          ) : (
            <div className="space-y-2">
              <div className="flex gap-2">
                <button
                  onClick={handleTogglePlay}
                  className={`flex-1 py-2.5 font-medium rounded-lg transition-colors flex items-center justify-center gap-2 ${
                    isPlaying
                      ? 'bg-yellow-600 hover:bg-yellow-500 text-white'
                      : 'bg-green-600 hover:bg-green-500 text-white'
                  }`}
                >
                  {isPlaying ? (
                    <>
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      Pause
                    </>
                  ) : (
                    <>
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      Play
                    </>
                  )}
                </button>
                <button
                  onClick={handleStopPreview}
                  className="py-2.5 px-4 bg-gray-600 hover:bg-gray-500 text-white font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                  Exit Preview
                </button>
              </div>
              <p className="text-xs text-purple-400 text-center">
                Viewing exported skinned GLB with embedded animations
              </p>
            </div>
          )}
        </div>
      )}

      {/* Download buttons */}
      <div className="space-y-2">
        {/* Primary: Export Skinned GLB for Godot - only show if rigged */}
        {hasRigging && (
          <button
            onClick={handleExportSkinnedGLB}
            disabled={isExportingSkinned || !activeAssetId}
            className="w-full py-3 text-sm font-medium text-white bg-green-600 hover:bg-green-500 disabled:bg-gray-600 disabled:cursor-not-allowed rounded transition-colors flex items-center justify-center gap-2"
          >
            {isExportingSkinned ? (
              <>
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Exporting Skinned GLB...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
                </svg>
                Export Skinned GLB for Godot
                {animationCount > 0 && ` (+ ${animationCount} anim)`}
              </>
            )}
          </button>
        )}

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
              Download GLB {hasRigging ? '(Mesh Only)' : ''}
            </>
          )}
        </button>

        {/* Export with animations button - only show if animations exist and not rigged (legacy option) */}
        {hasAnimations && animationCount > 0 && !hasRigging && (
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
        {hasRigging && (
          <span className="block mt-1 text-green-400">
            <strong>Recommended:</strong> "Export Skinned GLB" creates a self-contained file with embedded skeleton,
            skinning weights, and animations that will deform the mesh in Godot.
          </span>
        )}
        {!hasRigging && hasAnimations && animationCount > 0 && (
          <span className="block mt-1 text-purple-400">
            Tip: Use "Export with Animations" to embed animation clips directly in the GLB file.
          </span>
        )}
      </div>
    </div>
  );
}
