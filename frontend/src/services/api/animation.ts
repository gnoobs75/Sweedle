/**
 * Animation API service.
 */

import { apiClient } from './client';
import type {
  AnimationType,
  AnimationPreset,
  AnimationClip,
  AnimationParameters,
  AnimationData,
  LoopMode,
} from '../../stores/animationStore';

export interface CreateAnimationParams {
  assetId: string;
  presetId: string;
  name?: string;
  parameters?: AnimationParameters;
  loopMode?: LoopMode;
}

/**
 * Get available animation presets.
 */
export async function getAnimationPresets(
  characterType?: string
): Promise<AnimationPreset[]> {
  const endpoint = characterType
    ? `/animation/presets?character_type=${characterType}`
    : '/animation/presets';

  const response = await apiClient.get<
    Array<{
      id: string;
      name: string;
      description: string;
      animation_type: string;
      character_type: string;
      default_parameters: {
        speed: number;
        intensity: number;
        blend_factor: number;
      };
      duration: number;
      thumbnail_url?: string;
      tags: string[];
    }>
  >(endpoint);

  return response.map((p) => ({
    id: p.id,
    name: p.name,
    description: p.description,
    animationType: p.animation_type as AnimationType,
    characterType: p.character_type as 'humanoid' | 'quadruped',
    defaultParameters: {
      speed: p.default_parameters.speed,
      intensity: p.default_parameters.intensity,
      blendFactor: p.default_parameters.blend_factor,
    },
    duration: p.duration,
    thumbnailUrl: p.thumbnail_url,
    tags: p.tags,
  }));
}

/**
 * Get a specific animation preset.
 */
export async function getAnimationPreset(presetId: string): Promise<AnimationPreset> {
  const response = await apiClient.get<{
    id: string;
    name: string;
    description: string;
    animation_type: string;
    character_type: string;
    default_parameters: {
      speed: number;
      intensity: number;
      blend_factor: number;
    };
    duration: number;
    thumbnail_url?: string;
    tags: string[];
  }>(`/animation/presets/${presetId}`);

  return {
    id: response.id,
    name: response.name,
    description: response.description,
    animationType: response.animation_type as AnimationType,
    characterType: response.character_type as 'humanoid' | 'quadruped',
    defaultParameters: {
      speed: response.default_parameters.speed,
      intensity: response.default_parameters.intensity,
      blendFactor: response.default_parameters.blend_factor,
    },
    duration: response.duration,
    thumbnailUrl: response.thumbnail_url,
    tags: response.tags,
  };
}

/**
 * Create an animation clip from a preset.
 * Returns the clip with keyframe data included for immediate playback.
 */
export async function createAnimation(
  params: CreateAnimationParams
): Promise<AnimationClip> {
  const response = await apiClient.post<{
    id: string;
    asset_id: string;
    name: string;
    animation_type: string;
    duration: number;
    parameters: {
      speed: number;
      intensity: number;
      blend_factor: number;
    };
    loop_mode: string;
    created_at: string;
  }>('/animation/clips', {
    asset_id: params.assetId,
    preset_id: params.presetId,
    name: params.name,
    parameters: params.parameters
      ? {
          speed: params.parameters.speed,
          intensity: params.parameters.intensity,
          blend_factor: params.parameters.blendFactor,
        }
      : undefined,
    loop_mode: params.loopMode || 'loop',
  });

  // Fetch keyframe data for playback
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
  }>(`/animation/clips/${response.id}/data`);

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
        values: track.rotations.flat(), // Flatten [x,y,z,w] arrays
      });
    }
    if (track.positions && track.positions.length > 0) {
      flatTracks.push({
        bone_name: track.bone_name,
        property: 'position',
        times: track.times,
        values: track.positions.flat(), // Flatten [x,y,z] arrays
      });
    }
    if (track.scales && track.scales.length > 0) {
      flatTracks.push({
        bone_name: track.bone_name,
        property: 'scale',
        times: track.times,
        values: track.scales.flat(), // Flatten [x,y,z] arrays
      });
    }
  }

  return {
    id: response.id,
    assetId: response.asset_id,
    name: response.name,
    animationType: response.animation_type as AnimationType,
    duration: response.duration,
    parameters: {
      speed: response.parameters.speed,
      intensity: response.parameters.intensity,
      blendFactor: response.parameters.blend_factor,
    },
    loop_mode: response.loop_mode as LoopMode,
    createdAt: response.created_at,
    keyframe_data: {
      tracks: flatTracks,
      duration: keyframeData.duration,
      frame_rate: keyframeData.frame_rate,
    },
  };
}

/**
 * Get all animation clips for an asset.
 */
