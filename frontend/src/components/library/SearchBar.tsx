/**
 * SearchBar Component - Search and filter controls
 */

import { useState, useCallback, useMemo } from 'react';
import { useLibraryStore } from '../../stores/libraryStore';
import { Input } from '../ui/Input';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { Select } from '../ui/Select';
import { cn, debounce } from '../../lib/utils';

interface SearchBarProps {
  className?: string;
}

export function SearchBar({ className }: SearchBarProps) {
  const {
    filters,
    setFilter,
    resetFilters,
    tags,
    viewMode,
    setViewMode,
  } = useLibraryStore();

  const [showFilters, setShowFilters] = useState(false);
  const [localSearch, setLocalSearch] = useState(filters.search);

  // Debounced search
  const debouncedSetSearch = useMemo(
    () => debounce((value: string) => setFilter('search', value), 300),
    [setFilter]
  );

  const handleSearchChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const value = e.target.value;
      setLocalSearch(value);
      debouncedSetSearch(value);
    },
    [debouncedSetSearch]
  );

  const handleClearSearch = useCallback(() => {
    setLocalSearch('');
    setFilter('search', '');
  }, [setFilter]);

  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (filters.tags?.length > 0) count++;
    if (filters.sourceType && filters.sourceType !== 'all') count++;
    if (filters.hasLod !== null && filters.hasLod !== undefined) count++;
    if (filters.isFavorite !== null && filters.isFavorite !== undefined) count++;
    return count;
  }, [filters]);

  return (
    <div className={cn('space-y-3', className)}>
      {/* Search Input Row */}
      <div className="flex items-center gap-2">
        <div className="flex-1 relative">
          <Input
            value={localSearch}
            onChange={handleSearchChange}
            placeholder="Search assets..."
            leftIcon={
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            }
            rightIcon={
              localSearch ? (
                <button
                  onClick={handleClearSearch}
                  className="p-1 hover:bg-surface-lighter rounded transition-colors"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              ) : undefined
            }
          />
        </div>

        {/* View Mode Toggle */}
        <div className="flex items-center bg-surface-light rounded-lg p-1">
          <Button
            variant={viewMode === 'grid' ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setViewMode('grid')}
            className="px-2"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
            </svg>
          </Button>
          <Button
            variant={viewMode === 'list' ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setViewMode('list')}
            className="px-2"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
            </svg>
          </Button>
        </div>

        {/* Filter Toggle */}
        <Button
          variant={showFilters ? 'primary' : 'secondary'}
          size="sm"
          onClick={() => setShowFilters(!showFilters)}
        >
          <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
          </svg>
          Filters
          {activeFilterCount > 0 && (
            <Badge variant="primary" size="sm" className="ml-1">
              {activeFilterCount}
            </Badge>
          )}
        </Button>
      </div>

      {/* Quick Filters */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1">
        <Badge
          variant={filters.sourceType === 'all' ? 'primary' : 'default'}
          className="cursor-pointer whitespace-nowrap"
          onClick={() => setFilter('sourceType', 'all')}
        >
          All
        </Badge>
        <Badge
          variant={filters.sourceType === 'image_to_3d' ? 'primary' : 'default'}
          className="cursor-pointer whitespace-nowrap"
          onClick={() => setFilter('sourceType', 'image_to_3d')}
        >
          Image to 3D
        </Badge>
        <Badge
          variant={filters.isFavorite === true ? 'primary' : 'default'}
          className="cursor-pointer whitespace-nowrap"
          onClick={() => setFilter('isFavorite', filters.isFavorite === true ? null : true)}
        >
          <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 24 24">
            <path d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
          </svg>
          Favorites
        </Badge>
        <Badge
          variant={filters.hasLod === true ? 'primary' : 'default'}
          className="cursor-pointer whitespace-nowrap"
          onClick={() => setFilter('hasLod', filters.hasLod === true ? null : true)}
        >
          Has LOD
        </Badge>
      </div>

      {/* Extended Filters */}
      {showFilters && (
        <div className="p-3 bg-surface-light rounded-lg space-y-3 animate-fadeIn">
          <div className="grid grid-cols-2 gap-3">
            <Select
              label="Sort By"
              value={filters.sortBy}
              onChange={(e) => setFilter('sortBy', e.target.value as any)}
              options={[
                { value: 'created', label: 'Date Created' },
                { value: 'name', label: 'Name' },
                { value: 'size', label: 'File Size' },
                { value: 'rating', label: 'Rating' },
              ]}
            />
            <Select
              label="Order"
              value={filters.sortOrder}
              onChange={(e) => setFilter('sortOrder', e.target.value as any)}
              options={[
                { value: 'desc', label: 'Descending' },
                { value: 'asc', label: 'Ascending' },
              ]}
            />
          </div>

          {/* Tag Filters */}
          {tags.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-2">
                Tags
              </label>
              <div className="flex flex-wrap gap-1">
                {tags.map((tag) => (
                  <Badge
                    key={tag.id}
                    variant={filters.tags?.includes(tag.id) ? 'primary' : 'default'}
                    className="cursor-pointer"
                    style={
                      filters.tags?.includes(tag.id)
                        ? { backgroundColor: tag.color, color: 'white' }
                        : { backgroundColor: `${tag.color}20`, color: tag.color }
                    }
                    onClick={() => {
                      const currentTags = filters.tags || [];
                      const newTags = currentTags.includes(tag.id)
                        ? currentTags.filter((t) => t !== tag.id)
                        : [...currentTags, tag.id];
                      setFilter('tags', newTags);
                    }}
                  >
                    {tag.name}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* Reset Filters */}
          {activeFilterCount > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={resetFilters}
              className="w-full"
            >
              <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Reset All Filters
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
