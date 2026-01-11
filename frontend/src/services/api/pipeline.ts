/**
 * Pipeline API service for VRAM management
 */

import { apiClient } from './client';

interface PipelineStatusResponse {
  shape_loaded: boolean;
  texture_loaded: boolean;
  vram_allocated_gb: number;
  vram_free_gb: number;
  vram_total_gb: number;
  ready_for_stage: string;
}

interface PrepareStageResponse {
  success: boolean;
  message: string;
  freed_gb?: number;
  loaded_pipeline?: string;
}

interface UnloadResponse {
  success: boolean;
  message: string;
  freed_gb: number;
}

/**
 * Get current pipeline status and VRAM usage
 */
export async function getPipelineStatus(): Promise<PipelineStatusResponse> {
  return apiClient.get<PipelineStatusResponse>('/pipeline/status');
}

/**
 * Prepare VRAM for a specific workflow stage
 */
export async function prepareForStage(stage: string): Promise<PrepareStageResponse> {
  return apiClient.post<PrepareStageResponse>(`/pipeline/prepare/${stage}`);
}

/**
 * Unload all pipelines to free VRAM
 */
export async function unloadAllPipelines(): Promise<UnloadResponse> {
  return apiClient.post<UnloadResponse>('/pipeline/unload');
}
