/**
 * Assets API Service
 */

import { apiClient } from './client';
import type { Asset, Tag, AssetListResponse } from '../../types';

// Detect if running in Tauri (check at runtime, not module load)
// Tauri v2 uses __TAURI_INTERNALS__, v1 used __TAURI__
function isTauri(): boolean {
  return typeof window !== 'undefined' &&
    ('__TAURI_INTERNALS__' in window || '__TAURI__' in window);
}

// Storage base URL - in Tauri, use localhost directly
export function getStorageBase(): string {
  return isTauri() ? 'http://localhost:8001' : '';
}

interface ListAssetsParams {
  page?: number;
  pageSize?: number;
  search?: string;
  tags?: number[];
  sourceType?: 'all' | 'image_to_3d' | 'text_to_3d';
  hasLod?: boolean;
  isFavorite?: boolean;
  folderId?: number;
  sortBy?: 'created' | 'name' | 'size' | 'rating';
  sortOrder?: 'asc' | 'desc';
}

interface UpdateAssetParams {
  name?: string;
  description?: string;
  isFavorite?: boolean;
  rating?: number;
  tags?: number[];
}

// Transform snake_case rigging data from backend to camelCase SkeletonData
function transformRiggingData(raw: Record<string, unknown> | undefined): Record<string, unknown> | undefined {
  if (!raw || !Array.isArray(raw.bones)) return raw;

  return {
    rootBone: raw.root_bone ?? raw.rootBone,
    bones: (raw.bones as Array<Record<string, unknown>>).map((b) => ({
      name: b.name,
      parent: b.parent,
      headPosition: b.head_position ?? b.headPosition ?? [0, 0, 0],
      tailPosition: b.tail_position ?? b.tailPosition ?? [0, 0, 0],
      rotation: b.rotation || [0, 0, 0, 1],
      scale: b.scale || [1, 1, 1],
      connected: b.connected ?? false,
      deform: b.deform ?? true,
    })),
    characterType: raw.character_type ?? raw.characterType,
    boneCount: raw.bone_count ?? raw.boneCount,
  };
}

// Transform API response to frontend Asset type
function transformAsset(data: Record<string, unknown>): Asset {
  return {
    id: data.id as string,
    name: data.name as string,
    description: data.description as string | undefined,
    sourceType: data.source_type as Asset['sourceType'],
    sourceImagePath: data.source_image_path as string | undefined,
    sourcePrompt: data.source_prompt as string | undefined,
    generationParams: data.generation_params as Asset['generationParams'],
    filePath: data.file_path as string,
    thumbnailPath: data.thumbnail_path as string | undefined,
    vertexCount: data.vertex_count as number | undefined,
    faceCount: data.face_count as number | undefined,
    fileSizeBytes: data.file_size_bytes as number | undefined,
    generationTimeSeconds: data.generation_time_seconds as number | undefined,
    status: data.status as string,
    hasLod: data.has_lod as boolean,
    hasTexture: data.has_texture as boolean,
    isRigged: data.is_rigged as boolean | undefined,
    characterType: data.character_type as string | undefined,
    hasAnimations: data.has_animations as boolean | undefined,
    animationCount: data.animation_count as number | undefined,
    riggingData: transformRiggingData(data.rigging_data as Record<string, unknown> | undefined),
    lodLevels: data.lod_levels as number[] | undefined,
    isFavorite: data.is_favorite as boolean,
    rating: data.rating as number | undefined,
    tags: ((data.tags as Array<{ id: number; name: string; color: string }>) || []).map(
      (t) => ({
        id: t.id,
        name: t.name,
        color: t.color,
      })
    ),
    createdAt: data.created_at as string,
    updatedAt: data.updated_at as string,
    folderId: data.folder_id as number | undefined,
  };
}

/**
 * List assets with filters
 */
export async function listAssets(
  params: ListAssetsParams = {}
): Promise<AssetListResponse> {
  const queryParams = new URLSearchParams();

  if (params.page) queryParams.set('page', String(params.page));
  if (params.pageSize) queryParams.set('page_size', String(params.pageSize));
  if (params.search) queryParams.set('search', params.search);
  if (params.tags?.length) queryParams.set('tags', params.tags.join(','));
  if (params.sourceType && params.sourceType !== 'all') {
    queryParams.set('source_type', params.sourceType);
  }
  if (params.hasLod !== undefined) queryParams.set('has_lod', String(params.hasLod));
  if (params.isFavorite !== undefined) {
    queryParams.set('is_favorite', String(params.isFavorite));
  }
  if (params.folderId !== undefined) {
    queryParams.set('folder_id', String(params.folderId));
  }
  if (params.sortBy) queryParams.set('sort_by', params.sortBy);
  if (params.sortOrder) queryParams.set('sort_order', params.sortOrder);

  const query = queryParams.toString();
  const endpoint = `/assets${query ? `?${query}` : ''}`;

  const response = await apiClient.get<{
    assets: Array<Record<string, unknown>>;
    total: number;
    page: number;
    page_size: number;
  }>(endpoint);

  return {
    assets: response.assets.map(transformAsset),
    total: response.total,
    page: response.page,
    pageSize: response.page_size,
  };
}

