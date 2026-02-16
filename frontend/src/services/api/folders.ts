/**
 * Folders API Service
 */

import { apiClient } from './client';

export interface Folder {
  id: number;
  name: string;
  description?: string;
  color: string;
  icon: string;
  parentId?: number;
  assetCount: number;
  childCount: number;
  createdAt: string;
  updatedAt: string;
}

export interface FolderWithChildren extends Folder {
  children: FolderWithChildren[];
}

export interface FolderTree {
  folders: FolderWithChildren[];
  totalFolders: number;
  totalAssets: number;
}

export interface CreateFolderParams {
  name: string;
  description?: string;
  color?: string;
  icon?: string;
  parentId?: number;
}

export interface UpdateFolderParams {
  name?: string;
  description?: string;
  color?: string;
  icon?: string;
  parentId?: number;
}

export interface MoveAssetsParams {
  assetIds: string[];
  folderId?: number; // null means move to root
}

// Transform API response to frontend types
function transformFolder(data: Record<string, unknown>): Folder {
  return {
    id: data.id as number,
    name: data.name as string,
    description: data.description as string | undefined,
    color: data.color as string,
    icon: data.icon as string,
    parentId: data.parent_id as number | undefined,
    assetCount: data.asset_count as number,
    childCount: data.child_count as number,
    createdAt: data.created_at as string,
    updatedAt: data.updated_at as string,
  };
}

function transformFolderWithChildren(data: Record<string, unknown>): FolderWithChildren {
  return {
    ...transformFolder(data),
    children: ((data.children as Array<Record<string, unknown>>) || []).map(transformFolderWithChildren),
  };
}

/**
 * List folders (optionally by parent)
 */
export async function listFolders(parentId?: number): Promise<Folder[]> {
  const queryParams = new URLSearchParams();
  if (parentId !== undefined) {
    queryParams.set('parent_id', String(parentId));
  }
  queryParams.set('include_counts', 'true');

  const query = queryParams.toString();
  const endpoint = `/folders${query ? `?${query}` : ''}`;

  const response = await apiClient.get<{
    folders: Array<Record<string, unknown>>;
    total: number;
  }>(endpoint);

  return response.folders.map(transformFolder);
}

/**
 * Get complete folder tree structure
 */
export async function getFolderTree(): Promise<FolderTree> {
  const response = await apiClient.get<{
    folders: Array<Record<string, unknown>>;
    total_folders: number;
    total_assets: number;
  }>('/folders/tree');

  return {
    folders: response.folders.map(transformFolderWithChildren),
    totalFolders: response.total_folders,
    totalAssets: response.total_assets,
  };
}

/**
 * Get a specific folder
 */
export async function getFolder(folderId: number): Promise<Folder> {
  const response = await apiClient.get<Record<string, unknown>>(`/folders/${folderId}`);
  return transformFolder(response);
}

/**
 * Create a new folder
 */
export async function createFolder(params: CreateFolderParams): Promise<Folder> {
  const response = await apiClient.post<Record<string, unknown>>('/folders', {
    name: params.name,
    description: params.description,
    color: params.color || '#6366f1',
    icon: params.icon || 'folder',
    parent_id: params.parentId,
  });

  return transformFolder(response);
}

/**
 * Update a folder
 */
export async function updateFolder(folderId: number, params: UpdateFolderParams): Promise<Folder> {
  const body: Record<string, unknown> = {};
  if (params.name !== undefined) body.name = params.name;
  if (params.description !== undefined) body.description = params.description;
  if (params.color !== undefined) body.color = params.color;
  if (params.icon !== undefined) body.icon = params.icon;
  if (params.parentId !== undefined) body.parent_id = params.parentId;

  const response = await apiClient.patch<Record<string, unknown>>(`/folders/${folderId}`, body);
  return transformFolder(response);
}

/**
 * Delete a folder
 */
export async function deleteFolder(folderId: number, moveAssetsTo?: number): Promise<void> {
  const queryParams = new URLSearchParams();
  if (moveAssetsTo !== undefined) {
    queryParams.set('move_assets_to', String(moveAssetsTo));
  }

  const query = queryParams.toString();
  const endpoint = `/folders/${folderId}${query ? `?${query}` : ''}`;
  await apiClient.delete(endpoint);
}

/**
 * Move assets to a folder (or root)
 */
export async function moveAssets(params: MoveAssetsParams): Promise<{ movedCount: number; message: string }> {
  const response = await apiClient.post<{
    success: boolean;
    moved_count: number;
    message: string;
  }>('/folders/move-assets', {
    asset_ids: params.assetIds,
    folder_id: params.folderId,
  });

  return {
    movedCount: response.moved_count,
    message: response.message,
  };
}
