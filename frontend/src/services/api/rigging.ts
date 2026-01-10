/**
 * Rigging API service.
 */

import { apiClient } from './client';
import type { CharacterType, RiggingProcessor, SkeletonData, RiggingStatus } from '../../stores/riggingStore';

export interface AutoRigParams {
  assetId: string;
  characterType?: CharacterType;
  processor?: RiggingProcessor;
  priority?: 'low' | 'normal' | 'high';
  force?: boolean;
}

export interface AutoRigResponse {
  jobId: string;
  assetId: string;
  status: string;
  message: string;
  queuePosition?: number;
}

export interface RiggingJobStatus {
  jobId: string;
  assetId: string;
  status: RiggingStatus;
  progress: number;
  stage: string;
  detectedType?: CharacterType;
  processorUsed?: RiggingProcessor;
  error?: string;
  createdAt: string;
  startedAt?: string;
  completedAt?: string;
}

export interface DetectTypeResponse {
  assetId: string;
  detectedType: CharacterType;
  confidence: number;
  analysis?: Record<string, unknown>;
}

export interface SkeletonResponse {
  assetId: string;
  skeleton: SkeletonData;
  riggedMeshPath: string;
  processorUsed: RiggingProcessor;
  createdAt: string;
}

export interface SkeletonTemplateInfo {
  name: string;
  characterType: CharacterType;
  boneCount: number;
  description: string;
  previewUrl?: string;
}

/**
 * Submit an asset for auto-rigging.
 */
export async function autoRigAsset(params: AutoRigParams): Promise<AutoRigResponse> {
  const formData = new FormData();
  formData.append('asset_id', params.assetId);

  if (params.characterType) {
    formData.append('character_type', params.characterType);
  }
  if (params.processor) {
    formData.append('processor', params.processor);
  }
  if (params.priority) {
    formData.append('priority', params.priority);
  }
  if (params.force) {
    formData.append('force', 'true');
  }

  const response = await apiClient.post<{
    job_id: string;
    asset_id: string;
    status: string;
    message: string;
    queue_position?: number;
  }>('/rigging/auto-rig', formData);

  return {
    jobId: response.job_id,
    assetId: response.asset_id,
    status: response.status,
    message: response.message,
    queuePosition: response.queue_position,
  };
}

/**
 * Reset rigging state for an asset.
 */
export async function resetRigging(assetId: string): Promise<{ message: string; assetId: string }> {
  const response = await apiClient.post<{ message: string; asset_id: string }>(
    `/rigging/reset/${assetId}`
  );
  return {
    message: response.message,
    assetId: response.asset_id,
  };
}

/**
 * Get the status of a rigging job.
 */
export async function getRiggingJobStatus(jobId: string): Promise<RiggingJobStatus> {
  const response = await apiClient.get<{
    job_id: string;
    asset_id: string;
    status: string;
    progress: number;
    stage: string;
    detected_type?: string;
    processor_used?: string;
    error?: string;
    created_at: string;
    started_at?: string;
    completed_at?: string;
  }>(`/rigging/jobs/${jobId}`);

  return {
    jobId: response.job_id,
    assetId: response.asset_id,
    status: response.status as RiggingStatus,
    progress: response.progress,
    stage: response.stage,
    detectedType: response.detected_type as CharacterType | undefined,
    processorUsed: response.processor_used as RiggingProcessor | undefined,
    error: response.error,
    createdAt: response.created_at,
    startedAt: response.started_at,
    completedAt: response.completed_at,
  };
}

/**
 * Cancel a pending rigging job.
 */
export async function cancelRiggingJob(jobId: string): Promise<{ message: string; jobId: string }> {
  const response = await apiClient.delete<{ message: string; job_id: string }>(
    `/rigging/jobs/${jobId}`
  );
  return {
    message: response.message,
    jobId: response.job_id,
  };
}

/**
 * Get skeleton data for a rigged asset.
 */
export async function getSkeleton(assetId: string): Promise<SkeletonResponse | null> {
  try {
    const response = await apiClient.get<{
      asset_id: string;
      skeleton: {
        root_bone: string;
        bones: Array<{
          name: string;
          parent: string | null;
          head_position: [number, number, number];
          tail_position: [number, number, number];
          rotation: [number, number, number, number];
        }>;
        character_type: string;
        bone_count: number;
      };
      rigged_mesh_path: string;
      processor_used: string;
      created_at: string;
    }>(`/rigging/skeleton/${assetId}`);

    return {
      assetId: response.asset_id,
      skeleton: {
        rootBone: response.skeleton.root_bone,
        bones: response.skeleton.bones.map((b) => ({
          name: b.name,
          parent: b.parent,
          headPosition: b.head_position,
          tailPosition: b.tail_position,
          rotation: b.rotation,
        })),
        characterType: response.skeleton.character_type as CharacterType,
        boneCount: response.skeleton.bone_count,
      },
      riggedMeshPath: response.rigged_mesh_path,
      processorUsed: response.processor_used as RiggingProcessor,
      createdAt: response.created_at,
    };
  } catch {
    return null;
  }
}

/**
 * Detect the character type of an asset.
 */
export async function detectCharacterType(assetId: string): Promise<DetectTypeResponse> {
  const response = await apiClient.post<{
    asset_id: string;
    detected_type: string;
    confidence: number;
    analysis?: Record<string, unknown>;
  }>('/rigging/detect-type', { asset_id: assetId });

  return {
    assetId: response.asset_id,
    detectedType: response.detected_type as CharacterType,
    confidence: response.confidence,
    analysis: response.analysis,
  };
}

/**
 * List available skeleton templates.
 */
export async function listTemplates(): Promise<SkeletonTemplateInfo[]> {
  const response = await apiClient.get<{
    templates: Array<{
      name: string;
      character_type: string;
      bone_count: number;
      description: string;
      preview_url?: string;
    }>;
  }>('/rigging/templates');

  return response.templates.map((t) => ({
    name: t.name,
    characterType: t.character_type as CharacterType,
    boneCount: t.bone_count,
    description: t.description,
    previewUrl: t.preview_url,
  }));
}
