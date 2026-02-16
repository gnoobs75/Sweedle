/**
 * Materials API Service
 */

import { apiClient } from './client';

export interface MaterialInfo {
  hasColorTexture: boolean;
  hasNormalMap: boolean;
  hasRoughnessMap: boolean;
  hasMetallicMap: boolean;
  hasAoMap: boolean;
  colorTexturePath?: string;
  normalMapPath?: string;
  roughnessMapPath?: string;
  metallicMapPath?: string;
  aoMapPath?: string;
}

export interface PBRMapPaths {
  color: string;
  normal: string;
  roughness: string;
  metallic: string;
  ao: string;
}

export interface GeneratePBRMapsParams {
  assetId: string;
  normalStrength?: number;
  baseRoughness?: number;
  roughnessVariance?: number;
  aoStrength?: number;
}

/**
 * Get material information for an asset.
 */
export async function getMaterialInfo(assetId: string): Promise<MaterialInfo> {
  const response = await apiClient.get<{
    success: boolean;
    asset_id: string;
    info: {
      has_color_texture: boolean;
      has_normal_map: boolean;
      has_roughness_map: boolean;
      has_metallic_map: boolean;
      has_ao_map: boolean;
      color_texture_path?: string;
      normal_map_path?: string;
      roughness_map_path?: string;
      metallic_map_path?: string;
      ao_map_path?: string;
    } | null;
    error?: string;
  }>(`/materials/${assetId}/info`);

  if (!response.success || !response.info) {
    throw new Error(response.error || 'Failed to get material info');
  }

  return {
    hasColorTexture: response.info.has_color_texture,
    hasNormalMap: response.info.has_normal_map,
    hasRoughnessMap: response.info.has_roughness_map,
    hasMetallicMap: response.info.has_metallic_map,
    hasAoMap: response.info.has_ao_map,
    colorTexturePath: response.info.color_texture_path,
    normalMapPath: response.info.normal_map_path,
    roughnessMapPath: response.info.roughness_map_path,
    metallicMapPath: response.info.metallic_map_path,
    aoMapPath: response.info.ao_map_path,
  };
}

/**
 * Generate PBR material maps from the asset's color texture.
 */
export async function generatePBRMaps(params: GeneratePBRMapsParams): Promise<{
  success: boolean;
  maps?: PBRMapPaths;
  message: string;
  error?: string;
}> {
  const response = await apiClient.post<{
    success: boolean;
    asset_id: string;
    maps?: {
      color: string;
      normal: string;
      roughness: string;
      metallic: string;
      ao: string;
    };
    message: string;
    error?: string;
  }>('/materials/generate-pbr', {
    asset_id: params.assetId,
    normal_strength: params.normalStrength ?? 1.0,
    base_roughness: params.baseRoughness ?? 0.5,
    roughness_variance: params.roughnessVariance ?? 0.3,
    ao_strength: params.aoStrength ?? 1.0,
  });

  return {
    success: response.success,
    maps: response.maps,
    message: response.message,
    error: response.error,
  };
}
