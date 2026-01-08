use gltf::Gltf;
use memmap2::Mmap;
use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use std::fs::File;
use std::path::Path;
use tauri::command;

/// Result of analyzing a 3D model
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelAnalysis {
    pub vertex_count: usize,
    pub face_count: usize,
    pub mesh_count: usize,
    pub material_count: usize,
    pub has_textures: bool,
    pub has_normals: bool,
    pub has_uvs: bool,
    pub file_size_bytes: u64,
    pub bounding_box: BoundingBox,
    pub center: [f32; 3],
}

/// Axis-aligned bounding box
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct BoundingBox {
    pub min: [f32; 3],
    pub max: [f32; 3],
}

impl BoundingBox {
    pub fn new() -> Self {
        Self {
            min: [f32::MAX, f32::MAX, f32::MAX],
            max: [f32::MIN, f32::MIN, f32::MIN],
        }
    }

    pub fn expand(&mut self, point: [f32; 3]) {
        for i in 0..3 {
            self.min[i] = self.min[i].min(point[i]);
            self.max[i] = self.max[i].max(point[i]);
        }
    }

    pub fn center(&self) -> [f32; 3] {
        [
            (self.min[0] + self.max[0]) / 2.0,
            (self.min[1] + self.max[1]) / 2.0,
            (self.min[2] + self.max[2]) / 2.0,
        ]
    }

    pub fn is_valid(&self) -> bool {
        self.min[0] <= self.max[0] && self.min[1] <= self.max[1] && self.min[2] <= self.max[2]
    }
}

/// Analyze a GLB/GLTF model and return detailed information
#[command]
pub async fn analyze_model(path: String) -> Result<ModelAnalysis, String> {
    let path = Path::new(&path);

    if !path.exists() {
        return Err(format!("File not found: {}", path.display()));
    }

    let file_size_bytes = std::fs::metadata(path)
        .map_err(|e| format!("Failed to get file metadata: {}", e))?
        .len();

    // Memory-map the file for efficient access
    let file = File::open(path).map_err(|e| format!("Failed to open file: {}", e))?;
    let mmap = unsafe { Mmap::map(&file) }.map_err(|e| format!("Failed to mmap file: {}", e))?;

    // Parse GLTF
    let gltf = Gltf::from_slice(&mmap).map_err(|e| format!("Failed to parse GLTF: {}", e))?;

    // Collect mesh statistics in parallel
    let mesh_stats: Vec<MeshStats> = gltf
        .meshes()
        .collect::<Vec<_>>()
        .par_iter()
        .map(|mesh| {
            let mut stats = MeshStats::default();
            for primitive in mesh.primitives() {
                // Count vertices from positions accessor
                if let Some(accessor) = primitive.get(&gltf::Semantic::Positions) {
                    stats.vertex_count += accessor.count();

                    // We can't read the actual buffer data without gltf::import,
                    // but we can estimate bounds from accessor min/max if available
                    if let Some(min) = accessor.min() {
                        if let Some(max) = accessor.max() {
                            let min_vals: Vec<f32> = min.as_array().unwrap()
                                .iter()
                                .filter_map(|v| v.as_f64().map(|f| f as f32))
                                .collect();
                            let max_vals: Vec<f32> = max.as_array().unwrap()
                                .iter()
                                .filter_map(|v| v.as_f64().map(|f| f as f32))
                                .collect();
                            if min_vals.len() >= 3 && max_vals.len() >= 3 {
                                stats.bounds.expand([min_vals[0], min_vals[1], min_vals[2]]);
                                stats.bounds.expand([max_vals[0], max_vals[1], max_vals[2]]);
                            }
                        }
                    }
                }

                // Count faces from indices or vertices
                if let Some(indices) = primitive.indices() {
                    stats.face_count += indices.count() / 3;
                } else {
                    stats.face_count += stats.vertex_count / 3;
                }

                // Check for normals
                if primitive.get(&gltf::Semantic::Normals).is_some() {
                    stats.has_normals = true;
                }

                // Check for UVs
                if primitive.get(&gltf::Semantic::TexCoords(0)).is_some() {
                    stats.has_uvs = true;
                }
            }
            stats
        })
        .collect();

    // Aggregate statistics
    let mut total_vertices = 0;
    let mut total_faces = 0;
    let mut has_normals = false;
    let mut has_uvs = false;
    let mut bounding_box = BoundingBox::new();

    for stats in &mesh_stats {
        total_vertices += stats.vertex_count;
        total_faces += stats.face_count;
        has_normals |= stats.has_normals;
        has_uvs |= stats.has_uvs;
        if stats.bounds.is_valid() {
            bounding_box.expand(stats.bounds.min);
            bounding_box.expand(stats.bounds.max);
        }
    }

    // Check for textures in materials
    let has_textures = gltf.materials().any(|mat| {
        mat.pbr_metallic_roughness().base_color_texture().is_some()
            || mat.pbr_metallic_roughness().metallic_roughness_texture().is_some()
            || mat.normal_texture().is_some()
            || mat.occlusion_texture().is_some()
            || mat.emissive_texture().is_some()
    });

    // Set default bounds if none found
    if !bounding_box.is_valid() {
        bounding_box = BoundingBox {
            min: [-1.0, -1.0, -1.0],
            max: [1.0, 1.0, 1.0],
        };
    }

    let center = bounding_box.center();

    Ok(ModelAnalysis {
        vertex_count: total_vertices,
        face_count: total_faces,
        mesh_count: gltf.meshes().count(),
        material_count: gltf.materials().count(),
        has_textures,
        has_normals,
        has_uvs,
        file_size_bytes,
        bounding_box,
        center,
    })
}

/// Load raw model data as bytes (for streaming to frontend)
#[command]
pub async fn load_model_data(path: String) -> Result<Vec<u8>, String> {
    let path = Path::new(&path);

    if !path.exists() {
        return Err(format!("File not found: {}", path.display()));
    }

    // Memory-map for efficient loading
    let file = File::open(path).map_err(|e| format!("Failed to open file: {}", e))?;
    let mmap = unsafe { Mmap::map(&file) }.map_err(|e| format!("Failed to mmap file: {}", e))?;

    Ok(mmap.to_vec())
}

/// Get just the bounding box of a model (fast operation)
#[command]
pub async fn get_model_bounds(path: String) -> Result<BoundingBox, String> {
    let analysis = analyze_model(path).await?;
    Ok(analysis.bounding_box)
}

#[derive(Default)]
struct MeshStats {
    vertex_count: usize,
    face_count: usize,
    has_normals: bool,
    has_uvs: bool,
    bounds: BoundingBox,
}
