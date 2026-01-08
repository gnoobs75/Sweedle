/**
 * AssetGrid Component - Grid and list views for assets
 */

import { useCallback } from 'react';
import { useLibraryStore } from '../../stores/libraryStore';
import { AssetCard, AssetListItem } from './AssetCard';
import { Spinner } from '../ui/Spinner';
import { Button } from '../ui/Button';
import { cn } from '../../lib/utils';
import type { Asset, ViewMode } from '../../types';

interface AssetGridProps {
  assets: Asset[];
  viewMode?: ViewMode;
  isLoading?: boolean;
  showCheckboxes?: boolean;
  selectedIds?: Set<string>;
  onSelect?: (id: string, selected: boolean) => void;
  onAssetClick?: (asset: Asset) => void;
  emptyMessage?: string;
  className?: string;
}

export function AssetGrid({
  assets,
  viewMode = 'grid',
  isLoading = false,
  showCheckboxes = false,
  selectedIds = new Set(),
  onSelect,
  onAssetClick,
  emptyMessage = 'No assets found',
  className,
}: AssetGridProps) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Spinner size="lg" variant="primary" />
      </div>
    );
  }

  if (assets.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <svg
          className="w-16 h-16 text-text-muted opacity-50 mb-4"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
          />
        </svg>
        <p className="text-text-secondary">{emptyMessage}</p>
        <p className="text-text-muted text-sm mt-1">
          Generate your first 3D model to see it here
        </p>
      </div>
    );
  }

  if (viewMode === 'list') {
    return (
      <div className={cn('space-y-1', className)}>
        {assets.map((asset) => (
          <AssetListItem
            key={asset.id}
            asset={asset}
            isSelected={selectedIds.has(asset.id)}
            onSelect={onSelect}
            onClick={onAssetClick}
            showCheckbox={showCheckboxes}
          />
        ))}
      </div>
    );
  }

  return (
    <div
      className={cn(
        'grid gap-3',
        'grid-cols-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4',
        className
      )}
    >
      {assets.map((asset) => (
        <AssetCard
          key={asset.id}
          asset={asset}
          isSelected={selectedIds.has(asset.id)}
          onSelect={onSelect}
          onClick={onAssetClick}
          showCheckbox={showCheckboxes}
        />
      ))}
    </div>
  );
}

/**
 * Asset grid with pagination
 */
interface PaginatedAssetGridProps extends AssetGridProps {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
}

export function PaginatedAssetGrid({
  page,
  pageSize,
  total,
  onPageChange,
  ...gridProps
}: PaginatedAssetGridProps) {
  const totalPages = Math.ceil(total / pageSize);
  const hasMore = page < totalPages;
  const hasPrev = page > 1;

  return (
    <div className="space-y-4">
      <AssetGrid {...gridProps} />

      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-4 border-t border-border">
          <p className="text-sm text-text-muted">
            Showing {(page - 1) * pageSize + 1}-{Math.min(page * pageSize, total)} of {total}
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              disabled={!hasPrev}
              onClick={() => onPageChange(page - 1)}
            >
              <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              Previous
            </Button>
            <span className="text-sm text-text-secondary px-2">
              Page {page} of {totalPages}
            </span>
            <Button
              variant="secondary"
              size="sm"
              disabled={!hasMore}
              onClick={() => onPageChange(page + 1)}
            >
              Next
              <svg className="w-4 h-4 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Infinite scroll asset grid
 */
interface InfiniteAssetGridProps extends AssetGridProps {
  hasMore: boolean;
  onLoadMore: () => void;
  isLoadingMore?: boolean;
}

export function InfiniteAssetGrid({
  hasMore,
  onLoadMore,
  isLoadingMore = false,
  ...gridProps
}: InfiniteAssetGridProps) {
  return (
    <div className="space-y-4">
      <AssetGrid {...gridProps} />

      {hasMore && (
        <div className="flex justify-center pt-4">
          <Button
            variant="secondary"
            onClick={onLoadMore}
            isLoading={isLoadingMore}
          >
            {isLoadingMore ? 'Loading...' : 'Load More'}
          </Button>
        </div>
      )}
    </div>
  );
}
