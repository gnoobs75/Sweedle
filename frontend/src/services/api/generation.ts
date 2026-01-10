/**
 * Generation API Service
 */

import { apiClient } from './client';
import type {
  GenerationParameters,
  GenerationResponse,
  JobStatusResponse,
  QueueStatus,
  Job,
} from '../../types';

interface GenerateFromImageParams {
  file: File;
  name?: string;
  parameters: GenerationParameters;
  priority?: 'low' | 'normal' | 'high';
  projectId?: string;
  tags?: string[];
}

interface GenerateFromTextParams {
  prompt: string;
  name?: string;
  parameters: GenerationParameters;
  priority?: 'low' | 'normal' | 'high';
  projectId?: string;
  tags?: string[];
}

/**
 * Submit an image for 3D generation
 */
export async function generateFromImage(
  params: GenerateFromImageParams
): Promise<GenerationResponse> {
  const formData = new FormData();
  formData.append('file', params.file);

  if (params.name) formData.append('name', params.name);
  formData.append('inference_steps', String(params.parameters.inferenceSteps));
  formData.append('guidance_scale', String(params.parameters.guidanceScale));
  formData.append('octree_resolution', String(params.parameters.octreeResolution));
  if (params.parameters.seed !== undefined) {
    formData.append('seed', String(params.parameters.seed));
  }
  formData.append('generate_texture', String(params.parameters.generateTexture));
  if (params.parameters.faceCount !== undefined) {
    formData.append('face_count', String(params.parameters.faceCount));
  }
  formData.append('output_format', params.parameters.outputFormat);
  formData.append('mode', params.parameters.mode);
  formData.append('priority', params.priority || 'normal');
  if (params.projectId) formData.append('project_id', params.projectId);
  if (params.tags?.length) formData.append('tags', params.tags.join(','));

  const response = await apiClient.post<{
    job_id: string;
    asset_id: string;
    status: string;
    message: string;
    queue_position?: number;
  }>('/generation/image-to-3d', formData);

  return {
    jobId: response.job_id,
    assetId: response.asset_id,
    status: response.status as GenerationResponse['status'],
    message: response.message,
    queuePosition: response.queue_position,
  };
}

/**
 * Submit text prompt for 3D generation (not yet implemented)
 */
export async function generateFromText(
  params: GenerateFromTextParams
): Promise<GenerationResponse> {
  const formData = new FormData();
  formData.append('prompt', params.prompt);

  if (params.name) formData.append('name', params.name);
  formData.append('inference_steps', String(params.parameters.inferenceSteps));
  formData.append('guidance_scale', String(params.parameters.guidanceScale));
  formData.append('octree_resolution', String(params.parameters.octreeResolution));
  if (params.parameters.seed !== undefined) {
    formData.append('seed', String(params.parameters.seed));
  }
  formData.append('generate_texture', String(params.parameters.generateTexture));
  if (params.parameters.faceCount !== undefined) {
    formData.append('face_count', String(params.parameters.faceCount));
  }
  formData.append('output_format', params.parameters.outputFormat);
  formData.append('mode', params.parameters.mode);
  formData.append('priority', params.priority || 'normal');
  if (params.projectId) formData.append('project_id', params.projectId);
  if (params.tags?.length) formData.append('tags', params.tags.join(','));

  const response = await apiClient.post<{
    job_id: string;
    asset_id: string;
    status: string;
    message: string;
    queue_position?: number;
  }>('/generation/text-to-3d', formData);

  return {
    jobId: response.job_id,
    assetId: response.asset_id,
    status: response.status as GenerationResponse['status'],
    message: response.message,
    queuePosition: response.queue_position,
  };
}

/**
 * Get job status
 */
export async function getJobStatus(jobId: string): Promise<JobStatusResponse> {
  const response = await apiClient.get<{
    job_id: string;
    asset_id?: string;
    status: string;
    progress: number;
    stage: string;
    message?: string;
    error?: string;
    created_at: string;
    started_at?: string;
    completed_at?: string;
  }>(`/generation/jobs/${jobId}`);

  return {
    jobId: response.job_id,
    assetId: response.asset_id,
    status: response.status as JobStatusResponse['status'],
    progress: response.progress,
    stage: response.stage,
    message: response.message,
    error: response.error,
    createdAt: response.created_at,
    startedAt: response.started_at,
    completedAt: response.completed_at,
  };
}

/**
 * Cancel a pending job
 */
export async function cancelJob(
  jobId: string
): Promise<{ message: string; jobId: string }> {
  const response = await apiClient.delete<{ message: string; job_id: string }>(
    `/generation/jobs/${jobId}`
  );
  return {
    message: response.message,
    jobId: response.job_id,
  };
}

/**
 * Get queue status
 */
