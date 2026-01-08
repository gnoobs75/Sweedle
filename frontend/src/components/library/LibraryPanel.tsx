/**
 * LibraryPanel Component - Complete asset library with search, filters, and grid
 */

import { useEffect, useCallback, useState } from 'react';
import { useLibraryStore } from '../../stores/libraryStore';
import { useUIStore } from '../../stores/uiStore';
import { listAssets, listTags } from '../../services/api/assets';
import { SearchBar } from './SearchBar';
import { AssetGrid } from './AssetGrid';
import { BulkActions, SelectionToggle } from './BulkActions';
import { TagManager } from './TagManager';
import { AssetDetails } from './AssetDetails';
import { Button } from '../ui/Button';
import { cn } from '../../lib/utils';
import type { Asset } from '../../types';

export function LibraryPanel() {
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
        sortBy: filters.sortBy,
        sortOrder: filters.sortOrder,
      });

      setAssets(response.assets);
      setTotalAssets(response.total);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load assets';
      setError(message);
      addNotification({
        type: 'error',
        title: 'Failed to Load Assets',
        message,
      });
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

  // Get selected asset for details
  const selectedAsset = currentAssetId
    ? assets.find((a) => a.id === currentAssetId)
    : undefined;

  const handleAssetClick = useCallback(
    (asset: Asset) => {
      if (isSelecting) {
        toggleAssetSelection(asset.id);
      } else {
        setCurrentAsset(asset.id);
      }
    },
    [isSelecting, toggleAssetSelection, setCurrentAsset]
  );

  const handleAssetSelect = useCallback(
    (id: string, selected: boolean) => {
      toggleAssetSelection(id);
    },
    [toggleAssetSelection]
  );

  const handleCloseDetails = useCallback(() => {
    setCurrentAsset(null);
  }, [setCurrentAsset]);

  return (
    <div className="h-full flex">
      {/* Main Content */}
      <div className={cn('flex-1 flex flex-col min-w-0', selectedAsset && 'hidden lg:flex')}>
        {/* Header */}
        <div className="p-4 border-b border-border">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-lg font-semibold text-text-primary">Library</h2>
              <p className="text-sm text-text-muted">
                {totalAssets} asset{totalAssets !== 1 ? 's' : ''}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <SelectionToggle
                isSelecting={isSelecting}
                onToggle={setIsSelecting}
              />
              <Button
                variant={showTags ? 'primary' : 'ghost'}
                size="sm"
                onClick={() => setShowTags(!showTags)}
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                </svg>
              </Button>
              <Button variant="ghost" size="sm" onClick={fetchAssets}>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </Button>
            </div>
          </div>

          {/* Search Bar */}
          <SearchBar />
        </div>

        {/* Tag Manager (collapsible) */}
        {showTags && (
          <div className="p-4 border-b border-border bg-surface-light animate-fadeIn">
            <TagManager />
          </div>
        )}

        {/* Asset Grid */}
        <div className="flex-1 overflow-y-auto p-4">
          {error ? (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <svg
                className="w-16 h-16 text-error mb-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
              <p className="text-text-secondary mb-2">{error}</p>
              <Button variant="secondary" onClick={fetchAssets}>
                Try Again
              </Button>
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
          {totalAssets > pageSize && (
            <div className="flex justify-center gap-2 mt-4 pt-4 border-t border-border">
              <Button
                variant="secondary"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
              >
                Previous
              </Button>
              <span className="px-3 py-1.5 text-sm text-text-secondary">
                Page {page} of {Math.ceil(totalAssets / pageSize)}
              </span>
              <Button
                variant="secondary"
                size="sm"
                disabled={page >= Math.ceil(totalAssets / pageSize)}
                onClick={() => setPage(page + 1)}
              >
                Next
              </Button>
            </div>
          )}
        </div>
      </div>

      {/* Asset Details Sidebar */}
      {selectedAsset && (
        <div className="w-full lg:w-80 border-l border-border bg-surface flex-shrink-0 animate-fadeIn">
          <AssetDetails asset={selectedAsset} onClose={handleCloseDetails} />
        </div>
      )}

      {/* Bulk Actions */}
      <BulkActions />
    </div>
  );
}
