/**
 * AssetDetails Component - Asset information and actions sidebar
 */

import { useState, useCallback, useEffect } from 'react';
import { useLibraryStore } from '../../stores/libraryStore';
import { useViewerStore } from '../../stores/viewerStore';
import { useUIStore } from '../../stores/uiStore';
import { useRiggingStore, type SkeletonData } from '../../stores/riggingStore';
import { useAnimationStore, type AnimationClip } from '../../stores/animationStore';
import {
  updateAsset,
  deleteAsset as deleteAssetApi,
  getAssetModelUrl,
  getAssetDownloadUrl,
} from '../../services/api/assets';
import { getAssetAnimations } from '../../services/api/animation';
import { Input } from '../ui/Input';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { Card } from '../ui/Card';
import { TagSelector } from './TagManager';
import { cn, formatNumber, formatFileSize, formatDuration, formatRelativeTime } from '../../lib/utils';
import type { Asset } from '../../types';

// Animation type to emoji mapping
const ANIMATION_EMOJIS: Record<string, string> = {
  idle: '🧘',
  walk: '🚶',
  run: '🏃',
  attack: '⚔️',
  jump: '🦘',
  die: '💀',
  sit: '🪑',
  lie_down: '🛏️',
  crouch: '🦆',
  dodge: '💨',
  wave: '👋',
  cheer: '🎉',
  pickup: '🤲',
  trot: '🐕',
  gallop: '🏇',
  tail_wag: '🐕',
  bite: '🦴',
  shake: '🐕‍🦺',
  pounce: '🐱',
  howl: '🐺',
  roll_over: '🔄',
  play_dead: '😵',
};

interface AssetDetailsProps {
  asset: Asset;
  onClose?: () => void;
  className?: string;
}