export async function getQueueStatus(): Promise<QueueStatus> {
  const response = await apiClient.get<{
    queue_size: number;
    current_job_id?: string;
    pending_count: number;
    processing_count: number;
    completed_count: number;
  }>('/generation/queue/status');

  return {
    queueSize: response.queue_size,
    currentJobId: response.current_job_id,
    pendingCount: response.pending_count,
    processingCount: response.processing_count,
    completedCount: response.completed_count,
    failedCount: 0,
  };
}

/**
 * Get jobs in queue
 */
export async function getQueueJobs(
  limit = 20,
  includeCompleted = false
): Promise<Job[]> {
  const response = await apiClient.get<{
    jobs: Array<{
      job_id: string;
      job_type: string;
      status: string;
      progress: number;
      stage: string;
      priority: string;
      created_at: string;
      started_at?: string;
      completed_at?: string;
    }>;
    total: number;
  }>(`/generation/queue/jobs?limit=${limit}&include_completed=${includeCompleted}`);

  return response.jobs.map((job) => ({
    id: job.job_id,
    type: job.job_type as Job['type'],
    status: job.status as Job['status'],
    progress: job.progress,
    stage: job.stage,
    name: 'Generation Job',
    priority: job.priority.toLowerCase() as Job['priority'],
    createdAt: job.created_at,
    startedAt: job.started_at,
    completedAt: job.completed_at,
  }));
}

/**
 * Pause the queue (stop processing new jobs)
 */
export async function pauseQueue(): Promise<{ message: string }> {
  return apiClient.post('/generation/queue/pause', {});
}

/**
 * Resume the queue
 */
export async function resumeQueue(): Promise<{ message: string }> {
  return apiClient.post('/generation/queue/resume', {});
}

/**
 * Clear all jobs from the queue
 */
export async function clearQueue(): Promise<{ message: string; cleared: number }> {
  return apiClient.delete('/generation/queue');
}

/**
 * Retry a failed job
 */
export async function retryJob(jobId: string): Promise<{ message: string; jobId: string }> {
  const response = await apiClient.post<{ message: string; job_id: string }>(
    `/generation/jobs/${jobId}/retry`,
    {}
  );
  return {
    message: response.message,
    jobId: response.job_id,
  };
}

/**
 * Submit image to 3D generation (simplified interface for batch import)
 */
export interface SubmitImageParams {
  removeBackground?: boolean;
  foregroundRatio?: number;
  octreeResolution?: number;
  numInferenceSteps?: number;
  guidanceScale?: number;
  textureSize?: number;
}

export async function submitImageTo3D(
  file: File,
  params: SubmitImageParams = {}
): Promise<{ jobId: string; assetId: string }> {
  const formData = new FormData();
  formData.append('file', file);

  if (params.removeBackground !== undefined) {
    formData.append('remove_background', String(params.removeBackground));
  }
  if (params.foregroundRatio !== undefined) {
    formData.append('foreground_ratio', String(params.foregroundRatio));
  }
  if (params.octreeResolution !== undefined) {
    formData.append('octree_resolution', String(params.octreeResolution));
  }
  if (params.numInferenceSteps !== undefined) {
    formData.append('inference_steps', String(params.numInferenceSteps));
  }
  if (params.guidanceScale !== undefined) {
    formData.append('guidance_scale', String(params.guidanceScale));
  }
  if (params.textureSize !== undefined) {
    formData.append('texture_size', String(params.textureSize));
  }

  const response = await apiClient.post<{
    job_id: string;
    asset_id: string;
  }>('/generation/image-to-3d', formData);

  return {
    jobId: response.job_id,
    assetId: response.asset_id,
  };
}

/**
 * Image quality analysis result types
 */
export interface QualityCheck {
  name: string;
  passed: boolean;
  score: number;
  message: string;
  suggestion?: string;
}

export interface ImageAnalysis {
  overall_score: number;
  quality_level: 'excellent' | 'good' | 'fair' | 'poor';
  checks: QualityCheck[];
  warnings: string[];
  tips: string[];
}

/**
 * Analyze an image for 3D generation suitability
 */
export async function analyzeImage(file: File): Promise<ImageAnalysis> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await apiClient.post<{
    success: boolean;
    analysis: ImageAnalysis;
  }>('/generation/analyze-image', formData);

  return response.analysis;
}

/**
 * Add texture to an existing untextured asset
 *
 * This is for the two-step workflow:
 * 1. Generate shape only (fast)
 * 2. Preview and approve
 * 3. Add texture (this function)
 */
export async function addTextureToAsset(
  assetId: string,
  priority: 'low' | 'normal' | 'high' = 'normal'
): Promise<GenerationResponse> {
  const formData = new FormData();
  formData.append('priority', priority);

  const response = await apiClient.post<{
    job_id: string;
    asset_id: string;
    status: string;
    message: string;
    queue_position?: number;
  }>(`/generation/add-texture/${assetId}`, formData);

  return {
    jobId: response.job_id,
    assetId: response.asset_id,
    status: response.status as GenerationResponse['status'],
    message: response.message,
    queuePosition: response.queue_position,
  };
}
