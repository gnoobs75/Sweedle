/**
 * Animation Studio - Main animation panel component.
 * Allows users to select, customize, and apply animations to rigged models.
 */

import { useEffect, useCallback } from 'react';
import { useAnimationStore } from '../../stores/animationStore';
import { useRiggingStore } from '../../stores/riggingStore';
import { useViewerStore } from '../../stores/viewerStore';
import {
  getAnimationPresets,
  createAnimation,
  getAssetAnimations,
  deleteAnimation,
} from '../../services/api/animation';
import { PresetSelector } from './PresetSelector';
import { AnimationTimeline } from './AnimationTimeline';
import { ParameterSliders } from './ParameterSliders';
import { AnimationList } from './AnimationList';
import { Spinner } from '../ui/Spinner';

export function AnimationStudio() {
  const { currentAssetId } = useViewerStore();
  const { skeletonData } = useRiggingStore();
  const {
    presets,
    setPresets,
    clips,
    setClips,
    selectedPresetId,
    selectPreset,
    parameters,
    setParameters,
    isLoading,
    setIsLoading,
    isApplying,
    setIsApplying,
    error,
    setError,
    clearError,
    addClip,
    removeClip,
  } = useAnimationStore();

  // Load presets when skeleton data is available
  useEffect(() => {
    if (skeletonData?.characterType) {
      loadPresets(skeletonData.characterType);
    }
  }, [skeletonData?.characterType]);

  // Load existing animations for asset
  useEffect(() => {
    if (currentAssetId) {
      loadAssetAnimations(currentAssetId);
    }
  }, [currentAssetId]);

  async function loadPresets(characterType: string) {
    setIsLoading(true);
    setError(null);
    try {
      const fetchedPresets = await getAnimationPresets(characterType);
      setPresets(fetchedPresets);
    } catch (err) {
      setError('Failed to load animation presets');
      console.error('Failed to load presets:', err);
    } finally {
      setIsLoading(false);
    }
  }

  async function loadAssetAnimations(assetId: string) {
    try {
      const fetchedClips = await getAssetAnimations(assetId);
      setClips(fetchedClips);
    } catch {
      // No animations yet - that's fine
    }
  }

  async function handleApplyAnimation() {
    if (!selectedPresetId || !currentAssetId) return;

    setIsApplying(true);
    clearError();
    try {
      const clip = await createAnimation({
        assetId: currentAssetId,
        presetId: selectedPresetId,
        parameters,
      });
      addClip(clip);
      selectPreset(null); // Clear selection after applying
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(`Failed to apply animation: ${message}`);
      console.error('Failed to apply animation:', err);
    } finally {
      setIsApplying(false);
    }
  }

  const handleDeleteAnimation = useCallback(async (clipId: string) => {
    clearError();
    try {
      await deleteAnimation(clipId);
      removeClip(clipId);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      setError(`Failed to delete animation: ${message}`);
      console.error('Failed to delete animation:', err);
    }
  }, [removeClip, setError, clearError]);

  // Not rigged yet
  if (!skeletonData) {
    return (
      <div className="flex flex-col items-center justify-center p-8 text-center">
        <div className="text-4xl mb-4">🦴</div>
        <h3 className="text-lg font-medium text-white mb-2">
          Rigging Required
        </h3>
        <p className="text-gray-400 text-sm max-w-xs">
          Your model needs to be rigged with a skeleton before you can add
          animations. Complete the rigging step first.
        </p>
      </div>
    );
  }

  // Loading presets
  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Spinner size="lg" variant="primary" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-gray-700">
        <h3 className="text-lg font-medium text-white">Animation Studio</h3>
        <p className="text-sm text-gray-400 mt-1">
          Add animations to your {skeletonData.characterType} model.
        </p>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {/* Preset Selection */}
        <div>
          <h4 className="text-sm font-medium text-gray-300 mb-3">
            Choose Animation
          </h4>
          <PresetSelector
            presets={presets}
            selectedId={selectedPresetId}
            onSelect={selectPreset}
          />
        </div>

        {/* Parameter Adjustments */}
        {selectedPresetId && (
          <div className="p-4 bg-gray-800/50 rounded-lg border border-gray-700">
            <h4 className="text-sm font-medium text-gray-300 mb-4">
              Adjust Parameters
            </h4>
            <ParameterSliders
              parameters={parameters}
              onChange={setParameters}
              disabled={isApplying}
            />
            <button
              onClick={handleApplyAnimation}
              disabled={isApplying}
              className="mt-4 w-full py-2.5 bg-indigo-600 hover:bg-indigo-500
                         text-white font-medium rounded-lg transition-colors
                         disabled:opacity-50 disabled:cursor-not-allowed
                         flex items-center justify-center gap-2"
            >
              {isApplying ? (
                <>
                  <Spinner size="sm" variant="white" />
                  Applying...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  Apply Animation
                </>
              )}
            </button>
          </div>
        )}

        {/* Applied Animations */}
        {clips.length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-gray-300 mb-3">
              Applied Animations ({clips.length})
            </h4>
            <AnimationList clips={clips} onDelete={handleDeleteAnimation} />
          </div>
        )}
      </div>

      {/* Timeline Controls */}
      <AnimationTimeline />

      {/* Error Display */}
      {error && (
        <div className="p-3 bg-red-900/20 border-t border-red-700/30 text-red-400 text-sm flex items-center justify-between">
          <span className="flex items-center gap-2">
            <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {error}
          </span>
          <button
            onClick={clearError}
            className="p-1 hover:bg-red-800/30 rounded transition-colors"
            aria-label="Dismiss error"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}
    </div>
  );
}
