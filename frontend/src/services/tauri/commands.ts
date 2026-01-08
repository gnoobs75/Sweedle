/**
 * Tauri Command Wrappers
 *
 * Provides typed interfaces for calling Rust backend commands.
 * These commands offer native performance for heavy file/mesh operations.
 */

// Check if running in Tauri environment
export const isTauri = (): boolean => {
  return typeof window !== 'undefined' && '__TAURI__' in window;
};

// Types matching Rust structs
export interface ModelAnalysis {
  vertex_count: number;
  face_count: number;
  mesh_count: number;
  material_count: number;
  has_textures: boolean;
  has_normals: boolean;
  has_uvs: boolean;
  file_size_bytes: number;
  bounding_box: BoundingBox;
  center: [number, number, number];
}

export interface BoundingBox {
  min: [number, number, number];
  max: [number, number, number];
}

export interface LodResult {
  original_vertex_count: number;
  original_face_count: number;
  levels: LodLevel[];
}

export interface LodLevel {
  level: number;
  vertex_count: number;
  face_count: number;
  reduction_ratio: number;
}

export interface MeshStats {
  vertex_count: number;
  face_count: number;
  edge_count: number;
  is_manifold: boolean;
  has_degenerate_faces: boolean;
  surface_area: number;
  volume: number;
}

export interface OptimizedMeshResult {
  original_vertex_count: number;
  optimized_vertex_count: number;
  cache_hits_before: number;
  cache_hits_after: number;
  overdraw_before: number;
  overdraw_after: number;
}

export interface FileInfo {
  path: string;
  name: string;
  extension: string | null;
  size_bytes: number;
  created: number | null;
  modified: number | null;
  is_directory: boolean;
}

export interface StorageAsset {
  id: string;
  path: string;
  has_glb: boolean;
  has_obj: boolean;
  has_fbx: boolean;
  has_thumbnail: boolean;
  glb_size: number | null;
  thumbnail_path: string | null;
}

// Dynamic import for Tauri API (only available in Tauri environment)
async function invoke<T>(command: string, args?: Record<string, unknown>): Promise<T> {
  if (!isTauri()) {
    throw new Error('Tauri commands are only available in the Tauri environment');
  }

  // Dynamic import to avoid errors in browser environment
  const { invoke: tauriInvoke } = await import('@tauri-apps/api/core');
  return tauriInvoke<T>(command, args);
}

/**
 * Model Loading Commands
 */
export const modelCommands = {
  /**
   * Analyze a 3D model and return detailed statistics
   * Uses native Rust for 10x+ faster analysis than JavaScript
   */
  analyzeModel: async (path: string): Promise<ModelAnalysis> => {
    return invoke<ModelAnalysis>('analyze_model', { path });
  },

  /**
   * Load raw model data as bytes
   * Uses memory-mapped files for efficient streaming
   */
  loadModelData: async (path: string): Promise<Uint8Array> => {
    const data = await invoke<number[]>('load_model_data', { path });
    return new Uint8Array(data);
  },

  /**
   * Get just the bounding box of a model (fast operation)
   */
  getModelBounds: async (path: string): Promise<BoundingBox> => {
    return invoke<BoundingBox>('get_model_bounds', { path });
  },
};

/**
 * Mesh Processing Commands
 */
export const meshCommands = {
  /**
   * Generate LOD (Level of Detail) versions of a mesh
   * Uses native meshoptimizer for high-quality decimation
   */
  generateLod: async (
    vertices: Float32Array,
    indices: Uint32Array,
    targetRatios: number[]
  ): Promise<LodResult> => {
    return invoke<LodResult>('generate_lod', {
      vertices: Array.from(vertices),
      indices: Array.from(indices),
      target_ratios: targetRatios,
    });
  },

  /**
   * Optimize mesh for GPU rendering
   * Performs vertex cache and overdraw optimization
   */
  optimizeMesh: async (
    vertices: Float32Array,
    indices: Uint32Array
  ): Promise<OptimizedMeshResult> => {
    return invoke<OptimizedMeshResult>('optimize_mesh', {
      vertices: Array.from(vertices),
      indices: Array.from(indices),
    });
  },

  /**
   * Calculate detailed mesh statistics
   */
  calculateMeshStats: async (
    vertices: Float32Array,
    indices: Uint32Array
  ): Promise<MeshStats> => {
    return invoke<MeshStats>('calculate_mesh_stats', {
      vertices: Array.from(vertices),
      indices: Array.from(indices),
    });
  },
};

/**
 * File Operation Commands
 */
export const fileCommands = {
  /**
   * Read file in chunks (for streaming large files)
   */
  readFileChunked: async (
    path: string,
    offset?: number,
    length?: number
  ): Promise<Uint8Array> => {
    const data = await invoke<number[]>('read_file_chunked', {
      path,
      offset,
      length,
    });
    return new Uint8Array(data);
  },

  /**
   * Get detailed information about a file
   */
  getFileInfo: async (path: string): Promise<FileInfo> => {
    return invoke<FileInfo>('get_file_info', { path });
  },

  /**
   * List all assets in the storage directory
   */
  listStorageAssets: async (storagePath: string): Promise<StorageAsset[]> => {
    return invoke<StorageAsset[]>('list_storage_assets', {
      storage_path: storagePath,
    });
  },

  /**
   * Watch a directory and get current file list
   */
  watchDirectory: async (path: string): Promise<FileInfo[]> => {
    return invoke<FileInfo[]>('watch_directory', { path });
  },
};

/**
 * Combined Tauri commands export
 */
export const tauriCommands = {
  ...modelCommands,
  ...meshCommands,
  ...fileCommands,
  isTauri,
};

export default tauriCommands;
