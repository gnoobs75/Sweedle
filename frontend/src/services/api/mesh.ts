/**
 * Mesh Editing API Service
 */

import { apiClient } from './client';

export interface MeshInfo {
  vertexCount: number;
  faceCount: number;
  hasNormals: boolean;
  hasUvs: boolean;
  isWatertight: boolean;
  boundingBoxMin: [number, number, number];
  boundingBoxMax: [number, number, number];
  centerOfMass: [number, number, number];
}

export interface SmoothMeshParams {
  assetId: string;
  iterations?: number;
  lambdaFactor?: number;
}

export interface RepairMeshParams {
  assetId: string;
  fillHoles?: boolean;
  fixNormals?: boolean;
  removeDegenerates?: boolean;
  mergeDuplicates?: boolean;
}

export interface DecimateMeshParams {
  assetId: string;
  targetFaces?: number;
  ratio?: number;
}

export interface CenterPivotParams {
  assetId: string;
  centerX?: boolean;
  centerY?: boolean;
  centerZ?: boolean;
}

export interface ScaleMeshParams {
  assetId: string;
  scaleFactor?: number;
  uniform?: boolean;
  scaleX?: number;
  scaleY?: number;
  scaleZ?: number;
}

export type CollisionMethod = 'convex_hull' | 'simplified' | 'box' | 'capsule' | 'sphere';

export interface GenerateCollisionParams {
  assetId: string;
  method?: CollisionMethod;
  simplificationRatio?: number;
}

export interface CollisionMeshInfo {
  method: string;
  vertexCount: number;
  faceCount: number;
  filePath: string;
  fileSizeBytes: number;
}

/**
 * Get detailed mesh information
 */
export async function getMeshInfo(assetId: string): Promise<MeshInfo> {
  const response = await apiClient.post<{
    success: boolean;
    asset_id: string;
    info: {
      vertexCount: number;
      faceCount: number;
      hasNormals: boolean;
      hasUvs: boolean;
      isWatertight: boolean;
      boundingBoxMin: number[];
      boundingBoxMax: number[];
      centerOfMass: number[];
    };
    error?: string;
  }>('/mesh/info', { asset_id: assetId });

  if (!response.success) {
    throw new Error(response.error || 'Failed to get mesh info');
  }

  return {
    ...response.info,
    boundingBoxMin: response.info.boundingBoxMin as [number, number, number],
    boundingBoxMax: response.info.boundingBoxMax as [number, number, number],
    centerOfMass: response.info.centerOfMass as [number, number, number],
  };
}

/**
 * Apply Laplacian smoothing to mesh
 */
export async function smoothMesh(params: SmoothMeshParams): Promise<{
  success: boolean;
  originalVertexCount: number;
  newVertexCount: number;
  message: string;
}> {
  const response = await apiClient.post<{
    success: boolean;
    asset_id: string;
    original_vertex_count: number;
    new_vertex_count: number;
    message: string;
    error?: string;
  }>('/mesh/smooth', {
    asset_id: params.assetId,
    iterations: params.iterations ?? 1,
    lambda_factor: params.lambdaFactor ?? 0.5,
  });

  if (!response.success) {
    throw new Error(response.error || 'Failed to smooth mesh');
  }

  return {
    success: true,
    originalVertexCount: response.original_vertex_count,
    newVertexCount: response.new_vertex_count,
    message: response.message,
  };
}

/**
 * Repair mesh issues
 */
export async function repairMesh(params: RepairMeshParams): Promise<{
  success: boolean;
  holesFilled: number;
  facesRemoved: number;
  verticesMerged: number;
  normalsFixed: boolean;
  message: string;
}> {
  const response = await apiClient.post<{
    success: boolean;
    asset_id: string;
    holes_filled: number;
    faces_removed: number;
    vertices_merged: number;
    normals_fixed: boolean;
    message: string;
    error?: string;
  }>('/mesh/repair', {
    asset_id: params.assetId,
    fill_holes: params.fillHoles ?? true,
    fix_normals: params.fixNormals ?? true,
    remove_degenerates: params.removeDegenerates ?? true,
    merge_duplicates: params.mergeDuplicates ?? true,
  });

  if (!response.success) {
    throw new Error(response.error || 'Failed to repair mesh');
  }

  return {
    success: true,
    holesFilled: response.holes_filled,
    facesRemoved: response.faces_removed,
    verticesMerged: response.vertices_merged,
    normalsFixed: response.normals_fixed,
    message: response.message,
  };
}

