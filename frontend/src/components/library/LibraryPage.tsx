/**
 * LibraryPage - Full-page gallery view.
 * Clean layout: top bar with search/filters, asset grid, click-through to detail view.
 */

import { useEffect, useCallback, useState } from 'react';
import { useLibraryStore } from '../../stores/libraryStore';
import { useUIStore } from '../../stores/uiStore';
import { listAssets, listTags } from '../../services/api/assets';
import { regenerateThumbnail } from '../../services/api/export';
import { SearchBar } from './SearchBar';
import { AssetGrid } from './AssetGrid';
import { BulkActions, SelectionToggle } from './BulkActions';
import { TagManager } from './TagManager';
import { AssetDetailView } from './AssetDetailView';
import { Button } from '../ui/Button';
import { Tooltip } from '../ui/Tooltip';
import type { Asset } from '../../types';

export function LibraryPage() {
  const {
    assets,
    filters,
    viewMode,
    page,
    pageSize,
    totalAssets,
    selectedAssetIds,
    currentAssetId,
    isLoading,
    error,
    setAssets,
    setTags,
    setTotalAssets,
    setLoading,
    setError,
    setPage,
    toggleAssetSelection,
    setCurrentAsset,
  } = useLibraryStore();

  const { addNotification } = useUIStore();

  const [showTags, setShowTags] = useState(false);
  const [isSelecting, setIsSelecting] = useState(false);
  const [isRegeneratingThumbnails, setIsRegeneratingThumbnails] = useState(false);
  const [thumbnailProgress, setThumbnailProgress] = useState({ current: 0, total: 0 });

  // Fetch assets
  const fetchAssets = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await listAssets({
        page,
        pageSize,
        search: filters.search,
        tags: filters.tags,
        sourceType: filters.sourceType === 'all' ? undefined : filters.sourceType,
        hasLod: filters.hasLod ?? undefined,
        isFavorite: filters.isFavorite ?? undefined,
        folderId: filters.folderId ?? undefined,
        sortBy: filters.sortBy,
        sortOrder: filters.sortOrder,
      });
      setAssets(response.assets);
      setTotalAssets(response.total);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load assets';
      setError(message);
      addNotification({ type: 'error', title: 'Failed to Load Assets', message });
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, filters, setAssets, setTotalAssets, setLoading, setError, addNotification]);

  // Fetch tags
  const fetchTags = useCallback(async () => {
    try {
      const tags = await listTags();
      setTags(tags);
    } catch (err) {
      console.error('Failed to load tags:', err);
    }
  }, [setTags]);

  // Initial load
  useEffect(() => {
    fetchAssets();
    fetchTags();
  }, [fetchAssets, fetchTags]);

  // Regenerate all thumbnails
  const handleRegenerateAllThumbnails = useCallback(async () => {
    if (assets.length === 0) return;
    setIsRegeneratingThumbnails(true);
    setThumbnailProgress({ current: 0, total: assets.length });

    let successCount = 0;
    let failCount = 0;

    for (let i = 0; i < assets.length; i++) {
      setThumbnailProgress({ current: i + 1, total: assets.length });
      try {
        await regenerateThumbnail(assets[i].id);
        successCount++;
      } catch {
        failCount++;
      }
    }

    setIsRegeneratingThumbnails(false);
    setThumbnailProgress({ current: 0, total: 0 });
    fetchAssets();

    addNotification({
      type: failCount > 0 ? 'warning' : 'success',
      title: 'Thumbnails Regenerated',
      message: `${successCount} done${failCount > 0 ? `, ${failCount} failed` : ''}`,
    });
  }, [assets, fetchAssets, addNotification]);

  // Selected asset for detail view
  const selectedAsset = currentAssetId ? assets.find((a) => a.id === currentAssetId) : undefined;

  const handleAssetClick = useCallback((asset: Asset) => {
    if (isSelecting) {
      toggleAssetSelection(asset.id);
    } else {
      setCurrentAsset(asset.id);
    }
  }, [isSelecting, toggleAssetSelection, setCurrentAsset]);

  const handleAssetSelect = useCallback((_id: string) => {
    toggleAssetSelection(_id);
  }, [toggleAssetSelection]);

  const handleBackToGrid = useCallback(() => {
    setCurrentAsset(null);
  }, [setCurrentAsset]);

  const totalPages = Math.ceil(totalAssets / pageSize);

  // If an asset is selected, show its detail view
  if (selectedAsset) {
    return (
      <div className="h-full overflow-y-auto p-6 lg:p-10">
        <AssetDetailView asset={selectedAsset} onBack={handleBackToGrid} />
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Top bar */}
      <div className="flex-shrink-0 px-6 py-4 border-b border-border bg-surface">
        <div className="flex items-center gap-4 max-w-7xl mx-auto">
          {/* Title & count */}
          <div className="flex-shrink-0">
            <h1 className="text-xl font-bold text-text-primary">Library</h1>
            <p className="text-xs text-text-muted">
              {totalAssets} asset{totalAssets !== 1 ? 's' : ''}
            </p>
          </div>

          {/* Search bar (takes remaining space) */}
          <div className="flex-1 max-w-xl">
            <SearchBar />
          </div>

          {/* Toolbar */}
          <div className="flex items-center gap-2 flex-shrink-0">
            <SelectionToggle isSelecting={isSelecting} onToggle={setIsSelecting} />
            <Tooltip content="Manage Tags" position="bottom">
              <Button
                variant={showTags ? 'primary' : 'ghost'}
                size="sm"
                onClick={() => setShowTags(!showTags)}
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                </svg>
              </Button>
            </Tooltip>
            <Tooltip content="Regenerate All Thumbnails" position="bottom">
              <Button
                variant="ghost"
                size="sm"
                onClick={handleRegenerateAllThumbnails}
                disabled={isRegeneratingThumbnails || assets.length === 0}
              >
                {isRegeneratingThumbnails ? (
                  <span className="flex items-center gap-1 text-xs">
                    <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    {thumbnailProgress.current}/{thumbnailProgress.total}
                  </span>
                ) : (
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                )}
              </Button>
            </Tooltip>
            <Tooltip content="Refresh" position="bottom">
              <Button variant="ghost" size="sm" onClick={fetchAssets}>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </Button>
            </Tooltip>
          </div>
        </div>
      </div>

      {/* Tag Manager (collapsible) */}
      {showTags && (
        <div className="flex-shrink-0 px-6 py-4 border-b border-border bg-surface-light">
          <div className="max-w-7xl mx-auto">
            <TagManager />
          </div>
        </div>
      )}

      {/* Main content */}
      <div className="flex-1 overflow-y-auto px-6 py-6">
        <div className="max-w-7xl mx-auto">
          {error ? (
            <div className="flex flex-col items-center justify-center py-20 text-center">
              <svg className="w-16 h-16 text-error mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <p className="text-text-secondary mb-2">{error}</p>
              <Button variant="secondary" onClick={fetchAssets}>Try Again</Button>
            </div>
          ) : (
            <AssetGrid
              assets={assets}
              viewMode={viewMode}
              isLoading={isLoading}
              showCheckboxes={isSelecting}
              selectedIds={selectedAssetIds}
              onSelect={handleAssetSelect}
              onAssetClick={handleAssetClick}
              emptyMessage={
                filters.search
                  ? 'No assets match your search'
                  : 'No assets yet. Generate your first 3D model!'
              }
            />
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex justify-center items-center gap-3 mt-8 pt-6 border-t border-border">
              <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>
                Previous
              </Button>
              <span className="text-sm text-text-secondary">
                Page {page} of {totalPages}
              </span>
              <Button variant="secondary" size="sm" disabled={page >= totalPages} onClick={() => setPage(page + 1)}>
                Next
              </Button>
            </div>
          )}
        </div>
      </div>

      {/* Bulk Actions */}
      <BulkActions />
    </div>
  );
}