export function AssetDetails({ asset, onClose, className }: AssetDetailsProps) {
  const { updateAsset: updateAssetInStore, removeAsset } = useLibraryStore();
  const { loadModel } = useViewerStore();
  const { addNotification, openModal } = useUIStore();
  const { setSkeletonData, setCharacterType } = useRiggingStore();
  const { setClips } = useAnimationStore();

  const [isEditing, setIsEditing] = useState(false);
  const [editedName, setEditedName] = useState(asset.name);
  const [editedDescription, setEditedDescription] = useState(asset.description || '');
  const [editedTags, setEditedTags] = useState(asset.tags.map((t) => t.id));
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [animations, setAnimations] = useState<AnimationClip[]>([]);
  const [isLoadingAnimations, setIsLoadingAnimations] = useState(false);

  // Load animations when asset changes and has animations
  useEffect(() => {
    if (asset.isRigged && (asset.animationCount ?? 0) > 0) {
      setIsLoadingAnimations(true);
      getAssetAnimations(asset.id)
        .then((clips) => {
          setAnimations(clips);
        })
        .catch((error) => {
          console.error('Failed to load animations:', error);
          setAnimations([]);
        })
        .finally(() => {
          setIsLoadingAnimations(false);
        });
    } else {
      setAnimations([]);
    }
  }, [asset.id, asset.isRigged, asset.animationCount]);

  const handleSave = useCallback(async () => {
    setIsSaving(true);
    try {
      const updated = await updateAsset(asset.id, {
        name: editedName,
        description: editedDescription,
        tags: editedTags,
      });
      updateAssetInStore(asset.id, updated);
      setIsEditing(false);
      addNotification({
        type: 'success',
        title: 'Asset Updated',
        message: 'Changes saved successfully',
      });
    } catch (error) {
      addNotification({
        type: 'error',
        title: 'Update Failed',
        message: error instanceof Error ? error.message : 'Failed to save changes',
      });
    } finally {
      setIsSaving(false);
    }
  }, [asset.id, editedName, editedDescription, editedTags, updateAssetInStore, addNotification]);

  const handleDelete = useCallback(async () => {
    const confirmed = window.confirm(
      `Are you sure you want to delete "${asset.name}"? This action cannot be undone.`
    );
    if (!confirmed) return;

    setIsDeleting(true);
    try {
      await deleteAssetApi(asset.id);
      removeAsset(asset.id);
      onClose?.();
      addNotification({
        type: 'success',
        title: 'Asset Deleted',
        message: `"${asset.name}" has been deleted`,
      });
    } catch (error) {
      addNotification({
        type: 'error',
        title: 'Delete Failed',
        message: error instanceof Error ? error.message : 'Failed to delete asset',
      });
    } finally {
      setIsDeleting(false);
    }
  }, [asset, removeAsset, onClose, addNotification]);

  const handleFavoriteToggle = useCallback(async () => {
    try {
      const updated = await updateAsset(asset.id, {
        isFavorite: !asset.isFavorite,
      });
      updateAssetInStore(asset.id, { isFavorite: updated.isFavorite });
    } catch (error) {
      addNotification({
        type: 'error',
        title: 'Update Failed',
        message: 'Failed to update favorite status',
      });
    }
  }, [asset, updateAssetInStore, addNotification]);

  const handleViewInViewer = useCallback(() => {
    // Load skeleton if rigged - this enables animation playback in ViewerToolbar
    if (asset.isRigged && asset.riggingData) {
      try {
        const skeleton = asset.riggingData as SkeletonData;
        setSkeletonData(skeleton);
        if (asset.characterType) {
          setCharacterType(asset.characterType as 'humanoid' | 'quadruped');
        }
        // Pre-load animations into the animation store
        if (animations.length > 0) {
          setClips(animations);
        }
      } catch (error) {
        console.error('Failed to load skeleton data:', error);
      }
    } else {
      // Clear skeleton data if not rigged
      setSkeletonData(null);
      setClips([]);
    }

    loadModel(getAssetModelUrl(asset.id), asset.id);
  }, [asset, animations, loadModel, setSkeletonData, setCharacterType, setClips]);

  const handleExport = useCallback(() => {
    openModal('export', { assetId: asset.id });
  }, [asset.id, openModal]);

  const handleDownload = useCallback(async () => {
    try {
      const url = getAssetDownloadUrl(asset.id);

      // Fetch the file
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error('Failed to download file');
      }

      // Get the blob
      const blob = await response.blob();

      // Create download link
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = `${asset.name}.glb`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);

      addNotification({
        type: 'success',
        title: 'Download Started',
        message: `Downloading ${asset.name}.glb`,
      });
    } catch (error) {
      addNotification({
        type: 'error',
        title: 'Download Failed',
        message: error instanceof Error ? error.message : 'Failed to download file',
      });
    }
  }, [asset.id, asset.name, addNotification]);

  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* Header */}
      <div className="p-4 border-b border-border flex items-center justify-between">
        <h2 className="text-lg font-semibold text-text-primary">Asset Details</h2>
        {onClose && (
          <button
            onClick={onClose}
            className="p-1 text-text-muted hover:text-text-primary transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Preview */}
        <div className="aspect-square rounded-xl overflow-hidden bg-surface-light">
          {asset.thumbnailPath ? (
            <img
              src={asset.thumbnailPath}
              alt={asset.name}
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <svg
                className="w-16 h-16 text-text-muted"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"
                />
              </svg>
            </div>
          )}
        </div>

        {/* Quick Actions */}
        <div className="flex gap-2">
          <Button variant="primary" className="flex-1" onClick={handleViewInViewer}>
            <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
            </svg>
            View
          </Button>
          <Button variant="secondary" onClick={handleFavoriteToggle}>
            <svg
              className={cn('w-4 h-4', asset.isFavorite && 'text-warning')}
              fill={asset.isFavorite ? 'currentColor' : 'none'}
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
            </svg>
          </Button>
        </div>

        {/* Name & Description */}
        {isEditing ? (
          <div className="space-y-3">
            <Input
              label="Name"
              value={editedName}
              onChange={(e) => setEditedName(e.target.value)}
            />
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-1.5">
                Description
              </label>
              <textarea
                value={editedDescription}
                onChange={(e) => setEditedDescription(e.target.value)}
                className="w-full h-24 px-3 py-2 bg-surface-light border border-border rounded-lg text-text-primary resize-none focus:outline-none focus:ring-2 focus:ring-primary/50"
                placeholder="Add a description..."
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-1.5">
                Tags
              </label>
              <TagSelector
                selectedTags={editedTags}
                onChange={setEditedTags}
              />
            </div>
            <div className="flex gap-2">
              <Button
                variant="primary"
                className="flex-1"
                onClick={handleSave}
                isLoading={isSaving}
              >
                Save
              </Button>
              <Button
                variant="ghost"
                onClick={() => {
                  setIsEditing(false);
                  setEditedName(asset.name);
                  setEditedDescription(asset.description || '');
                  setEditedTags(asset.tags.map((t) => t.id));
                }}
              >
                Cancel
              </Button>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-lg font-semibold text-text-primary">{asset.name}</h3>
                {asset.description && (
                  <p className="text-sm text-text-muted mt-1">{asset.description}</p>
                )}
              </div>
              <Button variant="ghost" size="sm" onClick={() => setIsEditing(true)}>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
              </Button>
            </div>

            {/* Tags */}
            {asset.tags.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {asset.tags.map((tag) => (
                  <Badge
                    key={tag.id}
                    variant="default"
                    style={{ backgroundColor: `${tag.color}20`, color: tag.color }}
                  >
                    {tag.name}
                  </Badge>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Stats */}
        <Card variant="outlined" padding="sm">
          <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">
            Statistics
          </h4>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <span className="text-text-muted">Vertices</span>
              <p className="font-mono text-text-primary">
                {asset.vertexCount ? formatNumber(asset.vertexCount) : '--'}
              </p>
            </div>
            <div>
              <span className="text-text-muted">Faces</span>
              <p className="font-mono text-text-primary">
                {asset.faceCount ? formatNumber(asset.faceCount) : '--'}
              </p>
            </div>
            <div>
              <span className="text-text-muted">File Size</span>
              <p className="font-mono text-text-primary">
                {asset.fileSizeBytes ? formatFileSize(asset.fileSizeBytes) : '--'}
              </p>
            </div>
            <div>
              <span className="text-text-muted">Generation Time</span>
              <p className="font-mono text-text-primary">
                {asset.generationTimeSeconds
                  ? formatDuration(asset.generationTimeSeconds)
                  : '--'}
              </p>
            </div>
          </div>

          {/* Badges */}
          <div className="flex gap-1 mt-3 pt-3 border-t border-border flex-wrap">
            {asset.hasLod && <Badge variant="info" size="sm">Has LOD</Badge>}
            {asset.hasTexture ? (
              <Badge variant="success" size="sm">Textured</Badge>
            ) : (
              <Badge variant="warning" size="sm">No Texture</Badge>
            )}
            {asset.isRigged && <Badge variant="success" size="sm">Rigged</Badge>}
            {(asset.animationCount ?? 0) > 0 && (
              <Badge variant="primary" size="sm">{asset.animationCount} Anim</Badge>
            )}
            <Badge variant="default" size="sm">{asset.sourceType.replace('_', ' ')}</Badge>
          </div>
        </Card>

        {/* Metadata */}
        <Card variant="outlined" padding="sm">
          <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">
            Metadata
          </h4>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-text-muted">Created</span>
              <span className="text-text-primary">{formatRelativeTime(asset.createdAt)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-muted">Updated</span>
              <span className="text-text-primary">{formatRelativeTime(asset.updatedAt)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-muted">ID</span>
              <span className="text-text-primary font-mono text-xs">{asset.id.slice(0, 8)}...</span>
            </div>
          </div>
        </Card>

        {/* Rigging & Animation Info */}
        {asset.isRigged && (
          <Card variant="outlined" padding="sm">
            <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">
              Rigging & Animation
            </h4>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between items-center">
                <span className="text-text-muted">Character Type</span>
                <Badge variant="success" size="sm">
                  {asset.characterType || 'Unknown'}
                </Badge>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-text-muted">Animations</span>
                <span className="text-text-primary">
                  {isLoadingAnimations ? (
                    <span className="text-text-muted">Loading...</span>
                  ) : (
                    `${animations.length} clip${animations.length !== 1 ? 's' : ''}`
                  )}
                </span>
              </div>
            </div>

            {/* Animation List */}
            {animations.length > 0 && (
              <div className="mt-3 pt-3 border-t border-border">
                <div className="space-y-1.5">
                  {animations.map((clip) => (
                    <div
                      key={clip.id}
                      className="flex items-center justify-between px-2 py-1.5 rounded bg-surface-light"
                    >
                      <div className="flex items-center gap-2">
                        <span className="text-sm">
                          {ANIMATION_EMOJIS[clip.animationType] || '🎬'}
                        </span>
                        <span className="text-sm text-text-primary">{clip.name}</span>
                      </div>
                      <span className="text-xs text-text-muted">
                        {clip.duration.toFixed(1)}s
                      </span>
                    </div>
                  ))}
                </div>
                <p className="text-xs text-text-muted mt-2">
                  Click "View" to preview animations in the 3D viewer
                </p>
              </div>
            )}
          </Card>
        )}
      </div>

      {/* Footer Actions */}
      <div className="p-4 border-t border-border space-y-2">
        <div className="flex gap-2">
          <Button variant="secondary" className="flex-1" onClick={handleDownload}>
            <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Download
          </Button>
          <Button variant="secondary" className="flex-1" onClick={handleExport}>
            <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            Export
          </Button>
        </div>
        <Button
          variant="ghost"
          className="w-full text-error hover:bg-error/10"
          onClick={handleDelete}
          isLoading={isDeleting}
        >
          <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
          Delete Asset
        </Button>
      </div>
    </div>
  );
}