/**
 * Get a single asset by ID
 */
export async function getAsset(assetId: string): Promise<Asset> {
  const response = await apiClient.get<Record<string, unknown>>(
    `/assets/${assetId}`
  );
  return transformAsset(response);
}

/**
 * Update an asset
 */
export async function updateAsset(
  assetId: string,
  updates: UpdateAssetParams
): Promise<Asset> {
  const body: Record<string, unknown> = {};
  if (updates.name !== undefined) body.name = updates.name;
  if (updates.description !== undefined) body.description = updates.description;
  if (updates.isFavorite !== undefined) body.is_favorite = updates.isFavorite;
  if (updates.rating !== undefined) body.rating = updates.rating;
  if (updates.tags !== undefined) body.tags = updates.tags;

  const response = await apiClient.patch<Record<string, unknown>>(
    `/assets/${assetId}`,
    body
  );
  return transformAsset(response);
}

/**
 * Delete an asset
 */
export async function deleteAsset(assetId: string): Promise<void> {
  await apiClient.delete(`/assets/${assetId}`);
}

/**
 * Bulk delete assets
 */
export async function bulkDeleteAssets(assetIds: string[]): Promise<void> {
  await apiClient.post('/assets/bulk-delete', { asset_ids: assetIds });
}

/**
 * Download an asset file
 */
export function getAssetDownloadUrl(assetId: string): string {
  return `${getStorageBase()}/api/assets/${assetId}/download`;
}

/**
 * Get asset thumbnail URL
 */
export function getAssetThumbnailUrl(assetId: string): string {
  return `${getStorageBase()}/storage/generated/${assetId}/thumbnail.png`;
}

/**
 * Get asset model URL
 */
export function getAssetModelUrl(assetId: string, format = 'glb'): string {
  return `${getStorageBase()}/storage/generated/${assetId}/${assetId}.${format}`;
}

// Tag APIs

/**
 * List all tags
 */
export async function listTags(): Promise<Tag[]> {
  const response = await apiClient.get<{
    tags: Array<{ id: number; name: string; color: string }>;
  }>('/assets/tags');

  return response.tags.map((t) => ({
    id: t.id,
    name: t.name,
    color: t.color,
  }));
}

/**
 * Create a new tag
 */
export async function createTag(name: string, color?: string): Promise<Tag> {
  const response = await apiClient.post<{ id: number; name: string; color: string }>(
    '/assets/tags',
    { name, color }
  );

  return {
    id: response.id,
    name: response.name,
    color: response.color,
  };
}

/**
 * Delete a tag
 */
export async function deleteTag(tagId: number): Promise<void> {
  await apiClient.delete(`/assets/tags/${tagId}`);
}

/**
 * Add tag to asset
 */
export async function addTagToAsset(assetId: string, tagId: number): Promise<void> {
  await apiClient.post(`/assets/${assetId}/tags/${tagId}`);
}

/**
 * Remove tag from asset
 */
export async function removeTagFromAsset(
  assetId: string,
  tagId: number
): Promise<void> {
  await apiClient.delete(`/assets/${assetId}/tags/${tagId}`);
}

/**
 * Import an existing 3D model
 */
export interface ImportModelResult {
  success: boolean;
  assetId: string;
  name: string;
  filePath: string;
  vertexCount: number;
  faceCount: number;
  hasTexture: boolean;
  message: string;
  error?: string;
}

export async function importModel(
  file: File,
  name?: string
): Promise<ImportModelResult> {
  const formData = new FormData();
  formData.append('file', file);
  if (name) {
    formData.append('name', name);
  }

  const response = await apiClient.post<{
    success: boolean;
    asset_id: string;
    name: string;
    file_path: string;
    vertex_count: number;
    face_count: number;
    has_texture: boolean;
    message: string;
    error?: string;
  }>('/assets/import', formData);

  return {
    success: response.success,
    assetId: response.asset_id,
    name: response.name,
    filePath: response.file_path,
    vertexCount: response.vertex_count,
    faceCount: response.face_count,
    hasTexture: response.has_texture,
    message: response.message,
    error: response.error,
  };
}
