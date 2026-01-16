/**
 * Mixamo animation import API service.
 */

import { apiClient } from './client';
import type { AnimationClip, AnimationType, LoopMode } from '../../stores/animationStore';

export interface MixamoValidateResult {
  isValid: boolean;
  animationName: string;
  durationSeconds: number;
  fps: number;
  sourceBones: number;
  mappedBones: number;
  coveragePercent: number;
  hasAllRequired: boolean;
  missingRequired: string[];
  warnings: string[];
}

export interface MixamoUploadResult {
  success: boolean;
  clipId: string;
  name: string;
  durationSeconds: number;
  mappedBones: number;
  warnings: string[];
}

/**
 * Validate a Mixamo FBX file before importing.
 */
export async function validateMixamoFbx(
  file: File,
  assetId?: string
): Promise<MixamoValidateResult> {
  const formData = new FormData();
  formData.append('file', file);
  if (assetId) {
    formData.append('asset_id', assetId);
  }

  const response = await apiClient.post<{
    is_valid: boolean;
    animation_name: string;
    duration_seconds: number;
    fps: number;
    source_bones: number;
    mapped_bones: number;
    coverage_percent: number;
    has_all_required: boolean;
    missing_required: string[];
    warnings: string[];
  }>('/animation/mixamo/validate', formData);

  return {
    isValid: response.is_valid,
    animationName: response.animation_name,
    durationSeconds: response.duration_seconds,
    fps: response.fps,
    sourceBones: response.source_bones,
    mappedBones: response.mapped_bones,
    coveragePercent: response.coverage_percent,
    hasAllRequired: response.has_all_required,
    missingRequired: response.missing_required,
    warnings: response.warnings,
  };
}

/**
 * Upload and import a Mixamo FBX animation.
 */
export async function uploadMixamoAnimation(
  file: File,
  assetId: string,
  name?: string
): Promise<MixamoUploadResult> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('asset_id', assetId);
  if (name) {
    formData.append('name', name);
  }

  const response = await apiClient.post<{
    success: boolean;
    clip_id: string;
    name: string;
    duration_seconds: number;
    mapped_bones: number;
    warnings: string[];
  }>('/animation/mixamo/upload', formData);

  return {
    success: response.success,
    clipId: response.clip_id,
    name: response.name,
    durationSeconds: response.duration_seconds,
    mappedBones: response.mapped_bones,
    warnings: response.warnings,
  };
}

/**
 * Upload Mixamo animation and return full AnimationClip with keyframe data.
 */
export async function importMixamoAnimation(
  file: File,
  assetId: string,
  name?: string
): Promise<AnimationClip> {
  // First upload the animation
  const uploadResult = await uploadMixamoAnimation(file, assetId, name);

  if (!uploadResult.success) {
    throw new Error('Failed to upload Mixamo animation');
  }

  // Fetch the keyframe data for the created clip
  const keyframeData = await apiClient.get<{
    name: string;
    duration: number;
    frame_rate: number;
    tracks: Array<{
      bone_name: string;
      times: number[];
      rotations?: number[][];
      positions?: number[][];
      scales?: number[][];
    }>;
  }>(`/animation/clips/${uploadResult.clipId}/data`);

  // Transform tracks to flat format expected by Three.js
  const flatTracks: Array<{
    bone_name: string;
    property: 'rotation' | 'position' | 'scale';
    times: number[];
    values: number[];
    interpolation?: string;
  }> = [];

  for (const track of keyframeData.tracks) {
    if (track.rotations && track.rotations.length > 0) {
      flatTracks.push({
        bone_name: track.bone_name,
        property: 'rotation',
        times: track.times,
        values: track.rotations.flat(),
      });
    }
    if (track.positions && track.positions.length > 0) {
      flatTracks.push({
        bone_name: track.bone_name,
        property: 'position',
        times: track.times,
        values: track.positions.flat(),
      });
    }
    if (track.scales && track.scales.length > 0) {
      flatTracks.push({
        bone_name: track.bone_name,
        property: 'scale',
        times: track.times,
        values: track.scales.flat(),
      });
    }
  }

  return {
    id: uploadResult.clipId,
    assetId: assetId,
    name: uploadResult.name,
    animationType: 'imported' as AnimationType,
    duration: uploadResult.durationSeconds,
    parameters: {
      speed: 1.0,
      intensity: 1.0,
      blendFactor: 1.0,
    },
    loop_mode: 'loop' as LoopMode,
    createdAt: new Date().toISOString(),
    keyframe_data: {
      tracks: flatTracks,
      duration: keyframeData.duration,
      frame_rate: keyframeData.frame_rate,
    },
  };
}
