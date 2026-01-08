/**
 * Sweedle Type Definitions
 */

// Generation Types
export type GenerationType = 'image_to_3d' | 'text_to_3d';
export type GenerationMode = 'fast' | 'standard' | 'quality';
export type OutputFormat = 'glb' | 'obj' | 'fbx';

export interface GenerationParameters {
  inferenceSteps: number;
  guidanceScale: number;
  octreeResolution: number;
  seed?: number;
  generateTexture: boolean;
  faceCount?: number;
  outputFormat: OutputFormat;
  mode: GenerationMode;
  removeBackground?: boolean;
  foregroundRatio?: number;
  textureSize?: number;
}

export interface GenerationRequest {
  file?: File;
  prompt?: string;
  name?: string;
  parameters: GenerationParameters;
  projectId?: string;
  tags?: string[];
  priority?: 'low' | 'normal' | 'high';
}

// Job Types
export type JobStatus = 'pending' | 'queued' | 'processing' | 'completed' | 'failed' | 'cancelled';
export type GenerationStage = 'preprocessing' | 'shape-generation' | 'texture-generation' | 'post-processing';

export interface Job {
  id: string;
  assetId?: string;
  type: GenerationType;
  status: JobStatus;
  progress: number;
  stage: string;
  name: string;
  thumbnail?: string;
  error?: string;
  createdAt: string;
  startedAt?: string;
  completedAt?: string;
  priority: 'low' | 'normal' | 'high';
}

export interface GenerationJob {
  id: string;
  type: GenerationType;
  status: JobStatus;
  progress: number;
  stage?: GenerationStage | string;
  name?: string;
  sourceImagePath?: string;
  prompt?: string;
  assetId?: string;
  error?: string;
  eta?: number;
  createdAt: string;
  startedAt?: string;
  completedAt?: string;
}

// Asset Types
export interface Asset {
  id: string;
  name: string;
  description?: string;
  sourceType: GenerationType;
  sourceImagePath?: string;
  sourcePrompt?: string;
  generationParams?: GenerationParameters;
  filePath: string;
  thumbnailPath?: string;
  vertexCount?: number;
  faceCount?: number;
  fileSizeBytes?: number;
  generationTimeSeconds?: number;
  status: string;
  hasLod: boolean;
  lodLevels?: number[];
  isFavorite: boolean;
  rating?: number;
  tags: Tag[];
  createdAt: string;
  updatedAt: string;
}

export interface Tag {
  id: number;
  name: string;
  color: string;
}

export interface Project {
  id: string;
  name: string;
  engineType?: 'unity' | 'unreal' | 'godot';
  engineProjectPath?: string;
  createdAt: string;
}

// Queue Types
export interface QueueStatus {
  queueSize: number;
  currentJobId?: string;
  pendingCount: number;
  processingCount: number;
  completedCount: number;
  failedCount: number;
}

// WebSocket Message Types
export type WSMessageType =
  | 'progress'
  | 'queue_status'
  | 'job_created'
  | 'asset_ready'
  | 'error'
  | 'pong';

export interface WSProgressMessage {
  type: 'progress';
  job_id: string;
  progress: number;
  stage: string;
  status: JobStatus;
  result?: Record<string, unknown>;
  error?: string;
}

export interface WSQueueStatusMessage {
  type: 'queue_status';
  queue_size: number;
  current_job_id?: string;
  pending_count: number;
  processing_count: number;
  completed_count: number;
  failed_count: number;
}

export interface WSJobCreatedMessage {
  type: 'job_created';
  job_id: string;
  asset_id: string;
  job_type: GenerationType;
  queue_position: number;
}

export interface WSAssetReadyMessage {
  type: 'asset_ready';
  asset_id: string;
  name: string;
  thumbnail_url?: string;
  download_url?: string;
}

export interface WSErrorMessage {
  type: 'error';
  code: string;
  message: string;
  job_id?: string;
}

export type WSMessage =
  | WSProgressMessage
  | WSQueueStatusMessage
  | WSJobCreatedMessage
  | WSAssetReadyMessage
  | WSErrorMessage
  | { type: 'pong' };

// Viewer Types
export interface ViewerSettings {
  showWireframe: boolean;
  showGrid: boolean;
  showAxes: boolean;
  autoRotate: boolean;
  backgroundColor: string;
  environmentMap: string;
  exposure: number;
}

// UI Types
export type UIMode = 'simple' | 'advanced';
export type ViewMode = 'grid' | 'list';
export type Panel = 'generation' | 'library' | 'viewer' | 'queue' | 'export';

export interface PanelLayout {
  left: number;
  center: number;
  right: number;
}

// API Response Types
export interface GenerationResponse {
  jobId: string;
  assetId: string;
  status: JobStatus;
  message: string;
  queuePosition?: number;
}

export interface JobStatusResponse {
  jobId: string;
  assetId?: string;
  status: JobStatus;
  progress: number;
  stage: string;
  message?: string;
  error?: string;
  createdAt: string;
  startedAt?: string;
  completedAt?: string;
}

export interface AssetListResponse {
  assets: Asset[];
  total: number;
  page: number;
  pageSize: number;
}

// Export Types
export type EngineType = 'unity' | 'unreal' | 'godot';

export interface ExportOptions {
  engine: EngineType;
  projectPath: string;
  includeTextures: boolean;
  generateLods: boolean;
  lodLevels?: number[];
  compressMesh: boolean;
  format: OutputFormat;
}
