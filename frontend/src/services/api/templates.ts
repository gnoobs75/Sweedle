/**
 * Workflow Templates API Service
 */

import { apiClient } from './client';

// ============ Types ============

export interface MeshSettings {
  inferenceSteps: number;
  guidanceScale: number;
  octreeResolution: number;
  seed?: number;
}

export interface TextureSettings {
  resolution: number;
  cameraViews: number;
}

export interface RiggingSettings {
  characterType: string;
  processor: string;
  autoDecimate: boolean;
  targetVertices: number;
}

export interface AnimationSettings {
  presets: string[];
  defaultSpeed: number;
  defaultIntensity: number;
}

export interface ExportSettings {
  format: string;
  dracoCompression: boolean;
  generateLods: boolean;
  lodLevels: number[];
  centerPivot: boolean;
  groundOrigin: boolean;
}

export interface WorkflowTemplate {
  id: string;
  name: string;
  description?: string;
  category?: string;
  includeMesh: boolean;
  includeTexture: boolean;
  includeRigging: boolean;
  includeAnimation: boolean;
  includeExport: boolean;
  meshSettings?: MeshSettings;
  textureSettings?: TextureSettings;
  riggingSettings?: RiggingSettings;
  animationSettings?: AnimationSettings;
  exportSettings?: ExportSettings;
  isBuiltin: boolean;
  useCount: number;
  createdAt?: string;
  updatedAt?: string;
}

export interface CreateTemplateParams {
  name: string;
  description?: string;
  category?: string;
  includeMesh?: boolean;
  includeTexture?: boolean;
  includeRigging?: boolean;
  includeAnimation?: boolean;
  includeExport?: boolean;
  meshSettings?: Partial<MeshSettings>;
  textureSettings?: Partial<TextureSettings>;
  riggingSettings?: Partial<RiggingSettings>;
  animationSettings?: Partial<AnimationSettings>;
  exportSettings?: Partial<ExportSettings>;
}

// ============ API Functions ============

function transformTemplateResponse(response: any): WorkflowTemplate {
  return {
    id: response.id,
    name: response.name,
    description: response.description,
    category: response.category,
    includeMesh: response.include_mesh,
    includeTexture: response.include_texture,
    includeRigging: response.include_rigging,
    includeAnimation: response.include_animation,
    includeExport: response.include_export,
    meshSettings: response.mesh_settings ? {
      inferenceSteps: response.mesh_settings.inference_steps,
      guidanceScale: response.mesh_settings.guidance_scale,
      octreeResolution: response.mesh_settings.octree_resolution,
      seed: response.mesh_settings.seed,
    } : undefined,
    textureSettings: response.texture_settings ? {
      resolution: response.texture_settings.resolution,
      cameraViews: response.texture_settings.camera_views,
    } : undefined,
    riggingSettings: response.rigging_settings ? {
      characterType: response.rigging_settings.character_type,
      processor: response.rigging_settings.processor,
      autoDecimate: response.rigging_settings.auto_decimate,
      targetVertices: response.rigging_settings.target_vertices,
    } : undefined,
    animationSettings: response.animation_settings ? {
      presets: response.animation_settings.presets,
      defaultSpeed: response.animation_settings.default_speed,
      defaultIntensity: response.animation_settings.default_intensity,
    } : undefined,
    exportSettings: response.export_settings ? {
      format: response.export_settings.format,
      dracoCompression: response.export_settings.draco_compression,
      generateLods: response.export_settings.generate_lods,
      lodLevels: response.export_settings.lod_levels,
      centerPivot: response.export_settings.center_pivot,
      groundOrigin: response.export_settings.ground_origin,
    } : undefined,
    isBuiltin: response.is_builtin,
    useCount: response.use_count,
    createdAt: response.created_at,
    updatedAt: response.updated_at,
  };
}

/**
 * List all workflow templates
 */
