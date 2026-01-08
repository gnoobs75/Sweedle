/**
 * ViewerPanel Component - Complete 3D viewer with toolbar and info
 */

import { useCallback, useEffect } from 'react';
import { useViewerStore } from '../../stores/viewerStore';
import { GLBViewer } from './GLBViewer';
import { ViewerToolbar } from './ViewerToolbar';
import { ModelInfo } from './ModelInfo';
import { EmptyState, LoadingState, ErrorState, ControlsHint } from './ViewerStates';

export function ViewerPanel() {
  const {
    currentModelUrl,
    currentAssetId,
    isLoading,
    loadError,
    settings,
    setSetting,
    setLoading,
    setLoadError,
    clearModel,
    resetCamera,
  } = useViewerStore();

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if typing in an input
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement
      ) {
        return;
      }

      switch (e.key.toLowerCase()) {
        case 'w':
          setSetting('showWireframe', !settings.showWireframe);
          break;
        case 'g':
          setSetting('showGrid', !settings.showGrid);
          break;
        case 'a':
          setSetting('showAxes', !settings.showAxes);
          break;
        case 'r':
          setSetting('autoRotate', !settings.autoRotate);
          break;
        case 'home':
          resetCamera();
          break;
        case 'escape':
          clearModel();
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [settings, setSetting, resetCamera, clearModel]);

  const handleRetry = useCallback(() => {
    if (currentModelUrl) {
      setLoadError(null);
      setLoading(true);
      // Force re-render by clearing and reloading
      const url = currentModelUrl;
      clearModel();
      setTimeout(() => {
        useViewerStore.getState().loadModel(url, currentAssetId || undefined);
      }, 100);
    }
  }, [currentModelUrl, currentAssetId, setLoadError, setLoading, clearModel]);

  return (
    <div className="h-full flex flex-col bg-background relative">
      {/* Toolbar */}
      <div className="border-b border-border bg-surface relative z-10">
        <ViewerToolbar />
      </div>

      {/* Viewer Canvas */}
      <div className="flex-1 relative overflow-hidden">
        {/* Loading State */}
        {isLoading && <LoadingState />}

        {/* Error State */}
        {loadError && !isLoading && (
          <ErrorState error={loadError} onRetry={handleRetry} />
        )}

        {/* Empty State */}
        {!currentModelUrl && !isLoading && !loadError && <EmptyState />}

        {/* 3D Viewer */}
        {currentModelUrl && !loadError && (
          <>
            <GLBViewer
              url={currentModelUrl}
              onError={(error) => setLoadError(error.message)}
            />
            {/* Controls hint - only show when model is loaded */}
            {!isLoading && <ControlsHint />}
          </>
        )}
      </div>

      {/* Model Info Bar */}
      <ModelInfo variant="bar" />
    </div>
  );
}
