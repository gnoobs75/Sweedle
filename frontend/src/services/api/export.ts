/**
 * Export API Service
 */

import { apiClient } from './client';
import type { EngineType, ExportOptions } from '../../types';

interface ExportToEngineParams {
  assetId: string;
  engine: EngineType;
  projectPath: string;
  includeTextures?: boolean;
  generateLods?: boolean;
  lodLevels?: number[];
  compressMesh?: boolean;
}

interface GenerateLODsParams {
  assetId: string;
  levels?: number[];
}

interface ExportResult {
  success: boolean;
  exportPath: string;
  filesExported: string[];
  message: string;
}

interface LODResult {
  success: boolean;
  lodPaths: Record<string, string>;
  message: string;
}

/**
 * Export asset to Unity project
 */
export async function exportToUnity(
  params: ExportToEngineParams
): Promise<ExportResult> {
  const response = await apiClient.post<{
    success: boolean;
    export_path: string;
    files_exported: string[];
    message: string;
  }>('/export/to-unity', {
    asset_id: params.assetId,
    project_path: params.projectPath,
    include_textures: params.includeTextures ?? true,
    generate_lods: params.generateLods ?? false,
    lod_levels: params.lodLevels,
    compress_mesh: params.compressMesh ?? false,
  });

  return {
    success: response.success,
    exportPath: response.export_path,
    filesExported: response.files_exported,
    message: response.message,
  };
}

/**
 * Export asset to Unreal Engine project
 */
export async function exportToUnreal(
  params: ExportToEngineParams
): Promise<ExportResult> {
  const response = await apiClient.post<{
    success: boolean;
    export_path: string;
    files_exported: string[];
    message: string;
  }>('/export/to-unreal', {
    asset_id: params.assetId,
    project_path: params.projectPath,
    include_textures: params.includeTextures ?? true,
    generate_lods: params.generateLods ?? false,
    lod_levels: params.lodLevels,
    compress_mesh: params.compressMesh ?? false,
  });

  return {
    success: response.success,
    exportPath: response.export_path,
    filesExported: response.files_exported,
    message: response.message,
  };
}

/**
 * Export asset to Godot project
 */
export async function exportToGodot(
  params: ExportToEngineParams
): Promise<ExportResult> {
  const response = await apiClient.post<{
    success: boolean;
    export_path: string;
    files_exported: string[];
    message: string;
  }>('/export/to-godot', {
    asset_id: params.assetId,
    project_path: params.projectPath,
    include_textures: params.includeTextures ?? true,
    generate_lods: params.generateLods ?? false,
    lod_levels: params.lodLevels,
    compress_mesh: params.compressMesh ?? false,
  });

  return {
    success: response.success,
    exportPath: response.export_path,
    filesExported: response.files_exported,
    message: response.message,
  };
}

/**
 * Export to any engine based on type
 */
export async function exportToEngine(
  params: ExportToEngineParams
): Promise<ExportResult> {
  switch (params.engine) {
    case 'unity':
      return exportToUnity(params);
    case 'unreal':
      return exportToUnreal(params);
    case 'godot':
      return exportToGodot(params);
    default:
      throw new Error(`Unknown engine type: ${params.engine}`);
  }
}

/**
 * Generate LODs for an asset
 */
export async function generateLODs(params: GenerateLODsParams): Promise<LODResult> {
  const response = await apiClient.post<{
    success: boolean;
    lod_paths: Record<string, string>;
    message: string;
  }>('/export/generate-lods', {
    asset_id: params.assetId,
    levels: params.levels ?? [1.0, 0.5, 0.25, 0.1],
  });

  return {
    success: response.success,
    lodPaths: response.lod_paths,
    message: response.message,
  };
}

/**
 * Convert asset to different format
 */
export async function convertFormat(
  assetId: string,
  targetFormat: 'glb' | 'obj' | 'fbx'
): Promise<{ downloadUrl: string }> {
  const response = await apiClient.post<{ download_url: string }>(
    '/export/convert',
    {
      asset_id: assetId,
      target_format: targetFormat,
    }
  );

  return {
    downloadUrl: response.download_url,
  };
}

/**
 * Validate engine project path
 */