export async function listTemplates(
  category?: string,
  includeBuiltin = true
): Promise<WorkflowTemplate[]> {
  const params = new URLSearchParams();
  if (category) params.append('category', category);
  params.append('include_builtin', String(includeBuiltin));

  const response = await apiClient.get<{
    templates: any[];
    total: number;
  }>(`/workflow/templates?${params.toString()}`);

  return response.templates.map(transformTemplateResponse);
}

/**
 * Get a specific template
 */
export async function getTemplate(templateId: string): Promise<WorkflowTemplate> {
  const response = await apiClient.get<any>(`/workflow/templates/${templateId}`);
  return transformTemplateResponse(response);
}

/**
 * Create a new template
 */
export async function createTemplate(params: CreateTemplateParams): Promise<WorkflowTemplate> {
  const response = await apiClient.post<any>('/workflow/templates', {
    name: params.name,
    description: params.description,
    category: params.category,
    include_mesh: params.includeMesh ?? true,
    include_texture: params.includeTexture ?? true,
    include_rigging: params.includeRigging ?? false,
    include_animation: params.includeAnimation ?? false,
    include_export: params.includeExport ?? true,
    mesh_settings: params.meshSettings ? {
      inference_steps: params.meshSettings.inferenceSteps ?? 30,
      guidance_scale: params.meshSettings.guidanceScale ?? 5.5,
      octree_resolution: params.meshSettings.octreeResolution ?? 256,
      seed: params.meshSettings.seed,
    } : undefined,
    texture_settings: params.textureSettings ? {
      resolution: params.textureSettings.resolution ?? 1024,
      camera_views: params.textureSettings.cameraViews ?? 4,
    } : undefined,
    rigging_settings: params.riggingSettings ? {
      character_type: params.riggingSettings.characterType ?? 'auto',
      processor: params.riggingSettings.processor ?? 'auto',
      auto_decimate: params.riggingSettings.autoDecimate ?? true,
      target_vertices: params.riggingSettings.targetVertices ?? 30000,
    } : undefined,
    animation_settings: params.animationSettings ? {
      presets: params.animationSettings.presets ?? [],
      default_speed: params.animationSettings.defaultSpeed ?? 1.0,
      default_intensity: params.animationSettings.defaultIntensity ?? 1.0,
    } : undefined,
    export_settings: params.exportSettings ? {
      format: params.exportSettings.format ?? 'glb',
      draco_compression: params.exportSettings.dracoCompression ?? false,
      generate_lods: params.exportSettings.generateLods ?? false,
      lod_levels: params.exportSettings.lodLevels ?? [0.5, 0.25],
      center_pivot: params.exportSettings.centerPivot ?? true,
      ground_origin: params.exportSettings.groundOrigin ?? true,
    } : undefined,
  });

  return transformTemplateResponse(response);
}

/**
 * Update an existing template
 */
export async function updateTemplate(
  templateId: string,
  params: Partial<CreateTemplateParams>
): Promise<WorkflowTemplate> {
  const body: any = {};

  if (params.name !== undefined) body.name = params.name;
  if (params.description !== undefined) body.description = params.description;
  if (params.category !== undefined) body.category = params.category;
  if (params.includeMesh !== undefined) body.include_mesh = params.includeMesh;
  if (params.includeTexture !== undefined) body.include_texture = params.includeTexture;
  if (params.includeRigging !== undefined) body.include_rigging = params.includeRigging;
  if (params.includeAnimation !== undefined) body.include_animation = params.includeAnimation;
  if (params.includeExport !== undefined) body.include_export = params.includeExport;

  // Settings would need similar transformation...

  const response = await apiClient.patch<any>(`/workflow/templates/${templateId}`, body);
  return transformTemplateResponse(response);
}

/**
 * Delete a template
 */
export async function deleteTemplate(
  templateId: string
): Promise<{ success: boolean; message: string }> {
  return apiClient.delete(`/workflow/templates/${templateId}`);
}

/**
 * List template categories
 */
export async function listCategories(): Promise<string[]> {
  const response = await apiClient.get<{ categories: string[] }>('/workflow/templates/categories');
  return response.categories;
}