/**
 * Decimate mesh (reduce faces)
 */
export async function decimateMesh(params: DecimateMeshParams): Promise<{
  success: boolean;
  originalFaces: number;
  newFaces: number;
  reductionPercent: number;
  message: string;
}> {
  const response = await apiClient.post<{
    success: boolean;
    asset_id: string;
    original_faces: number;
    new_faces: number;
    reduction_percent: number;
    message: string;
    error?: string;
  }>('/mesh/decimate', {
    asset_id: params.assetId,
    target_faces: params.targetFaces,
    ratio: params.ratio,
  });

  if (!response.success) {
    throw new Error(response.error || 'Failed to decimate mesh');
  }

  return {
    success: true,
    originalFaces: response.original_faces,
    newFaces: response.new_faces,
    reductionPercent: response.reduction_percent,
    message: response.message,
  };
}

/**
 * Center mesh pivot
 */
export async function centerPivot(params: CenterPivotParams): Promise<{
  success: boolean;
  offsetApplied: [number, number, number];
  message: string;
}> {
  const response = await apiClient.post<{
    success: boolean;
    asset_id: string;
    offset_applied: number[];
    message: string;
    error?: string;
  }>('/mesh/center-pivot', {
    asset_id: params.assetId,
    center_x: params.centerX ?? true,
    center_y: params.centerY ?? false,
    center_z: params.centerZ ?? true,
  });

  if (!response.success) {
    throw new Error(response.error || 'Failed to center pivot');
  }

  return {
    success: true,
    offsetApplied: response.offset_applied as [number, number, number],
    message: response.message,
  };
}

/**
 * Scale mesh
 */
export async function scaleMesh(params: ScaleMeshParams): Promise<{
  success: boolean;
  scaleApplied: [number, number, number];
  message: string;
}> {
  const response = await apiClient.post<{
    success: boolean;
    asset_id: string;
    scale_applied: number[];
    message: string;
    error?: string;
  }>('/mesh/scale', {
    asset_id: params.assetId,
    scale_factor: params.scaleFactor ?? 1.0,
    uniform: params.uniform ?? true,
    scale_x: params.scaleX,
    scale_y: params.scaleY,
    scale_z: params.scaleZ,
  });

  if (!response.success) {
    throw new Error(response.error || 'Failed to scale mesh');
  }

  return {
    success: true,
    scaleApplied: response.scale_applied as [number, number, number],
    message: response.message,
  };
}

/**
 * Generate collision mesh for physics
 */
export async function generateCollisionMesh(params: GenerateCollisionParams): Promise<{
  success: boolean;
  collision: CollisionMeshInfo | null;
  message: string;
}> {
  const response = await apiClient.post<{
    success: boolean;
    asset_id: string;
    collision?: {
      method: string;
      vertex_count: number;
      face_count: number;
      file_path: string;
      file_size_bytes: number;
    };
    message: string;
    error?: string;
  }>('/mesh/generate-collision', {
    asset_id: params.assetId,
    method: params.method ?? 'convex_hull',
    simplification_ratio: params.simplificationRatio ?? 0.1,
  });

  if (!response.success) {
    throw new Error(response.error || 'Failed to generate collision mesh');
  }

  return {
    success: true,
    collision: response.collision ? {
      method: response.collision.method,
      vertexCount: response.collision.vertex_count,
      faceCount: response.collision.face_count,
      filePath: response.collision.file_path,
      fileSizeBytes: response.collision.file_size_bytes,
    } : null,
    message: response.message,
  };
}
