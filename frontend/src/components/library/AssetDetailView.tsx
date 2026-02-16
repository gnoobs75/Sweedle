/**
 * AssetDetailView - Full-width asset detail page for the full-page gallery.
 * Replaces the cramped AssetDetails sidebar with a spacious two-column layout.
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
  getAssetThumbnailUrl,
  getAssetDownloadUrl,
  getStorageBase,
} from '../../services/api/assets';
import { getAssetAnimations } from '../../services/api/animation';
import { Input } from '../ui/Input';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { TagSelector } from './TagManager';
import { GalleryViewer } from './GalleryViewer';
import { formatNumber, formatFileSize, formatDuration, formatRelativeTime } from '../../lib/utils';
import type { Asset } from '../../types';

const ANIMATION_EMOJIS: Record<string, string> = {
  idle: '🧘', walk: '🚶', run: '🏃', attack: '⚔️', jump: '🦘', die: '💀',
  sit: '🪑', lie_down: '🛏️', crouch: '🦆', dodge: '💨', wave: '👋',
  cheer: '🎉', pickup: '🤲', trot: '🐕', gallop: '🏇', tail_wag: '🐕',
  bite: '🦴', shake: '🐕‍🦺', pounce: '🐱', howl: '🐺', roll_over: '🔄', play_dead: '😵',
};

interface AssetDetailViewProps {
  asset: Asset;
  onBack: () => void;
}

export function AssetDetailView({ asset, onBack }: AssetDetailViewProps) {
  const { updateAsset: updateAssetInStore, removeAsset } = useLibraryStore();
  const { loadModel } = useViewerStore();
  const { addNotification, openModal, setActiveView } = useUIStore();
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

  const thumbnailUrl = asset.thumbnailPath
    ? `${getStorageBase()}/${asset.thumbnailPath.replace(/\\/g, '/').replace(/^\//, '')}`
    : getAssetThumbnailUrl(asset.id);

  // Reset edit state when asset changes
  useEffect(() => {
    setIsEditing(false);
    setEditedName(asset.name);
    setEditedDescription(asset.description || '');
    setEditedTags(asset.tags.map((t) => t.id));
  }, [asset.id]);

  // Load animations
  useEffect(() => {
    if (asset.isRigged && (asset.animationCount ?? 0) > 0) {
      setIsLoadingAnimations(true);
      getAssetAnimations(asset.id)
        .then(setAnimations)
        .catch(() => setAnimations([]))
        .finally(() => setIsLoadingAnimations(false));
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
      addNotification({ type: 'success', title: 'Asset Updated' });
    } catch (error) {
      addNotification({
        type: 'error',
        title: 'Update Failed',
        message: error instanceof Error ? error.message : 'Failed to save',
      });
    } finally {
      setIsSaving(false);
    }
  }, [asset.id, editedName, editedDescription, editedTags, updateAssetInStore, addNotification]);

  const handleDelete = useCallback(async () => {
    if (!window.confirm(`Delete "${asset.name}"? This cannot be undone.`)) return;
    setIsDeleting(true);
    try {
      await deleteAssetApi(asset.id);
      removeAsset(asset.id);
      onBack();
      addNotification({ type: 'success', title: 'Asset Deleted' });
    } catch (error) {
      addNotification({
        type: 'error',
        title: 'Delete Failed',
        message: error instanceof Error ? error.message : 'Failed to delete',
      });
    } finally {
      setIsDeleting(false);
    }
  }, [asset, removeAsset, onBack, addNotification]);

  const handleFavoriteToggle = useCallback(async () => {
    try {
      const updated = await updateAsset(asset.id, { isFavorite: !asset.isFavorite });
      updateAssetInStore(asset.id, { isFavorite: updated.isFavorite });
    } catch {
      addNotification({ type: 'error', title: 'Failed to update favorite' });
    }
  }, [asset, updateAssetInStore, addNotification]);

  const handleViewIn3D = useCallback(() => {
    if (asset.isRigged && asset.riggingData) {
      try {
        setSkeletonData(asset.riggingData as unknown as SkeletonData);
        if (asset.characterType) {
          setCharacterType(asset.characterType as 'humanoid' | 'quadruped');
        }
        if (animations.length > 0) {
          setClips(animations);
        }
      } catch (error) {
        console.error('Failed to load skeleton data:', error);
      }
    } else {
      setSkeletonData(null);
      setClips([]);
    }
    loadModel(getAssetModelUrl(asset.id), asset.id);
    setActiveView('workspace');
  }, [asset, animations, loadModel, setSkeletonData, setCharacterType, setClips, setActiveView]);

  const handleDownload = useCallback(async () => {
    try {
      const response = await fetch(getAssetDownloadUrl(asset.id));
      if (!response.ok) throw new Error('Failed to download');
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${asset.name}.glb`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      addNotification({ type: 'success', title: 'Download Started' });
    } catch (error) {
      addNotification({
        type: 'error',
        title: 'Download Failed',
        message: error instanceof Error ? error.message : 'Failed to download',
      });
    }
  }, [asset.id, asset.name, addNotification]);

  return (
    <div className="max-w-5xl mx-auto">
      {/* Back button */}
      <button
        onClick={onBack}
        className="flex items-center gap-2 text-text-muted hover:text-text-primary transition-colors mb-6 group"
      >
        <svg className="w-5 h-5 transition-transform group-hover:-translate-x-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        <span className="text-sm font-medium">Back to Library</span>
      </button>

      {/* Two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Left: 3D Viewer / Thumbnail */}
        <div>
          <GalleryViewer
            assetId={asset.id}
            isRigged={asset.isRigged}
            animationCount={asset.animationCount ?? 0}
            animations={animations}
            thumbnailUrl={thumbnailUrl}
          />
        </div>

        {/* Right: Details */}
        <div className="space-y-6">
          {/* Name & Favorite */}
          <div className="flex items-start justify-between gap-4">
            {isEditing ? (
              <div className="flex-1 space-y-3">
                <Input label="Name" value={editedName} onChange={(e) => setEditedName(e.target.value)} />
                <div>
                  <label className="block text-sm font-medium text-text-secondary mb-1.5">Description</label>
                  <textarea
                    value={editedDescription}
                    onChange={(e) => setEditedDescription(e.target.value)}
                    className="w-full h-24 px-3 py-2 bg-surface-light border border-border rounded-lg text-text-primary resize-none focus:outline-none focus:ring-2 focus:ring-primary/50"
                    placeholder="Add a description..."
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-text-secondary mb-1.5">Tags</label>
                  <TagSelector selectedTags={editedTags} onChange={setEditedTags} />
                </div>
                <div className="flex gap-2">
                  <Button variant="primary" onClick={handleSave} isLoading={isSaving}>Save</Button>
                  <Button variant="ghost" onClick={() => {
                    setIsEditing(false);
                    setEditedName(asset.name);
                    setEditedDescription(asset.description || '');
                    setEditedTags(asset.tags.map((t) => t.id));
                  }}>Cancel</Button>
                </div>
              </div>
            ) : (
              <div className="flex-1">
                <div className="flex items-center gap-3">
                  <h1 className="text-2xl font-bold text-text-primary">{asset.name}</h1>
                  <button onClick={handleFavoriteToggle} className="p-1">
                    <svg
                      className={`w-5 h-5 ${asset.isFavorite ? 'text-warning' : 'text-text-muted hover:text-warning'}`}
                      fill={asset.isFavorite ? 'currentColor' : 'none'}
                      viewBox="0 0 24 24" stroke="currentColor"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                        d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
                    </svg>
                  </button>
                  <button
                    onClick={() => setIsEditing(true)}
                    className="p-1 text-text-muted hover:text-text-primary"
                    title="Edit"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                        d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    </svg>
                  </button>
                </div>
                {asset.description && (
                  <p className="text-text-muted mt-2">{asset.description}</p>
                )}
              </div>
            )}
          </div>

          {/* Tags */}
          {!isEditing && asset.tags.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {asset.tags.map((tag) => (
                <Badge key={tag.id} variant="default" style={{ backgroundColor: `${tag.color}20`, color: tag.color }}>
                  {tag.name}
                </Badge>
              ))}
            </div>
          )}

          {/* Status badges */}
          <div className="flex flex-wrap gap-2">
            <Badge variant="default" size="sm">{asset.sourceType.replace('_', ' ')}</Badge>
            {asset.hasLod && <Badge variant="info" size="sm">Has LOD</Badge>}
            {asset.hasTexture ? (
              <Badge variant="success" size="sm">Textured</Badge>
            ) : (
              <Badge variant="warning" size="sm">No Texture</Badge>
            )}
            {asset.isRigged && <Badge variant="success" size="sm">Rigged</Badge>}
            {(asset.animationCount ?? 0) > 0 && (
              <Badge variant="primary" size="sm">{asset.animationCount} Animation{(asset.animationCount ?? 0) !== 1 ? 's' : ''}</Badge>
            )}
          </div>

          {/* Stats grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[
              { label: 'Vertices', value: asset.vertexCount ? formatNumber(asset.vertexCount) : '--' },
              { label: 'Faces', value: asset.faceCount ? formatNumber(asset.faceCount) : '--' },
              { label: 'File Size', value: asset.fileSizeBytes ? formatFileSize(asset.fileSizeBytes) : '--' },
              { label: 'Gen Time', value: asset.generationTimeSeconds ? formatDuration(asset.generationTimeSeconds) : '--' },
            ].map(({ label, value }) => (
              <div key={label} className="bg-surface-light rounded-lg p-3 border border-border">
                <div className="text-xs text-text-muted">{label}</div>
                <div className="text-sm font-mono font-medium text-text-primary mt-0.5">{value}</div>
              </div>
            ))}
          </div>

          {/* Metadata */}
          <div className="flex gap-6 text-sm text-text-muted">
            <span>Created {formatRelativeTime(asset.createdAt)}</span>
            <span>Updated {formatRelativeTime(asset.updatedAt)}</span>
            <span className="font-mono text-xs">ID: {asset.id.slice(0, 8)}</span>
          </div>

          {/* Animation section */}
          {asset.isRigged && (
            <div className="bg-surface-light rounded-lg border border-border p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-text-primary">Animations</h3>
                {asset.characterType && (
                  <Badge variant="success" size="sm">{asset.characterType}</Badge>
                )}
              </div>
              {isLoadingAnimations ? (
                <p className="text-sm text-text-muted">Loading animations...</p>
              ) : animations.length > 0 ? (
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  {animations.map((clip) => (
                    <div key={clip.id} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-surface border border-border">
                      <span>{ANIMATION_EMOJIS[clip.animationType] || '🎬'}</span>
                      <span className="text-sm text-text-primary truncate">{clip.name}</span>
                      <span className="text-xs text-text-muted ml-auto flex-shrink-0">{clip.duration.toFixed(1)}s</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-text-muted">No animations yet</p>
              )}
            </div>
          )}

          {/* Action buttons */}
          <div className="flex flex-wrap gap-3 pt-2">
            <Button variant="primary" onClick={handleViewIn3D}>
              <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
              View in 3D
            </Button>
            <Button variant="secondary" onClick={handleDownload}>
              <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Download
            </Button>
            <Button variant="secondary" onClick={() => openModal('export', { assetId: asset.id })}>
              <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
              </svg>
              Export
            </Button>
            <Button
              variant="ghost"
              className="text-error hover:bg-error/10"
              onClick={handleDelete}
              isLoading={isDeleting}
            >
              <svg className="w-4 h-4 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
              Delete
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
