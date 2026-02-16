/**
 * Variants API Service - Asset variants and version history
 */

import { apiClient } from './client';

// ============ Types ============

export interface VariantGroup {
  id: string;
  name: string;
  description?: string;
  sourceType: string;
  sourceImagePath?: string;
  sourcePrompt?: string;
  primaryAssetId?: string;
  variantCount: number;
  createdAt: string;
}

export interface VariantAssetInfo {
  id: string;
  name: string;
  thumbnailPath?: string;
  generationSeed?: number;
  variantIndex?: number;
  vertexCount?: number;
  faceCount?: number;
  isPrimary: boolean;
  createdAt: string;
}

export interface VariantGroupDetail {
  id: string;
  name: string;
  description?: string;
  sourceType: string;
  sourceImagePath?: string;
  sourcePrompt?: string;
  primaryAssetId?: string;
  variants: VariantAssetInfo[];
  createdAt: string;
  updatedAt: string;
}

export interface AssetVersion {
  id: string;
  assetId: string;
  versionNumber: number;
  changeType: string;
  changeDescription?: string;
  filePath: string;
  thumbnailPath?: string;
  vertexCount?: number;
  faceCount?: number;
  fileSizeBytes?: number;
  createdAt: string;
}

export interface VersionHistory {
  assetId: string;
  assetName: string;
  currentVersion: number;
  versions: AssetVersion[];
}

// ============ Variant Groups ============

/**
 * List all variant groups
 */
export async function listVariantGroups(limit = 50, offset = 0): Promise<VariantGroup[]> {
  const response = await apiClient.get<Array<{
    id: string;
    name: string;
    description?: string;
    source_type: string;
    source_image_path?: string;
    source_prompt?: string;
    primary_asset_id?: string;
    variant_count: number;
    created_at: string;
  }>>(`/variants/groups?limit=${limit}&offset=${offset}`);

  return response.map(g => ({
    id: g.id,
    name: g.name,
    description: g.description,
    sourceType: g.source_type,
    sourceImagePath: g.source_image_path,
    sourcePrompt: g.source_prompt,
    primaryAssetId: g.primary_asset_id,
    variantCount: g.variant_count,
    createdAt: g.created_at,
  }));
}

/**
 * Get detailed variant group with all variants
 */
export async function getVariantGroup(groupId: string): Promise<VariantGroupDetail> {
  const response = await apiClient.get<{
    id: string;
    name: string;
    description?: string;
    source_type: string;
    source_image_path?: string;
    source_prompt?: string;
    primary_asset_id?: string;
    variants: Array<{
      id: string;
      name: string;
      thumbnail_path?: string;
      generation_seed?: number;
      variant_index?: number;
      vertex_count?: number;
      face_count?: number;
      is_primary: boolean;
      created_at: string;
    }>;
    created_at: string;
    updated_at: string;
  }>(`/variants/groups/${groupId}`);

  return {
    id: response.id,
    name: response.name,
    description: response.description,
    sourceType: response.source_type,
    sourceImagePath: response.source_image_path,
    sourcePrompt: response.source_prompt,
    primaryAssetId: response.primary_asset_id,
    variants: response.variants.map(v => ({
      id: v.id,
      name: v.name,
      thumbnailPath: v.thumbnail_path,
      generationSeed: v.generation_seed,
      variantIndex: v.variant_index,
      vertexCount: v.vertex_count,
      faceCount: v.face_count,
      isPrimary: v.is_primary,
      createdAt: v.created_at,
    })),
    createdAt: response.created_at,
    updatedAt: response.updated_at,
  };
}

/**
 * Generate multiple variants from an asset
 */
export async function generateVariants(
  assetId: string,
  count = 4,
  namePrefix?: string
): Promise<{
  success: boolean;
  variantGroupId: string;
  jobIds: string[];
  message: string;
  error?: string;
}> {
  const response = await apiClient.post<{
    success: boolean;
    variant_group_id: string;
    job_ids: string[];
    message: string;
    error?: string;
  }>('/variants/generate', {
    asset_id: assetId,
    count,
    name_prefix: namePrefix,
  });

  return {
    success: response.success,
    variantGroupId: response.variant_group_id,
    jobIds: response.job_ids,
    message: response.message,
    error: response.error,
  };
}

/**
 * Set the primary variant in a group
 */
export async function setPrimaryVariant(
  groupId: string,
  assetId: string
): Promise<{ success: boolean; message: string }> {
  return apiClient.post(`/variants/groups/${groupId}/set-primary`, {
    variant_group_id: groupId,
    asset_id: assetId,
  });
}

/**
 * Delete a variant group
 */
export async function deleteVariantGroup(
  groupId: string,
  deleteAssets = false
): Promise<{ success: boolean; message: string }> {
  return apiClient.delete(`/variants/groups/${groupId}?delete_assets=${deleteAssets}`);
}

// ============ Version History ============

/**
 * Get version history for an asset
 */
export async function getVersionHistory(assetId: string): Promise<VersionHistory> {
  const response = await apiClient.get<{
    asset_id: string;
    asset_name: string;
    current_version: number;
    versions: Array<{
      id: string;
      asset_id: string;
      version_number: number;
      change_type: string;
      change_description?: string;
      file_path: string;
      thumbnail_path?: string;
      vertex_count?: number;
      face_count?: number;
      file_size_bytes?: number;
      created_at: string;
    }>;
  }>(`/variants/assets/${assetId}/versions`);

  return {
    assetId: response.asset_id,
    assetName: response.asset_name,
    currentVersion: response.current_version,
    versions: response.versions.map(v => ({
      id: v.id,
      assetId: v.asset_id,
      versionNumber: v.version_number,
      changeType: v.change_type,
      changeDescription: v.change_description,
      filePath: v.file_path,
      thumbnailPath: v.thumbnail_path,
      vertexCount: v.vertex_count,
      faceCount: v.face_count,
      fileSizeBytes: v.file_size_bytes,
      createdAt: v.created_at,
    })),
  };
}

/**
 * Create a version snapshot
 */
export async function createVersion(
  assetId: string,
  changeType: 'mesh_edit' | 'texture_change' | 'rigging' | 'animation' | 'manual',
  changeDescription?: string
): Promise<{
  success: boolean;
  versionId: string;
  versionNumber: number;
  message: string;
  error?: string;
}> {
  const response = await apiClient.post<{
    success: boolean;
    version_id: string;
    version_number: number;
    message: string;
    error?: string;
  }>('/variants/versions/create', {
    asset_id: assetId,
    change_type: changeType,
    change_description: changeDescription,
  });

  return {
    success: response.success,
    versionId: response.version_id,
    versionNumber: response.version_number,
    message: response.message,
    error: response.error,
  };
}

/**
 * Restore an asset to a previous version
 */
export async function restoreVersion(
  versionId: string,
  createBackup = true
): Promise<{
  success: boolean;
  restoredVersion: number;
  backupVersionId?: string;
  message: string;
  error?: string;
}> {
  const response = await apiClient.post<{
    success: boolean;
    restored_version: number;
    backup_version_id?: string;
    message: string;
    error?: string;
  }>('/variants/versions/restore', {
    version_id: versionId,
    create_backup: createBackup,
  });

  return {
    success: response.success,
    restoredVersion: response.restored_version,
    backupVersionId: response.backup_version_id,
    message: response.message,
    error: response.error,
  };
}

/**
 * Delete a specific version
 */
export async function deleteVersion(
  versionId: string
): Promise<{ success: boolean; message: string }> {
  return apiClient.delete(`/variants/versions/${versionId}`);
}
