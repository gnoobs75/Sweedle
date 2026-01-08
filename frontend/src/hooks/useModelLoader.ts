/**
 * useModelLoader Hook - Model loading utilities
 */

import { useCallback } from 'react';
import { useViewerStore } from '../stores/viewerStore';
import { getAssetModelUrl, getAssetThumbnailUrl } from '../services/api/assets';

interface UseModelLoaderOptions {
  autoFit?: boolean;
}

export function useModelLoader(options: UseModelLoaderOptions = {}) {
  const {
    currentModelUrl,
    currentAssetId,
    isLoading,
    loadError,
    modelInfo,
    loadModel,
    clearModel,
    setLoading,
    setLoadError,
  } = useViewerStore();

  /**
   * Load model from asset ID
   */
  const loadFromAsset = useCallback(
    (assetId: string, format: 'glb' | 'obj' | 'fbx' = 'glb') => {
      const url = getAssetModelUrl(assetId, format);
      loadModel(url, assetId);
    },
    [loadModel]
  );

  /**
   * Load model from URL
   */
  const loadFromUrl = useCallback(
    (url: string) => {
      loadModel(url);
    },
    [loadModel]
  );

  /**
   * Load model from file
   */
  const loadFromFile = useCallback(
    (file: File) => {
      const url = URL.createObjectURL(file);
      loadModel(url);

      // Cleanup blob URL when done
      return () => URL.revokeObjectURL(url);
    },
    [loadModel]
  );

  /**
   * Reload current model
   */
  const reload = useCallback(() => {
    if (currentModelUrl) {
      setLoadError(null);
      setLoading(true);
      const url = currentModelUrl;
      const assetId = currentAssetId;
      clearModel();
      setTimeout(() => {
        loadModel(url, assetId || undefined);
      }, 50);
    }
  }, [currentModelUrl, currentAssetId, clearModel, loadModel, setLoading, setLoadError]);

  /**
   * Clear loaded model
   */
  const clear = useCallback(() => {
    clearModel();
  }, [clearModel]);

  /**
   * Get thumbnail URL for asset
   */
  const getThumbnail = useCallback((assetId: string) => {
    return getAssetThumbnailUrl(assetId);
  }, []);

  return {
    // State
    currentUrl: currentModelUrl,
    currentAssetId,
    isLoading,
    error: loadError,
    modelInfo,

    // Actions
    loadFromAsset,
    loadFromUrl,
    loadFromFile,
    reload,
    clear,

    // Utilities
    getThumbnail,

    // Computed
    hasModel: !!currentModelUrl,
    isReady: !!currentModelUrl && !isLoading && !loadError,
  };
}
