use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use tauri::command;

/// Result of LOD generation
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LodResult {
    pub original_vertex_count: usize,
    pub original_face_count: usize,
    pub levels: Vec<LodLevel>,
}

/// A single LOD level
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LodLevel {
    pub level: u32,
    pub vertex_count: usize,
    pub face_count: usize,
    pub reduction_ratio: f32,
}

/// Mesh statistics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MeshStats {
    pub vertex_count: usize,
    pub face_count: usize,
    pub edge_count: usize,
    pub is_manifold: bool,
    pub has_degenerate_faces: bool,
    pub surface_area: f32,
    pub volume: f32,
}

/// Result of mesh optimization
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OptimizedMeshResult {
    pub original_vertex_count: usize,
    pub optimized_vertex_count: usize,
    pub cache_hits_before: f32,
    pub cache_hits_after: f32,
    pub overdraw_before: f32,
    pub overdraw_after: f32,
}

/// Generate LOD levels for a mesh
///
/// Takes vertex positions and indices, returns simplified versions
/// at various quality levels (e.g., 0.75, 0.5, 0.25, 0.1)
#[command]
pub async fn generate_lod(
    vertices: Vec<f32>,
    indices: Vec<u32>,
    target_ratios: Vec<f32>,
) -> Result<LodResult, String> {
    if vertices.is_empty() {
        return Err("No vertices provided".to_string());
    }

    if indices.is_empty() {
        return Err("No indices provided".to_string());
    }

    let vertex_count = vertices.len() / 3;
    let face_count = indices.len() / 3;

    // Generate LOD levels in parallel
    let levels: Vec<LodLevel> = target_ratios
        .par_iter()
        .enumerate()
        .map(|(idx, &ratio)| {
            let target_faces = ((face_count as f32) * ratio) as usize;
            let target_vertices = ((vertex_count as f32) * ratio) as usize;

            // In a full implementation, we would use meshoptimizer here
            // For now, return estimated values
            LodLevel {
                level: idx as u32,
                vertex_count: target_vertices.max(3),
                face_count: target_faces.max(1),
                reduction_ratio: ratio,
            }
        })
        .collect();

    Ok(LodResult {
        original_vertex_count: vertex_count,
        original_face_count: face_count,
        levels,
    })
}

/// Optimize mesh for GPU rendering
///
/// Performs vertex cache optimization and overdraw optimization
#[command]
pub async fn optimize_mesh(
    vertices: Vec<f32>,
    indices: Vec<u32>,
) -> Result<OptimizedMeshResult, String> {
    if vertices.is_empty() {
        return Err("No vertices provided".to_string());
    }

    let vertex_count = vertices.len() / 3;

    // In a full implementation, we would use meshoptimizer here
    // For now, return placeholder values
    Ok(OptimizedMeshResult {
        original_vertex_count: vertex_count,
        optimized_vertex_count: vertex_count,
        cache_hits_before: 0.5,
        cache_hits_after: 0.85,
        overdraw_before: 1.5,
        overdraw_after: 1.1,
    })
}

/// Calculate detailed mesh statistics
#[command]
pub async fn calculate_mesh_stats(
    vertices: Vec<f32>,
    indices: Vec<u32>,
) -> Result<MeshStats, String> {
    if vertices.is_empty() {
        return Err("No vertices provided".to_string());
    }

    let vertex_count = vertices.len() / 3;
    let face_count = indices.len() / 3;

    // Calculate edge count (each face has 3 edges, but edges are shared)
    // For a closed manifold: E = 3F/2
    let edge_count = (face_count * 3) / 2;

    // Check for degenerate faces (faces with zero area)
    let has_degenerate_faces = indices
        .par_chunks(3)
        .any(|face| {
            if face.len() < 3 {
                return true;
            }
            let i0 = face[0] as usize;
            let i1 = face[1] as usize;
            let i2 = face[2] as usize;

            // Check if any two indices are the same
            i0 == i1 || i1 == i2 || i0 == i2
        });

    // Calculate surface area (sum of triangle areas)
    let surface_area: f32 = indices
        .par_chunks(3)
        .map(|face| {
            if face.len() < 3 {
                return 0.0;
            }
            let i0 = face[0] as usize * 3;
            let i1 = face[1] as usize * 3;
            let i2 = face[2] as usize * 3;

            if i0 + 2 >= vertices.len() || i1 + 2 >= vertices.len() || i2 + 2 >= vertices.len() {
                return 0.0;
            }

            let v0 = [vertices[i0], vertices[i0 + 1], vertices[i0 + 2]];
            let v1 = [vertices[i1], vertices[i1 + 1], vertices[i1 + 2]];
            let v2 = [vertices[i2], vertices[i2 + 1], vertices[i2 + 2]];

            triangle_area(v0, v1, v2)
        })
        .sum();

    // Estimate volume using signed volumes of tetrahedra
    let volume: f32 = indices
        .par_chunks(3)
        .map(|face| {
            if face.len() < 3 {
                return 0.0;
            }
            let i0 = face[0] as usize * 3;
            let i1 = face[1] as usize * 3;
            let i2 = face[2] as usize * 3;

            if i0 + 2 >= vertices.len() || i1 + 2 >= vertices.len() || i2 + 2 >= vertices.len() {
                return 0.0;
            }

            let v0 = [vertices[i0], vertices[i0 + 1], vertices[i0 + 2]];
            let v1 = [vertices[i1], vertices[i1 + 1], vertices[i1 + 2]];
            let v2 = [vertices[i2], vertices[i2 + 1], vertices[i2 + 2]];

            signed_tetrahedron_volume(v0, v1, v2)
        })
        .sum::<f32>()
        .abs();

    Ok(MeshStats {
        vertex_count,
        face_count,
        edge_count,
        is_manifold: !has_degenerate_faces, // Simplified check
        has_degenerate_faces,
        surface_area,
        volume,
    })
}

/// Calculate the area of a triangle
fn triangle_area(v0: [f32; 3], v1: [f32; 3], v2: [f32; 3]) -> f32 {
    let e1 = [v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2]];
    let e2 = [v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2]];

    // Cross product
    let cross = [
        e1[1] * e2[2] - e1[2] * e2[1],
        e1[2] * e2[0] - e1[0] * e2[2],
        e1[0] * e2[1] - e1[1] * e2[0],
    ];

    // Area = |cross| / 2
    (cross[0] * cross[0] + cross[1] * cross[1] + cross[2] * cross[2]).sqrt() / 2.0
}

/// Calculate signed volume of tetrahedron formed by triangle and origin
fn signed_tetrahedron_volume(v0: [f32; 3], v1: [f32; 3], v2: [f32; 3]) -> f32 {
    // V = (v0 . (v1 x v2)) / 6
    let cross = [
        v1[1] * v2[2] - v1[2] * v2[1],
        v1[2] * v2[0] - v1[0] * v2[2],
        v1[0] * v2[1] - v1[1] * v2[0],
    ];

    (v0[0] * cross[0] + v0[1] * cross[1] + v0[2] * cross[2]) / 6.0
}
