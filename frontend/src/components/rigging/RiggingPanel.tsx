/**
 * RiggingPanel - Main UI for auto-rigging assets.
 */

import { useState, useCallback, useEffect } from 'react';
import { useRiggingStore } from '../../stores/riggingStore';
import { useLibraryStore } from '../../stores/libraryStore';
import { useViewerStore } from '../../stores/viewerStore';
import { autoRigAsset, getSkeleton, resetRigging } from '../../services/api/rigging';
import { CharacterTypeSelector } from './CharacterTypeSelector';
import { RiggingProgress } from './RiggingProgress';

type Step = 'config' | 'processing' | 'complete' | 'error';

interface RiggingPanelProps {
  assetId?: string;
  onClose?: () => void;
  className?: string;
}

export function RiggingPanel({ assetId, onClose, className = '' }: RiggingPanelProps) {
  const { assets } = useLibraryStore();
  const { currentAssetId } = useViewerStore();

  const {
    isRigging,
    progress,
    stage,
    characterType,
    processor,
    detectedType,
    showSkeleton,
    error,
    setCharacterType,
    setProcessor,
    setIsRigging,
    setCurrentJobId,
    setShowSkeleton,
    setSkeletonData,
    setError,
    reset,
  } = useRiggingStore();

  // Use provided assetId or current viewer asset
  const targetAssetId = assetId || currentAssetId;
  const targetAsset = assets.find((a) => a.id === targetAssetId);

  const [step, setStep] = useState<Step>('config');
  const [isResetting, setIsResetting] = useState(false);

  const handleStartRigging = useCallback(async () => {
    if (!targetAssetId) return;

    setStep('processing');
    setIsRigging(true);
    setError(null);

    try {
      const response = await autoRigAsset({
        assetId: targetAssetId,
        characterType,
        processor,
        priority: 'normal',
        force: targetAsset?.isRigged, // Force re-rigging if already rigged
      });

      setCurrentJobId(response.jobId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start rigging');
      setStep('error');
      setIsRigging(false);
    }
  }, [targetAssetId, targetAsset?.isRigged, characterType, processor, setIsRigging, setCurrentJobId, setError]);

  const handleResetRigging = useCallback(async () => {
    if (!targetAssetId) return;

    setIsResetting(true);
    try {
      await resetRigging(targetAssetId);
      // Clear skeleton data
      setSkeletonData(null);
      setError(null);
      reset();
      setStep('config');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reset rigging');
    } finally {
      setIsResetting(false);
    }
  }, [targetAssetId, setSkeletonData, setError, reset]);

  // Handle completion via WebSocket updates
  useEffect(() => {
    if (!isRigging && progress >= 1.0 && step === 'processing') {
      setStep('complete');

      // Fetch skeleton data
      if (targetAssetId) {
        getSkeleton(targetAssetId).then((skeleton) => {
          if (skeleton) {
            setSkeletonData(skeleton.skeleton);
          }
        });
      }
    }
  }, [isRigging, progress, step, targetAssetId, setSkeletonData]);

  // Handle error state
  useEffect(() => {
    if (error && step === 'processing') {
      setStep('error');
    }
  }, [error, step]);

  // Can rig if we have an asset ID and not currently rigging
  // Asset status check is optional since viewer already loaded the model successfully
  const canRig = targetAssetId && !isRigging;

  return (
    <div className={`flex flex-col h-full bg-surface ${className}`}>
      {/* Header */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-text-primary">Auto-Rig</h2>
            <p className="text-sm text-text-muted">Add skeleton and weights to 3D model</p>
          </div>
          {onClose && (
            <button
              onClick={onClose}
              className="p-2 text-text-muted hover:text-text-primary hover:bg-surface-light rounded"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {step === 'config' && (
          <>
            {/* Asset Preview */}
            {targetAsset ? (
              <div className="p-3 bg-surface-light rounded-lg border border-border">
                <div className="flex items-center gap-3">
                  {targetAsset.thumbnailPath ? (
                    <img
                      src={targetAsset.thumbnailPath}
                      alt={targetAsset.name}
                      className="w-16 h-16 rounded object-cover"
                    />
                  ) : (
                    <div className="w-16 h-16 rounded bg-surface flex items-center justify-center">
                      <svg className="w-8 h-8 text-text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                      </svg>
                    </div>
                  )}
                  <div>
                    <p className="font-medium text-text-primary">{targetAsset.name}</p>
                    <p className="text-sm text-text-muted">
                      {targetAsset.vertexCount?.toLocaleString()} vertices
                    </p>
                    {targetAsset.isRigged && (
                      <span className="inline-block mt-1 px-2 py-0.5 text-xs bg-primary/20 text-primary rounded">
                        Already Rigged
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ) : targetAssetId ? (
              <div className="p-3 bg-surface-light rounded-lg border border-border">
                <div className="flex items-center gap-3">
                  <div className="w-16 h-16 rounded bg-surface flex items-center justify-center">
                    <svg className="w-8 h-8 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                    </svg>
                  </div>
                  <div>
                    <p className="font-medium text-text-primary">Current Model</p>
                    <p className="text-sm text-text-muted">Ready for rigging</p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-6 text-center text-text-muted">
                <svg className="w-12 h-12 mx-auto mb-2 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                </svg>
                <p>Select an asset to rig</p>
              </div>
            )}

            {/* Character Type Selection */}
            <CharacterTypeSelector
              value={characterType}
              onChange={setCharacterType}
              detectedType={detectedType}
            />

            {/* Processor Selection */}
            <div className="p-3 bg-surface-light rounded-lg border border-border">
              <h4 className="text-xs font-semibold text-text-muted uppercase mb-3">Rigging Engine</h4>
              <div className="space-y-2">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="processor"
                    value="auto"
                    checked={processor === 'auto'}
                    onChange={() => setProcessor('auto')}
                    className="text-primary"
                  />
                  <span className="text-sm text-text-primary">Auto (Recommended)</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="processor"
                    value="unirig"
                    checked={processor === 'unirig'}
                    onChange={() => setProcessor('unirig')}
                    className="text-primary"
                  />
                  <span className="text-sm text-text-primary">UniRig (ML-based, faster)</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="processor"
                    value="blender"
                    checked={processor === 'blender'}
                    onChange={() => setProcessor('blender')}
                    className="text-primary"
                  />
                  <span className="text-sm text-text-primary">Blender (More control)</span>
                </label>
              </div>
            </div>
          </>
        )}

        {step === 'processing' && (
          <RiggingProgress progress={progress} stage={stage} detectedType={detectedType} />
        )}

        {step === 'complete' && (
          <div className="text-center py-8">
            <div className="w-16 h-16 mx-auto mb-4 text-success flex items-center justify-center">
              <svg className="w-16 h-16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-text-primary mb-2">Rigging Complete!</h3>
            <p className="text-sm text-text-muted mb-4">
              {detectedType === 'humanoid' ? 'Humanoid' : detectedType === 'quadruped' ? 'Quadruped' : 'Custom'} skeleton applied
            </p>
            <label className="flex items-center justify-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={showSkeleton}
                onChange={(e) => setShowSkeleton(e.target.checked)}
                className="rounded text-primary"
              />
              <span className="text-sm text-text-primary">Show skeleton in viewer</span>
            </label>
          </div>
        )}

        {step === 'error' && (
          <div className="text-center py-8">
            <div className="w-16 h-16 mx-auto mb-4 text-error flex items-center justify-center">
              <svg className="w-16 h-16" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-text-primary mb-2">Rigging Failed</h3>
            <p className="text-sm text-error">{error || 'An unknown error occurred'}</p>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-border">
        {step === 'config' && (
          <div className="space-y-2">
            <button
              onClick={handleStartRigging}
              disabled={!canRig}
              className="w-full py-2 px-4 bg-primary text-white rounded-lg font-medium hover:bg-primary-dark disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {targetAsset?.isRigged ? 'Re-Rig Asset' : 'Start Auto-Rigging'}
            </button>
            {targetAsset?.isRigged && (
              <button
                onClick={handleResetRigging}
                disabled={isResetting}
                className="w-full py-2 px-4 bg-surface-light text-text-secondary rounded-lg font-medium hover:bg-surface-hover disabled:opacity-50 transition-colors"
              >
                {isResetting ? 'Resetting...' : 'Reset Rigging State'}
              </button>
            )}
          </div>
        )}

        {step === 'complete' && (
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="flex-1 py-2 px-4 bg-primary text-white rounded-lg font-medium hover:bg-primary-dark transition-colors"
            >
              Done
            </button>
            <button
              onClick={() => {
                reset();
                setStep('config');
              }}
              className="py-2 px-4 bg-surface-light text-text-primary rounded-lg font-medium hover:bg-surface-hover transition-colors"
            >
              Rig Another
            </button>
          </div>
        )}

        {step === 'error' && (
          <button
            onClick={() => {
              setError(null);
              setStep('config');
            }}
            className="w-full py-2 px-4 bg-primary text-white rounded-lg font-medium hover:bg-primary-dark transition-colors"
          >
            Try Again
          </button>
        )}
      </div>
    </div>
  );
}
