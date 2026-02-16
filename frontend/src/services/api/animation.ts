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

interface RawKeyframeTrack {
  bone_name: string;
  times: number[];
  rotations?: number[][];
  positions?: number[][];
  scales?: number[][];
}

/** Flatten nested keyframe arrays into the flat format expected by Three.js */
function flattenAnimationTracks(tracks: RawKeyframeTrack[]) {
  const flat: Array<{
    bone_name: string;
    property: 'rotation' | 'position' | 'scale';
    times: number[];
    values: number[];
  }> = [];

  for (const track of tracks) {
    if (track.rotations && track.rotations.length > 0) {
      flat.push({
        bone_name: track.bone_name,
        property: 'rotation',
        times: track.times,
        values: track.rotations.flat(),
      });
    }
    if (track.positions && track.positions.length > 0) {
      flat.push({
        bone_name: track.bone_name,
        property: 'position',
        times: track.times,
        values: track.positions.flat(),
      });
    }
    if (track.scales && track.scales.length > 0) {
      flat.push({
        bone_name: track.bone_name,
        property: 'scale',
        times: track.times,
        values: track.scales.flat(),
      });
    }
  }

  return flat;
}

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
    tracks: RawKeyframeTrack[];
  }>(`/animation/clips/${response.id}/data`);

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
      tracks: flattenAnimationTracks(keyframeData.tracks),
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

  const clips: AnimationClip[] = response.clips.map((c) => ({
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

  // Fetch keyframe data for each clip so they can be played back
  const clipsWithData = await Promise.all(
    clips.map(async (clip) => {
      try {
        const keyframeData = await apiClient.get<{
          name: string;
          duration: number;
          frame_rate: number;
          tracks: RawKeyframeTrack[];
        }>(`/animation/clips/${clip.id}/data`);

        return {
          ...clip,
          keyframe_data: {
            tracks: flattenAnimationTracks(keyframeData.tracks),
            duration: keyframeData.duration,
            frame_rate: keyframeData.frame_rate,
          },
        };
      } catch (err) {
        console.warn(`Failed to fetch keyframe data for clip ${clip.id}:`, err);
        return clip;
      }
    })
  );

  return clipsWithData;
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

export interface GeneratePreviewParams {
  clipId: string;
  width?: number;
  height?: number;
  fps?: number;
  format?: 'gif' | 'webp';
}

export interface GeneratePreviewResult {
  success: boolean;
  clipId: string;
  previewPath?: string;
  frameCount: number;
  durationMs: number;
  fileSizeBytes: number;
  error?: string;
}

/**
 * Generate an animated preview (GIF/WebP) for an animation clip.
 */
export async function generateAnimationPreview(
  params: GeneratePreviewParams
): Promise<GeneratePreviewResult> {
  const response = await apiClient.post<{
    success: boolean;
    clip_id: string;
    preview_path?: string;
    frame_count: number;
    duration_ms: number;
    file_size_bytes: number;
    error?: string;
  }>(`/animation/clips/${params.clipId}/preview`, {
    clip_id: params.clipId,
    width: params.width || 256,
    height: params.height || 256,
    fps: params.fps || 15,
    format: params.format || 'gif',
  });

  return {
    success: response.success,
    clipId: response.clip_id,
    previewPath: response.preview_path,
    frameCount: response.frame_count,
    durationMs: response.duration_ms,
    fileSizeBytes: response.file_size_bytes,
    error: response.error,
  };
}

// ============ Animation Retargeting ============

export interface BoneMapping {
  sourceBone: string;
  targetBone: string;
  scaleFactor?: number;
}

export type RetargetingPreset =
  | 'mixamo_to_standard'
  | 'standard_to_mixamo'
  | 'blender_to_standard'
  | 'standard_to_blender'
  | 'unity_to_standard'
  | 'standard_to_unity'
  | 'auto_detect';

export interface RetargetingPresetInfo {
  id: RetargetingPreset;
  name: string;
  description: string;
  sourceType: string;
  targetType: string;
  mappingsCount: number;
}

export interface BoneMappingSuggestion {
  sourceBone: string;
  targetBone: string;
  confidence: number;
  reason: string;
}

export interface MappingSuggestionsResponse {
  success: boolean;
  sourceBones: string[];
  targetBones: string[];
  suggestions: BoneMappingSuggestion[];
  unmappedSource: string[];
  unmappedTarget: string[];
  message: string;
}

export interface RetargetAnimationParams {
  sourceClipId: string;
  targetAssetId: string;
  name?: string;
  preset?: RetargetingPreset;
  customMappings?: BoneMapping[];
  adjustProportions?: boolean;
  preserveRootMotion?: boolean;
}

export interface RetargetAnimationResponse {
  success: boolean;
  clipId?: string;
  sourceBonesMapped: number;
  targetBonesAffected: number;
  unmappedBones: string[];
  warnings: string[];
  message: string;
  error?: string;
}

/**
 * List available retargeting presets
 */
export async function listRetargetingPresets(): Promise<RetargetingPresetInfo[]> {
  const response = await apiClient.get<Array<{
    id: string;
    name: string;
    description: string;
    source_type: string;
    target_type: string;
    mappings_count: number;
  }>>('/animation/retargeting/presets');

  return response.map(p => ({
    id: p.id as RetargetingPreset,
    name: p.name,
    description: p.description,
    sourceType: p.source_type,
    targetType: p.target_type,
    mappingsCount: p.mappings_count,
  }));
}

/**
 * Get bone mapping suggestions between two skeletons
 */
export async function suggestBoneMappings(
  sourceAssetId: string,
  targetAssetId: string
): Promise<MappingSuggestionsResponse> {
  const response = await apiClient.post<{
    success: boolean;
    source_bones: string[];
    target_bones: string[];
    suggestions: Array<{
      source_bone: string;
      target_bone: string;
      confidence: number;
      reason: string;
    }>;
    unmapped_source: string[];
    unmapped_target: string[];
    message: string;
  }>('/animation/retargeting/suggest-mappings', {
    source_asset_id: sourceAssetId,
    target_asset_id: targetAssetId,
  });

  return {
    success: response.success,
    sourceBones: response.source_bones,
    targetBones: response.target_bones,
    suggestions: response.suggestions.map(s => ({
      sourceBone: s.source_bone,
      targetBone: s.target_bone,
      confidence: s.confidence,
      reason: s.reason,
    })),
    unmappedSource: response.unmapped_source,
    unmappedTarget: response.unmapped_target,
    message: response.message,
  };
}

/**
 * Retarget an animation to a different skeleton
 */
export async function retargetAnimation(
  params: RetargetAnimationParams
): Promise<RetargetAnimationResponse> {
  const response = await apiClient.post<{
    success: boolean;
    clip_id?: string;
    source_bones_mapped: number;
    target_bones_affected: number;
    unmapped_bones: string[];
    warnings: string[];
    message: string;
    error?: string;
  }>('/animation/retargeting/apply', {
    source_clip_id: params.sourceClipId,
    target_asset_id: params.targetAssetId,
    name: params.name,
    preset: params.preset,
    custom_mappings: params.customMappings?.map(m => ({
      source_bone: m.sourceBone,
      target_bone: m.targetBone,
      scale_factor: m.scaleFactor ?? 1.0,
    })),
    adjust_proportions: params.adjustProportions ?? true,
    preserve_root_motion: params.preserveRootMotion ?? true,
  });

  return {
    success: response.success,
    clipId: response.clip_id,
    sourceBonesMapped: response.source_bones_mapped,
    targetBonesAffected: response.target_bones_affected,
    unmappedBones: response.unmapped_bones,
    warnings: response.warnings,
    message: response.message,
    error: response.error,
  };
}
