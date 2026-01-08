/**
 * Library Store - Manages asset library state
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Asset, Tag, ViewMode } from '../types';

interface LibraryFilters {
  search: string;
  tags: number[];
  sourceType: 'all' | 'image_to_3d' | 'text_to_3d';
  hasLod: boolean | null;
  isFavorite: boolean | null;
  sortBy: 'created' | 'name' | 'size' | 'rating';
  sortOrder: 'asc' | 'desc';
}

interface LibraryState {
  // Assets
  assets: Asset[];
  selectedAssetIds: Set<string>;
  currentAssetId: string | null;

  // Tags
  tags: Tag[];

  // Filters
  filters: LibraryFilters;

  // Pagination
  page: number;
  pageSize: number;
  totalAssets: number;

  // UI state
  viewMode: ViewMode;
  isLoading: boolean;
  error: string | null;

  // Actions
  setAssets: (assets: Asset[]) => void;
  addAsset: (asset: Asset) => void;
  updateAsset: (id: string, updates: Partial<Asset>) => void;
  removeAsset: (id: string) => void;
  selectAsset: (id: string) => void;
  deselectAsset: (id: string) => void;
  toggleAssetSelection: (id: string) => void;
  selectAll: () => void;
  clearSelection: () => void;
  setCurrentAsset: (id: string | null) => void;

  // Tags
  setTags: (tags: Tag[]) => void;
  addTag: (tag: Tag) => void;
  removeTag: (id: number) => void;

  // Filters
  setFilter: <K extends keyof LibraryFilters>(key: K, value: LibraryFilters[K]) => void;
  setFilters: (filters: Partial<LibraryFilters>) => void;
  resetFilters: () => void;

  // Pagination
  setPage: (page: number) => void;
  setPageSize: (size: number) => void;
  setTotalAssets: (total: number) => void;

  // UI
  setViewMode: (mode: ViewMode) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

const defaultFilters: LibraryFilters = {
  search: '',
  tags: [],
  sourceType: 'all',
  hasLod: null,
  isFavorite: null,
  sortBy: 'created',
  sortOrder: 'desc',
};

export const useLibraryStore = create<LibraryState>()(
  persist(
    (set, get) => ({
      // Initial state
      assets: [],
      selectedAssetIds: new Set(),
      currentAssetId: null,
      tags: [],
      filters: { ...defaultFilters },
      page: 1,
      pageSize: 20,
      totalAssets: 0,
      viewMode: 'grid',
      isLoading: false,
      error: null,

      // Asset actions
      setAssets: (assets) => set({ assets, error: null }),

      addAsset: (asset) =>
        set((state) => ({
          assets: [asset, ...state.assets],
          totalAssets: state.totalAssets + 1,
        })),

      updateAsset: (id, updates) =>
        set((state) => ({
          assets: state.assets.map((a) =>
            a.id === id ? { ...a, ...updates } : a
          ),
        })),

      removeAsset: (id) =>
        set((state) => {
          const newSelectedIds = new Set(state.selectedAssetIds);
          newSelectedIds.delete(id);
          return {
            assets: state.assets.filter((a) => a.id !== id),
            selectedAssetIds: newSelectedIds,
            currentAssetId: state.currentAssetId === id ? null : state.currentAssetId,
            totalAssets: state.totalAssets - 1,
          };
        }),

      selectAsset: (id) =>
        set((state) => {
          const newIds = new Set(state.selectedAssetIds);
          newIds.add(id);
          return { selectedAssetIds: newIds };
        }),

      deselectAsset: (id) =>
        set((state) => {
          const newIds = new Set(state.selectedAssetIds);
          newIds.delete(id);
          return { selectedAssetIds: newIds };
        }),

      toggleAssetSelection: (id) =>
        set((state) => {
          const newIds = new Set(state.selectedAssetIds);
          if (newIds.has(id)) {
            newIds.delete(id);
          } else {
            newIds.add(id);
          }
          return { selectedAssetIds: newIds };
        }),

      selectAll: () =>
        set((state) => ({
          selectedAssetIds: new Set(state.assets.map((a) => a.id)),
        })),

      clearSelection: () => set({ selectedAssetIds: new Set() }),

      setCurrentAsset: (id) => set({ currentAssetId: id }),

      // Tag actions
      setTags: (tags) => set({ tags }),

      addTag: (tag) =>
        set((state) => ({
          tags: [...state.tags, tag],
        })),

      removeTag: (id) =>
        set((state) => ({
          tags: state.tags.filter((t) => t.id !== id),
          filters: {
            ...state.filters,
            tags: state.filters.tags.filter((tid) => tid !== id),
          },
        })),

      // Filter actions
      setFilter: (key, value) =>
        set((state) => ({
          filters: { ...state.filters, [key]: value },
          page: 1, // Reset to first page on filter change
        })),

      setFilters: (filters) =>
        set((state) => ({
          filters: { ...state.filters, ...filters },
          page: 1,
        })),

      resetFilters: () => set({ filters: { ...defaultFilters }, page: 1 }),

      // Pagination actions
      setPage: (page) => set({ page }),

      setPageSize: (pageSize) => set({ pageSize, page: 1 }),

      setTotalAssets: (total) => set({ totalAssets: total }),

      // UI actions
      setViewMode: (viewMode) => set({ viewMode }),

      setLoading: (isLoading) => set({ isLoading }),

      setError: (error) => set({ error, isLoading: false }),
    }),
    {
      name: 'sweedle-library',
      partialize: (state) => ({
        viewMode: state.viewMode,
        pageSize: state.pageSize,
        filters: {
          sortBy: state.filters.sortBy,
          sortOrder: state.filters.sortOrder,
        },
      }),
    }
  )
);
