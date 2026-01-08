/**
 * AssetCard Component - Asset thumbnail card
 */

import { useState, useCallback } from 'react';
import { useViewerStore } from '../../stores/viewerStore';
import { useLibraryStore } from '../../stores/libraryStore';
import { getAssetModelUrl, getAssetThumbnailUrl } from '../../services/api/assets';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import { Checkbox } from '../ui/Checkbox';
import { cn, formatNumber, formatRelativeTime } from '../../lib/utils';
import type { Asset } from '../../types';

interface AssetCardProps {
  asset: Asset;
  isSelected?: boolean;
  onSelect?: (id: string, selected: boolean) => void;
  onClick?: (asset: Asset) => void;
  showCheckbox?: boolean;
  className?: string;
}

export function AssetCard({
  asset,
  isSelected = false,
  onSelect,
  onClick,
  showCheckbox = false,
  className,
}: AssetCardProps) {
  const [imageError, setImageError] = useState(false);
  const [isHovered, setIsHovered] = useState(false);
  const { loadModel } = useViewerStore();
  const { setCurrentAsset } = useLibraryStore();

  const thumbnailUrl = asset.thumbnailPath || getAssetThumbnailUrl(asset.id);

  const handleClick = useCallback(() => {
    if (onClick) {
      onClick(asset);
    } else {
      setCurrentAsset(asset.id);
      loadModel(getAssetModelUrl(asset.id), asset.id);
    }
  }, [asset, onClick, setCurrentAsset, loadModel]);

  const handleCheckboxChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      e.stopPropagation();
      onSelect?.(asset.id, e.target.checked);
    },
    [asset.id, onSelect]
  );

  const handleFavoriteClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      // TODO: Implement favorite toggle API call
    },
    []
  );

  return (
    <div
      className={cn(
        'group relative rounded-xl overflow-hidden cursor-pointer transition-all',
        'bg-surface border border-border',
        'hover:border-primary/50 hover:shadow-lg hover:shadow-primary/10',
        isSelected && 'ring-2 ring-primary border-primary',
        className
      )}
      onClick={handleClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Thumbnail */}
      <div className="aspect-square bg-surface-light relative overflow-hidden">
        {!imageError ? (
          <img
            src={thumbnailUrl}
            alt={asset.name}
            className="w-full h-full object-cover transition-transform group-hover:scale-105"
            onError={() => setImageError(true)}
            loading="lazy"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <svg
              className="w-12 h-12 text-text-muted"
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

        {/* Checkbox overlay */}
        {(showCheckbox || isSelected) && (
          <div
            className={cn(
              'absolute top-2 left-2 transition-opacity',
              !isHovered && !isSelected && 'opacity-0 group-hover:opacity-100'
            )}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="w-6 h-6 bg-surface/80 backdrop-blur-sm rounded flex items-center justify-center">
              <input
                type="checkbox"
                checked={isSelected}
                onChange={handleCheckboxChange}
                className="w-4 h-4 rounded border-2 border-border bg-surface-light checked:bg-primary checked:border-primary cursor-pointer"
              />
            </div>
          </div>
        )}

        {/* Favorite button */}
        <button
          className={cn(
            'absolute top-2 right-2 p-1.5 rounded-lg transition-all',
            'bg-surface/80 backdrop-blur-sm',
            asset.isFavorite
              ? 'text-warning'
              : 'text-text-muted opacity-0 group-hover:opacity-100 hover:text-warning'
          )}
          onClick={handleFavoriteClick}
        >
          <svg
            className="w-4 h-4"
            fill={asset.isFavorite ? 'currentColor' : 'none'}
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"
            />
          </svg>
        </button>

        {/* Status badges */}
        <div className="absolute bottom-2 left-2 flex gap-1">
          {asset.hasLod && (
            <Badge variant="info" size="sm">
              LOD
            </Badge>
          )}
          {asset.status === 'pending' && (
            <Badge variant="warning" size="sm">
              Processing
            </Badge>
          )}
        </div>

        {/* Quick actions on hover */}
        <div
          className={cn(
            'absolute bottom-2 right-2 flex gap-1 transition-opacity',
            'opacity-0 group-hover:opacity-100'
          )}
        >
          <Button
            variant="secondary"
            size="sm"
            className="h-7 px-2 bg-surface/90 backdrop-blur-sm"
            onClick={(e) => {
              e.stopPropagation();
              loadModel(getAssetModelUrl(asset.id), asset.id);
            }}
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
            </svg>
          </Button>
        </div>
      </div>

      {/* Info */}
      <div className="p-3">
        <h3 className="text-sm font-medium text-text-primary truncate">
          {asset.name}
        </h3>
        <div className="flex items-center justify-between mt-1">
          <span className="text-xs text-text-muted">
            {asset.faceCount ? `${formatNumber(asset.faceCount)} faces` : '--'}
          </span>
          <span className="text-xs text-text-muted">
            {formatRelativeTime(asset.createdAt)}
          </span>
        </div>
        {/* Tags */}
        {asset.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {asset.tags.slice(0, 3).map((tag) => (
              <Badge
                key={tag.id}
                variant="default"
                size="sm"
                style={{ backgroundColor: `${tag.color}20`, color: tag.color }}
              >
                {tag.name}
              </Badge>
            ))}
            {asset.tags.length > 3 && (
              <Badge variant="default" size="sm">
                +{asset.tags.length - 3}
              </Badge>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Compact list item variant
 */
export function AssetListItem({
  asset,
  isSelected = false,
  onSelect,
  onClick,
  showCheckbox = false,
  className,
}: AssetCardProps) {
  const [imageError, setImageError] = useState(false);
  const { loadModel } = useViewerStore();
  const { setCurrentAsset } = useLibraryStore();

  const thumbnailUrl = asset.thumbnailPath || getAssetThumbnailUrl(asset.id);

  const handleClick = useCallback(() => {
    if (onClick) {
      onClick(asset);
    } else {
      setCurrentAsset(asset.id);
      loadModel(getAssetModelUrl(asset.id), asset.id);
    }
  }, [asset, onClick, setCurrentAsset, loadModel]);

  return (
    <div
      className={cn(
        'group flex items-center gap-3 p-2 rounded-lg cursor-pointer transition-all',
        'hover:bg-surface-light',
        isSelected && 'bg-primary/10 ring-1 ring-primary',
        className
      )}
      onClick={handleClick}
    >
      {/* Checkbox */}
      {showCheckbox && (
        <div onClick={(e) => e.stopPropagation()}>
          <input
            type="checkbox"
            checked={isSelected}
            onChange={(e) => onSelect?.(asset.id, e.target.checked)}
            className="w-4 h-4 rounded border-2 border-border bg-surface-light checked:bg-primary checked:border-primary cursor-pointer"
          />
        </div>
      )}

      {/* Thumbnail */}
      <div className="w-12 h-12 rounded-lg bg-surface-light overflow-hidden flex-shrink-0">
        {!imageError ? (
          <img
            src={thumbnailUrl}
            alt={asset.name}
            className="w-full h-full object-cover"
            onError={() => setImageError(true)}
            loading="lazy"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <svg
              className="w-6 h-6 text-text-muted"
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

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-medium text-text-primary truncate">
            {asset.name}
          </h3>
          {asset.isFavorite && (
            <svg className="w-3.5 h-3.5 text-warning flex-shrink-0" fill="currentColor" viewBox="0 0 24 24">
              <path d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
            </svg>
          )}
        </div>
        <div className="flex items-center gap-3 mt-0.5 text-xs text-text-muted">
          <span>{asset.faceCount ? `${formatNumber(asset.faceCount)} faces` : '--'}</span>
          <span>{formatRelativeTime(asset.createdAt)}</span>
          {asset.hasLod && <Badge variant="info" size="sm">LOD</Badge>}
        </div>
      </div>

      {/* Tags */}
      <div className="hidden sm:flex items-center gap-1 flex-shrink-0">
        {asset.tags.slice(0, 2).map((tag) => (
          <Badge
            key={tag.id}
            variant="default"
            size="sm"
            style={{ backgroundColor: `${tag.color}20`, color: tag.color }}
          >
            {tag.name}
          </Badge>
        ))}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <Button
          variant="ghost"
          size="sm"
          onClick={(e) => {
            e.stopPropagation();
            loadModel(getAssetModelUrl(asset.id), asset.id);
          }}
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
          </svg>
        </Button>
      </div>
    </div>
  );
}