export async function validateProjectPath(
  engine: EngineType,
  projectPath: string
): Promise<{ valid: boolean; message?: string }> {
  const response = await apiClient.post<{ valid: boolean; message?: string }>(
    '/export/validate-project',
    {
      engine,
      project_path: projectPath,
    }
  );

  return response;
}

/**
 * Generate LODs using the new API
 */
export async function generateLods(params: {
  assetId: string;
  ratios?: number[];
}): Promise<{
  success: boolean;
  lodLevels: Array<{
    level: number;
    ratio: number;
    filePath: string;
    vertexCount: number;
    faceCount: number;
  }>;
  error?: string;
}> {
  const response = await apiClient.post<{
    success: boolean;
    asset_id: string;
    lod_levels: Array<{
      level: number;
      ratio: number;
      file_path: string;
      vertex_count: number;
      face_count: number;
      file_size_bytes: number;
    }>;
    error?: string;
  }>('/export/generate-lods', {
    asset_id: params.assetId,
    ratios: params.ratios,
  });

  return {
    success: response.success,
    lodLevels: response.lod_levels.map((l) => ({
      level: l.level,
      ratio: l.ratio,
      filePath: l.file_path,
      vertexCount: l.vertex_count,
      faceCount: l.face_count,
    })),
    error: response.error,
  };
}

/**
 * Validate an asset for engine compatibility
 */
export async function validateAsset(params: {
  assetId: string;
  targetEngine?: string;
}): Promise<{
  isValid: boolean;
  vertexCount: number;
  faceCount: number;
  hasNormals: boolean;
  hasUvs: boolean;
  issues: Array<{
    category: string;
    severity: string;
    code: string;
    message: string;
    details?: string;
    fix_suggestion?: string;
  }>;
}> {
  const response = await apiClient.post<{
    is_valid: boolean;
    asset_id: string;
    vertex_count: number;
    face_count: number;
    has_normals: boolean;
    has_uvs: boolean;
    file_size_bytes: number;
    issues: Array<{
      category: string;
      severity: string;
      code: string;
      message: string;
      details?: string;
      fix_suggestion?: string;
    }>;
  }>('/export/validate', {
    asset_id: params.assetId,
    target_engine: params.targetEngine,
  });

  return {
    isValid: response.is_valid,
    vertexCount: response.vertex_count,
    faceCount: response.face_count,
    hasNormals: response.has_normals,
    hasUvs: response.has_uvs,
    issues: response.issues,
  };
}

/**
 * Compress an asset with Draco
 */
export async function compressAsset(params: {
  assetId: string;
  quality?: 'high_quality' | 'balanced' | 'high_compression';
}): Promise<{
  success: boolean;
  originalSizeBytes: number;
  compressedSizeBytes: number;
  compressionRatio: number;
  sizeReductionPercent: number;
  error?: string;
}> {
  const response = await apiClient.post<{
    success: boolean;
    asset_id: string;
    original_size_bytes: number;
    compressed_size_bytes: number;
    compression_ratio: number;
    size_reduction_percent: number;
    error?: string;
  }>('/export/compress', {
    asset_id: params.assetId,
    quality: params.quality || 'balanced',
  });

  return {
    success: response.success,
    originalSizeBytes: response.original_size_bytes,
    compressedSizeBytes: response.compressed_size_bytes,
    compressionRatio: response.compression_ratio,
    sizeReductionPercent: response.size_reduction_percent,
    error: response.error,
  };
}

/**
 * Export to engine (unified API)
 */
export async function exportToEngineUnified(params: {
  assetId: string;
  engine: EngineType;
  projectPath: string;
  includeLods?: boolean;
  compress?: boolean;
  format?: string;
}): Promise<{
  success: boolean;
  exportedFiles: string[];
  error?: string;
}> {
  const response = await apiClient.post<{
    success: boolean;
    asset_id: string;
    exported_files: string[];
    error?: string;
  }>('/export/to-engine', {
    asset_id: params.assetId,
    engine: params.engine,
    project_path: params.projectPath,
    include_lods: params.includeLods ?? true,
    compress: params.compress ?? true,
    format: params.format || 'glb',
  });

  return {
    success: response.success,
    exportedFiles: response.exported_files,
    error: response.error,
  };
}
