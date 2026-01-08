/**
 * BulkActions Component - Multi-select actions bar
 */

import { useState, useCallback } from 'react';
import { useLibraryStore } from '../../stores/libraryStore';
import { useUIStore } from '../../stores/uiStore';
import { bulkDeleteAssets } from '../../services/api/assets';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { cn } from '../../lib/utils';

interface BulkActionsProps {
  className?: string;
}

export function BulkActions({ className }: BulkActionsProps) {
  const {
    selectedAssetIds,
    assets,
    selectAll,
    clearSelection,
    removeAsset,
  } = useLibraryStore();
  const { addNotification, openModal } = useUIStore();

  const [isDeleting, setIsDeleting] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  const selectedCount = selectedAssetIds.size;
  const allSelected = selectedCount === assets.length && assets.length > 0;

  const handleSelectAll = useCallback(() => {
    if (allSelected) {
      clearSelection();
    } else {
      selectAll();
    }
  }, [allSelected, selectAll, clearSelection]);

  const handleDelete = useCallback(async () => {
    if (selectedCount === 0) return;

    const confirmed = window.confirm(
      `Are you sure you want to delete ${selectedCount} asset${selectedCount > 1 ? 's' : ''}? This action cannot be undone.`
    );

    if (!confirmed) return;

    setIsDeleting(true);
    try {
      const ids = Array.from(selectedAssetIds);
      await bulkDeleteAssets(ids);

      // Remove from local state
      ids.forEach((id) => removeAsset(id));
      clearSelection();

      addNotification({
        type: 'success',
        title: 'Assets Deleted',
        message: `${selectedCount} asset${selectedCount > 1 ? 's' : ''} deleted successfully`,
      });
    } catch (error) {
      addNotification({
        type: 'error',
        title: 'Delete Failed',
        message: error instanceof Error ? error.message : 'Failed to delete assets',
      });
    } finally {
      setIsDeleting(false);
    }
  }, [selectedAssetIds, selectedCount, removeAsset, clearSelection, addNotification]);

  const handleExport = useCallback(() => {
    openModal('bulk-export', {
      assetIds: Array.from(selectedAssetIds),
    });
  }, [selectedAssetIds, openModal]);

  const handleAddTags = useCallback(() => {
    openModal('bulk-tags', {
      assetIds: Array.from(selectedAssetIds),
    });
  }, [selectedAssetIds, openModal]);

  if (selectedCount === 0) {
    return null;
  }

  return (
    <div
      className={cn(
        'fixed bottom-4 left-1/2 -translate-x-1/2 z-50',
        'bg-surface border border-border rounded-xl shadow-2xl',
        'px-4 py-3 flex items-center gap-4',
        'animate-slideIn',
        className
      )}
    >
      {/* Selection Info */}
      <div className="flex items-center gap-2">
        <Badge variant="primary">
          {selectedCount} selected
        </Badge>
        <button
          onClick={handleSelectAll}
          className="text-sm text-primary hover:underline"
        >
          {allSelected ? 'Deselect all' : 'Select all'}
        </button>
      </div>

      <div className="w-px h-6 bg-border" />

      {/* Actions */}
      <div className="flex items-center gap-2">
        <Button
          variant="secondary"
          size="sm"
          onClick={handleAddTags}
        >
          <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
          </svg>
          Add Tags
        </Button>

        <Button
          variant="secondary"
          size="sm"
          onClick={handleExport}
          isLoading={isExporting}
        >
          <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
          </svg>
          Export
        </Button>

        <Button
          variant="danger"
          size="sm"
          onClick={handleDelete}
          isLoading={isDeleting}
        >
          <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
          </svg>
          Delete
        </Button>
      </div>

      {/* Close Button */}
      <button
        onClick={clearSelection}
        className="p-1 text-text-muted hover:text-text-primary transition-colors"
        title="Clear selection"
      >
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  );
}

/**
 * Selection mode toggle for mobile
 */
interface SelectionToggleProps {
  isSelecting: boolean;
  onToggle: (selecting: boolean) => void;
  className?: string;
}

export function SelectionToggle({
  isSelecting,
  onToggle,
  className,
}: SelectionToggleProps) {
  return (
    <Button
      variant={isSelecting ? 'primary' : 'ghost'}
      size="sm"
      onClick={() => onToggle(!isSelecting)}
      className={className}
    >
      <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
        />
      </svg>
      {isSelecting ? 'Done' : 'Select'}
    </Button>
  );
}