export async function getAssetAnimations(assetId: string): Promise<AnimationClip[]> {
  const response = await apiClient.get<{
    clips: Array<{
      id: string;
      asset_id: string;
      name: string;
      animation_type: string;
      duration: number;
      parameters: {
        speed: number;
        intensity: number;
        blend_factor: number;
      };
      loop_mode: string;
      created_at: string;
    }>;
    total: number;
  }>(`/animation/clips/asset/${assetId}`);

  return response.clips.map((c) => ({
    id: c.id,
    assetId: c.asset_id,
    name: c.name,
    animationType: c.animation_type as AnimationType,
    duration: c.duration,
    parameters: {
      speed: c.parameters.speed,
      intensity: c.parameters.intensity,
      blendFactor: c.parameters.blend_factor,
    },
    loop_mode: c.loop_mode as LoopMode,
    createdAt: c.created_at,
  }));
}

/**
 * Get a specific animation clip.
 */
export async function getAnimation(clipId: string): Promise<AnimationClip> {
  const response = await apiClient.get<{
    id: string;
    asset_id: string;
    name: string;
    animation_type: string;
    duration: number;
    parameters: {
      speed: number;
      intensity: number;
      blend_factor: number;
    };
    loop_mode: string;
    created_at: string;
  }>(`/animation/clips/${clipId}`);

  return {
    id: response.id,
    assetId: response.asset_id,
    name: response.name,
    animationType: response.animation_type as AnimationType,
    duration: response.duration,
    parameters: {
      speed: response.parameters.speed,
      intensity: response.parameters.intensity,
      blendFactor: response.parameters.blend_factor,
    },
    loop_mode: response.loop_mode as LoopMode,
    createdAt: response.created_at,
  };
}

/**
 * Delete an animation clip.
 */
export async function deleteAnimation(clipId: string): Promise<void> {
  await apiClient.delete(`/animation/clips/${clipId}`);
}

/**
 * Get the keyframe data for an animation clip (for playback).
 */
export async function getAnimationData(clipId: string): Promise<AnimationData> {
  const response = await apiClient.get<{
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
  }>(`/animation/clips/${clipId}/data`);

  return {
    name: response.name,
    duration: response.duration,
    frameRate: response.frame_rate,
    tracks: response.tracks.map((t) => ({
      boneName: t.bone_name,
      times: t.times,
      rotations: t.rotations,
      positions: t.positions,
      scales: t.scales,
    })),
  };
}

/**
 * Regenerate an animation with new parameters.
 */
export async function regenerateAnimation(
  clipId: string,
  parameters: AnimationParameters
): Promise<AnimationClip> {
  const response = await apiClient.put<{
    id: string;
    asset_id: string;
    name: string;
    animation_type: string;
    duration: number;
    parameters: {
      speed: number;
      intensity: number;
      blend_factor: number;
    };
    loop_mode: string;
    created_at: string;
  }>(`/animation/clips/${clipId}/regenerate`, {
    speed: parameters.speed,
    intensity: parameters.intensity,
    blend_factor: parameters.blendFactor,
  });

  return {
    id: response.id,
    assetId: response.asset_id,
    name: response.name,
    animationType: response.animation_type as AnimationType,
    duration: response.duration,
    parameters: {
      speed: response.parameters.speed,
      intensity: response.parameters.intensity,
      blendFactor: response.parameters.blend_factor,
    },
    loop_mode: response.loop_mode as LoopMode,
    createdAt: response.created_at,
  };
}

export interface ExportWithAnimationsParams {
  assetId: string;
  animationIds?: string[];
  outputFilename?: string;
}

export interface ExportWithAnimationsResult {
  success: boolean;
  assetId: string;
  outputPath: string;
  animationsEmbedded: number;
  animationNames: string[];
  fileSizeBytes: number;
  error?: string;
}

/**
 * Export an asset with embedded animations to a GLB file.
 */
export async function exportWithAnimations(
  params: ExportWithAnimationsParams
): Promise<ExportWithAnimationsResult> {
  const response = await apiClient.post<{
    success: boolean;
    asset_id: string;
    output_path: string;
    animations_embedded: number;
    animation_names: string[];
    file_size_bytes: number;
    error?: string;
  }>('/export/with-animations', {
    asset_id: params.assetId,
    animation_ids: params.animationIds,
    output_filename: params.outputFilename,
  });

  return {
    success: response.success,
    assetId: response.asset_id,
    outputPath: response.output_path,
    animationsEmbedded: response.animations_embedded,
    animationNames: response.animation_names,
    fileSizeBytes: response.file_size_bytes,
    error: response.error,
  };
}
