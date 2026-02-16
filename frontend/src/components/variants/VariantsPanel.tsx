/**
 * VariantsPanel - UI for managing asset variants and version history
 */

import { useState, useCallback, useEffect } from 'react';
import {
  generateVariants,
  getVariantGroup,
  getVersionHistory,
  createVersion,
  restoreVersion,
  setPrimaryVariant,
  type VariantGroupDetail,
  type VersionHistory,
} from '../../services/api/variants';

interface VariantsPanelProps {
  assetId: string;
  variantGroupId?: string | null;
  onSelectAsset?: (assetId: string) => void;
  onRefresh?: () => void;
}

export function VariantsPanel({
  assetId,
  variantGroupId,
  onSelectAsset,
  onRefresh,
}: VariantsPanelProps) {
  const [activeTab, setActiveTab] = useState<'variants' | 'history'>('variants');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Variants state
  const [variantGroup, setVariantGroup] = useState<VariantGroupDetail | null>(null);
  const [variantCount, setVariantCount] = useState(4);
  const [isGenerating, setIsGenerating] = useState(false);

  // Version history state
  const [versionHistory, setVersionHistory] = useState<VersionHistory | null>(null);

  // Load variant group if exists
  const loadVariantGroup = useCallback(async () => {
    if (!variantGroupId) {
      setVariantGroup(null);
      return;
    }

    try {
      const group = await getVariantGroup(variantGroupId);
      setVariantGroup(group);
    } catch (err) {
      console.error('Failed to load variant group:', err);
    }
  }, [variantGroupId]);

  // Load version history
  const loadVersionHistory = useCallback(async () => {
    try {
      const history = await getVersionHistory(assetId);
      setVersionHistory(history);
    } catch (err) {
      console.error('Failed to load version history:', err);
    }
  }, [assetId]);

  useEffect(() => {
    loadVariantGroup();
    loadVersionHistory();
  }, [loadVariantGroup, loadVersionHistory]);

  // Generate variants
  const handleGenerateVariants = async () => {
    setIsGenerating(true);
    setError(null);
    setSuccess(null);

    try {
      const result = await generateVariants(assetId, variantCount);
      if (result.success) {
        setSuccess(`Started generating ${variantCount} variants`);
        onRefresh?.();
      } else {
        setError(result.error || 'Failed to generate variants');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate variants');
    } finally {
      setIsGenerating(false);
    }
  };

  // Set primary variant
  const handleSetPrimary = async (variantAssetId: string) => {
    if (!variantGroupId) return;

    setIsLoading(true);
    try {
      await setPrimaryVariant(variantGroupId, variantAssetId);
      loadVariantGroup();
      setSuccess('Set as primary variant');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to set primary');
    } finally {
      setIsLoading(false);
    }
  };

  // Create version snapshot
  const handleCreateVersion = async () => {
    setIsLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const result = await createVersion(assetId, 'manual', 'Manual snapshot');
      if (result.success) {
        setSuccess(`Created version ${result.versionNumber}`);
        loadVersionHistory();
      } else {
        setError(result.error || 'Failed to create version');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create version');
    } finally {
      setIsLoading(false);
    }
  };

  // Restore version
  const handleRestoreVersion = async (versionId: string, versionNumber: number) => {
    if (!confirm(`Restore to version ${versionNumber}? Current state will be backed up.`)) {
      return;
    }

    setIsLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const result = await restoreVersion(versionId, true);
      if (result.success) {
        setSuccess(`Restored to version ${result.restoredVersion}`);
        loadVersionHistory();
        onRefresh?.();
      } else {
        setError(result.error || 'Failed to restore version');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to restore version');
    } finally {
      setIsLoading(false);
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-medium text-white flex items-center gap-2">
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
        </svg>
        Variants & History
      </h3>

      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-gray-800/50 rounded-lg">
        <button
          onClick={() => setActiveTab('variants')}
          className={`flex-1 py-1.5 text-xs font-medium rounded transition-colors ${
            activeTab === 'variants'
              ? 'bg-indigo-600 text-white'
              : 'text-gray-400 hover:text-white'
          }`}
        >
          Variants
        </button>
        <button
          onClick={() => setActiveTab('history')}
          className={`flex-1 py-1.5 text-xs font-medium rounded transition-colors ${
            activeTab === 'history'
              ? 'bg-indigo-600 text-white'
              : 'text-gray-400 hover:text-white'
          }`}
        >
          History
        </button>
      </div>

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

      {activeTab === 'variants' && (
        <div className="space-y-4">
          {/* Generate Variants */}
          <div className="p-3 bg-gray-800/50 rounded-lg">
            <h4 className="text-sm font-medium text-gray-300 mb-2">Generate Variants</h4>
            <p className="text-xs text-gray-400 mb-3">
              Create multiple versions with different random seeds.
            </p>
            <div className="flex items-center gap-2 mb-3">
              <label className="text-xs text-gray-400">Count:</label>
              <select
                value={variantCount}
                onChange={(e) => setVariantCount(Number(e.target.value))}
                className="flex-1 px-2 py-1 text-xs bg-gray-700 border border-gray-600 rounded text-white"
              >
                <option value={2}>2 variants</option>
                <option value={4}>4 variants</option>
                <option value={6}>6 variants</option>
                <option value={8}>8 variants</option>
              </select>
            </div>
            <button
              onClick={handleGenerateVariants}
              disabled={isGenerating}
              className="w-full py-1.5 text-xs font-medium text-white bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-600 disabled:cursor-not-allowed rounded transition-colors"
            >
              {isGenerating ? 'Generating...' : `Generate ${variantCount} Variants`}
            </button>
          </div>

          {/* Existing Variants */}
          {variantGroup && variantGroup.variants.length > 0 && (
            <div className="p-3 bg-gray-800/50 rounded-lg">
              <h4 className="text-sm font-medium text-gray-300 mb-2">
                {variantGroup.name}
                <span className="ml-2 text-xs text-gray-500">
                  ({variantGroup.variants.length} variants)
                </span>
              </h4>
              <div className="grid grid-cols-2 gap-2">
                {variantGroup.variants.map((variant) => (
                  <div
                    key={variant.id}
                    className={`relative p-2 rounded border cursor-pointer transition-colors ${
                      variant.isPrimary
                        ? 'border-indigo-500 bg-indigo-900/20'
                        : 'border-gray-700 hover:border-gray-600'
                    }`}
                    onClick={() => onSelectAsset?.(variant.id)}
                  >
                    {variant.thumbnailPath && (
                      <img
                        src={`/storage/${variant.thumbnailPath}`}
                        alt={variant.name}
                        className="w-full h-16 object-cover rounded mb-1"
                      />
                    )}
                    <div className="text-xs text-white truncate">{variant.name}</div>
                    <div className="text-xs text-gray-500">
                      Seed: {variant.generationSeed ?? 'N/A'}
                    </div>
                    {variant.isPrimary && (
                      <span className="absolute top-1 right-1 px-1 py-0.5 text-[10px] bg-indigo-600 text-white rounded">
                        Primary
                      </span>
                    )}
                    {!variant.isPrimary && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleSetPrimary(variant.id);
                        }}
                        className="absolute bottom-1 right-1 px-1 py-0.5 text-[10px] bg-gray-700 hover:bg-gray-600 text-white rounded"
                      >
                        Set Primary
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === 'history' && (
        <div className="space-y-4">
          {/* Create Snapshot */}
          <div className="p-3 bg-gray-800/50 rounded-lg">
            <h4 className="text-sm font-medium text-gray-300 mb-2">Version Snapshot</h4>
            <p className="text-xs text-gray-400 mb-3">
              Save current state as a version you can restore later.
            </p>
            <button
              onClick={handleCreateVersion}
              disabled={isLoading}
              className="w-full py-1.5 text-xs font-medium text-white bg-teal-600 hover:bg-teal-500 disabled:bg-gray-600 disabled:cursor-not-allowed rounded transition-colors"
            >
              {isLoading ? 'Creating...' : 'Create Snapshot'}
            </button>
          </div>

          {/* Version List */}
          {versionHistory && versionHistory.versions.length > 0 ? (
            <div className="p-3 bg-gray-800/50 rounded-lg">
              <h4 className="text-sm font-medium text-gray-300 mb-2">
                Version History
                <span className="ml-2 text-xs text-gray-500">
                  (Current: v{versionHistory.currentVersion})
                </span>
              </h4>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {versionHistory.versions.map((version) => (
                  <div
                    key={version.id}
                    className="p-2 bg-gray-900/50 rounded border border-gray-700"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-medium text-white">
                        Version {version.versionNumber}
                      </span>
                      <span className="text-[10px] text-gray-500">
                        {formatDate(version.createdAt)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <div>
                        <span className="text-[10px] px-1 py-0.5 bg-gray-700 text-gray-300 rounded">
                          {version.changeType.replace('_', ' ')}
                        </span>
                        {version.changeDescription && (
                          <span className="ml-2 text-[10px] text-gray-400">
                            {version.changeDescription}
                          </span>
                        )}
                      </div>
                      <button
                        onClick={() => handleRestoreVersion(version.id, version.versionNumber)}
                        disabled={isLoading}
                        className="px-2 py-0.5 text-[10px] bg-orange-600 hover:bg-orange-500 text-white rounded"
                      >
                        Restore
                      </button>
                    </div>
                    {version.vertexCount && (
                      <div className="text-[10px] text-gray-500 mt-1">
                        {version.vertexCount.toLocaleString()} verts, {version.faceCount?.toLocaleString()} faces
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="p-3 bg-gray-800/50 rounded-lg text-center">
              <p className="text-xs text-gray-400">No version history yet.</p>
              <p className="text-xs text-gray-500 mt-1">
                Create a snapshot to start tracking versions.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
