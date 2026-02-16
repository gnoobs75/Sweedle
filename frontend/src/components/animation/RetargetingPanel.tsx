/**
 * RetargetingPanel - UI for animation retargeting between skeletons
 */

import { useState, useCallback, useEffect } from 'react';
import {
  listRetargetingPresets,
  suggestBoneMappings,
  retargetAnimation,
  type RetargetingPresetInfo,
  type BoneMappingSuggestion,
  type RetargetingPreset,
  type BoneMapping,
} from '../../services/api/animation';

interface RetargetingPanelProps {
  sourceClipId: string;
  sourceAssetId: string;
  onClose?: () => void;
  onRetargetComplete?: (newClipId: string) => void;
}

export function RetargetingPanel({
  sourceClipId,
  sourceAssetId,
  onClose,
  onRetargetComplete,
}: RetargetingPanelProps) {
  const [step, setStep] = useState<'select' | 'mapping' | 'retarget'>('select');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Target selection
  const [targetAssetId, setTargetAssetId] = useState('');
  const [targetAssetName, setTargetAssetName] = useState('');

  // Presets
  const [presets, setPresets] = useState<RetargetingPresetInfo[]>([]);
  const [selectedPreset, setSelectedPreset] = useState<RetargetingPreset | null>(null);

  // Bone mapping
  const [suggestions, setSuggestions] = useState<BoneMappingSuggestion[]>([]);
  const [customMappings, setCustomMappings] = useState<BoneMapping[]>([]);
  const [sourceBones, setSourceBones] = useState<string[]>([]);
  const [targetBones, setTargetBones] = useState<string[]>([]);
  const [unmappedSource, setUnmappedSource] = useState<string[]>([]);
  const [unmappedTarget, setUnmappedTarget] = useState<string[]>([]);

  // Options
  const [adjustProportions, setAdjustProportions] = useState(true);
  const [preserveRootMotion, setPreserveRootMotion] = useState(true);
  const [animationName, setAnimationName] = useState('');

  // Load presets
  useEffect(() => {
    listRetargetingPresets()
      .then(setPresets)
      .catch(console.error);
  }, []);

  // Get bone mapping suggestions
  const loadSuggestions = useCallback(async () => {
    if (!targetAssetId) return;

    setIsLoading(true);
    setError(null);

    try {
      const result = await suggestBoneMappings(sourceAssetId, targetAssetId);
      if (result.success) {
        setSuggestions(result.suggestions);
        setSourceBones(result.sourceBones);
        setTargetBones(result.targetBones);
        setUnmappedSource(result.unmappedSource);
        setUnmappedTarget(result.unmappedTarget);
        // Initialize custom mappings from suggestions
        setCustomMappings(result.suggestions.map(s => ({
          sourceBone: s.sourceBone,
          targetBone: s.targetBone,
          scaleFactor: 1.0,
        })));
        setStep('mapping');
      } else {
        setError(result.message);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to get suggestions');
    } finally {
      setIsLoading(false);
    }
  }, [sourceAssetId, targetAssetId]);

  // Perform retargeting
  const handleRetarget = async () => {
    setIsLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const result = await retargetAnimation({
        sourceClipId,
        targetAssetId,
        name: animationName || undefined,
        preset: selectedPreset || undefined,
        customMappings: customMappings.length > 0 ? customMappings : undefined,
        adjustProportions,
        preserveRootMotion,
      });

      if (result.success && result.clipId) {
        setSuccess(`Retargeted animation with ${result.sourceBonesMapped} bones mapped`);
        onRetargetComplete?.(result.clipId);
      } else {
        setError(result.error || result.message);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to retarget');
    } finally {
      setIsLoading(false);
    }
  };

  // Update a single mapping
  const updateMapping = (sourceBone: string, targetBone: string) => {
    setCustomMappings(prev => {
      const existing = prev.findIndex(m => m.sourceBone === sourceBone);
      if (existing >= 0) {
        const updated = [...prev];
        updated[existing] = { ...updated[existing], targetBone };
        return updated;
      }
      return [...prev, { sourceBone, targetBone, scaleFactor: 1.0 }];
    });
  };

  // Remove a mapping
  const removeMapping = (sourceBone: string) => {
    setCustomMappings(prev => prev.filter(m => m.sourceBone !== sourceBone));
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-900 rounded-lg border border-gray-700 max-w-2xl w-full max-h-[80vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <h2 className="text-lg font-medium text-white flex items-center gap-2">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
            </svg>
            Animation Retargeting
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Status messages */}
          {error && (
            <div className="p-2 bg-red-900/20 border border-red-700/30 rounded text-sm text-red-400">
              {error}
            </div>
          )}
          {success && (
            <div className="p-2 bg-green-900/20 border border-green-700/30 rounded text-sm text-green-400">
              {success}
            </div>
          )}

          {step === 'select' && (
            <>
              {/* Target Asset Selection */}
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-300">
                  Target Asset ID
                </label>
                <p className="text-xs text-gray-500">
                  Enter the ID of the rigged asset to apply the animation to.
                </p>
                <input
                  type="text"
                  value={targetAssetId}
                  onChange={(e) => setTargetAssetId(e.target.value)}
                  placeholder="e.g., abc123-def456-..."
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm text-white placeholder-gray-500"
                />
              </div>

              {/* Preset Selection */}
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-300">
                  Mapping Preset (Optional)
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => setSelectedPreset('auto_detect')}
                    className={`p-2 text-left rounded border ${
                      selectedPreset === 'auto_detect'
                        ? 'border-indigo-500 bg-indigo-900/30'
                        : 'border-gray-700 hover:border-gray-600'
                    }`}
                  >
                    <div className="text-sm text-white">Auto Detect</div>
                    <div className="text-xs text-gray-400">Smart matching</div>
                  </button>
                  {presets.map(preset => (
                    <button
                      key={preset.id}
                      onClick={() => setSelectedPreset(preset.id)}
                      className={`p-2 text-left rounded border ${
                        selectedPreset === preset.id
                          ? 'border-indigo-500 bg-indigo-900/30'
                          : 'border-gray-700 hover:border-gray-600'
                      }`}
                    >
                      <div className="text-sm text-white">{preset.name}</div>
                      <div className="text-xs text-gray-400">{preset.mappingsCount} mappings</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Next Button */}
              <button
                onClick={loadSuggestions}
                disabled={!targetAssetId || isLoading}
                className="w-full py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-700 disabled:cursor-not-allowed rounded"
              >
                {isLoading ? 'Loading...' : 'Configure Bone Mapping'}
              </button>
            </>
          )}

          {step === 'mapping' && (
            <>
              {/* Bone Mapping Editor */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="block text-sm font-medium text-gray-300">
                    Bone Mappings
                  </label>
                  <span className="text-xs text-gray-500">
                    {customMappings.length} mapped, {unmappedSource.length} unmapped
                  </span>
                </div>
                <div className="max-h-64 overflow-y-auto space-y-1 bg-gray-800/50 rounded p-2">
                  {customMappings.map((mapping, idx) => {
                    const suggestion = suggestions.find(s => s.sourceBone === mapping.sourceBone);
                    return (
                      <div
                        key={idx}
                        className="flex items-center gap-2 p-1.5 bg-gray-900/50 rounded"
                      >
                        <span className="text-xs text-gray-400 w-32 truncate" title={mapping.sourceBone}>
                          {mapping.sourceBone}
                        </span>
                        <span className="text-gray-600">→</span>
                        <select
                          value={mapping.targetBone}
                          onChange={(e) => updateMapping(mapping.sourceBone, e.target.value)}
                          className="flex-1 px-2 py-1 text-xs bg-gray-700 border border-gray-600 rounded text-white"
                        >
                          <option value="">-- Unmapped --</option>
                          {targetBones.map(bone => (
                            <option key={bone} value={bone}>{bone}</option>
                          ))}
                        </select>
                        {suggestion && (
                          <span
                            className={`text-[10px] px-1 py-0.5 rounded ${
                              suggestion.confidence > 0.7
                                ? 'bg-green-900/30 text-green-400'
                                : 'bg-yellow-900/30 text-yellow-400'
                            }`}
                          >
                            {Math.round(suggestion.confidence * 100)}%
                          </span>
                        )}
                        <button
                          onClick={() => removeMapping(mapping.sourceBone)}
                          className="text-red-400 hover:text-red-300"
                        >
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Options */}
              <div className="space-y-2">
                <label className="flex items-center gap-2 text-sm text-gray-300">
                  <input
                    type="checkbox"
                    checked={adjustProportions}
                    onChange={(e) => setAdjustProportions(e.target.checked)}
                    className="rounded border-gray-600"
                  />
                  Adjust for different proportions
                </label>
                <label className="flex items-center gap-2 text-sm text-gray-300">
                  <input
                    type="checkbox"
                    checked={preserveRootMotion}
                    onChange={(e) => setPreserveRootMotion(e.target.checked)}
                    className="rounded border-gray-600"
                  />
                  Preserve root motion
                </label>
              </div>

              {/* Animation Name */}
              <div className="space-y-2">
                <label className="block text-sm font-medium text-gray-300">
                  New Animation Name (Optional)
                </label>
                <input
                  type="text"
                  value={animationName}
                  onChange={(e) => setAnimationName(e.target.value)}
                  placeholder="e.g., Idle (Retargeted)"
                  className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm text-white placeholder-gray-500"
                />
              </div>

              {/* Buttons */}
              <div className="flex gap-2">
                <button
                  onClick={() => setStep('select')}
                  className="flex-1 py-2 text-sm font-medium text-gray-300 bg-gray-700 hover:bg-gray-600 rounded"
                >
                  Back
                </button>
                <button
                  onClick={handleRetarget}
                  disabled={customMappings.length === 0 || isLoading}
                  className="flex-1 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-700 disabled:cursor-not-allowed rounded"
                >
                  {isLoading ? 'Retargeting...' : 'Apply Retargeting'}
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
