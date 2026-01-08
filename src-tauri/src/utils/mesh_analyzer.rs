use rayon::prelude::*;

/// Analyze mesh topology and return statistics
pub struct MeshAnalyzer {
    vertices: Vec<f32>,
    indices: Vec<u32>,
}

impl MeshAnalyzer {
    pub fn new(vertices: Vec<f32>, indices: Vec<u32>) -> Self {
        Self { vertices, indices }
    }

    /// Count unique vertices (removing duplicates within epsilon)
    pub fn count_unique_vertices(&self, epsilon: f32) -> usize {
        if self.vertices.is_empty() {
            return 0;
        }

        let vertex_count = self.vertices.len() / 3;
        let epsilon_sq = epsilon * epsilon;

        // Simple O(n^2) duplicate detection - could be optimized with spatial hashing
        let mut unique_count = 0;
        let mut is_duplicate = vec![false; vertex_count];

        for i in 0..vertex_count {
            if is_duplicate[i] {
                continue;
            }

            unique_count += 1;
            let vi = [
                self.vertices[i * 3],
                self.vertices[i * 3 + 1],
                self.vertices[i * 3 + 2],
            ];

            for j in (i + 1)..vertex_count {
                if is_duplicate[j] {
                    continue;
                }

                let vj = [
                    self.vertices[j * 3],
                    self.vertices[j * 3 + 1],
                    self.vertices[j * 3 + 2],
                ];

                let dist_sq = (vi[0] - vj[0]).powi(2)
                    + (vi[1] - vj[1]).powi(2)
                    + (vi[2] - vj[2]).powi(2);

                if dist_sq < epsilon_sq {
                    is_duplicate[j] = true;
                }
            }
        }

        unique_count
    }

    /// Calculate the bounding box of the mesh
    pub fn calculate_bounds(&self) -> ([f32; 3], [f32; 3]) {
        if self.vertices.is_empty() {
            return ([0.0; 3], [0.0; 3]);
        }

        let vertex_count = self.vertices.len() / 3;

        // Parallel min/max calculation
        let (min, max) = (0..vertex_count)
            .into_par_iter()
            .map(|i| {
                let v = [
                    self.vertices[i * 3],
                    self.vertices[i * 3 + 1],
                    self.vertices[i * 3 + 2],
                ];
                (v, v)
            })
            .reduce(
                || {
                    (
                        [f32::MAX, f32::MAX, f32::MAX],
                        [f32::MIN, f32::MIN, f32::MIN],
                    )
                },
                |(min_a, max_a), (min_b, max_b)| {
                    (
                        [
                            min_a[0].min(min_b[0]),
                            min_a[1].min(min_b[1]),
                            min_a[2].min(min_b[2]),
                        ],
                        [
                            max_a[0].max(max_b[0]),
                            max_a[1].max(max_b[1]),
                            max_a[2].max(max_b[2]),
                        ],
                    )
                },
            );

        (min, max)
    }

    /// Find connected components in the mesh
    pub fn count_connected_components(&self) -> usize {
        if self.indices.is_empty() {
            return 0;
        }

        let vertex_count = self.vertices.len() / 3;
        let mut parent: Vec<usize> = (0..vertex_count).collect();

        fn find(parent: &mut [usize], i: usize) -> usize {
            if parent[i] != i {
                parent[i] = find(parent, parent[i]);
            }
            parent[i]
        }

        fn union(parent: &mut [usize], i: usize, j: usize) {
            let pi = find(parent, i);
            let pj = find(parent, j);
            if pi != pj {
                parent[pi] = pj;
            }
        }

        // Union-find on face connectivity
        for face in self.indices.chunks(3) {
            if face.len() < 3 {
                continue;
            }
            let i0 = face[0] as usize;
            let i1 = face[1] as usize;
            let i2 = face[2] as usize;

            if i0 < vertex_count && i1 < vertex_count && i2 < vertex_count {
                union(&mut parent, i0, i1);
                union(&mut parent, i1, i2);
            }
        }

        // Count unique roots
        let mut roots = std::collections::HashSet::new();
        for i in 0..vertex_count {
            roots.insert(find(&mut parent, i));
        }

        roots.len()
    }

    /// Check if mesh is watertight (closed)
    pub fn is_watertight(&self) -> bool {
        if self.indices.is_empty() {
            return false;
        }

        use std::collections::HashMap;

        // Count edge occurrences
        let mut edge_count: HashMap<(u32, u32), i32> = HashMap::new();

        for face in self.indices.chunks(3) {
            if face.len() < 3 {
                continue;
            }

            // For a watertight mesh, each edge should appear exactly twice
            // with opposite orientations
            let edges = [
                (face[0], face[1]),
                (face[1], face[2]),
                (face[2], face[0]),
            ];

            for (a, b) in edges {
                // Normalize edge direction for counting
                let key = if a < b { (a, b) } else { (b, a) };
                *edge_count.entry(key).or_insert(0) += 1;
            }
        }

        // Check all edges appear exactly twice
        edge_count.values().all(|&count| count == 2)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_bounds_calculation() {
        let vertices = vec![
            0.0, 0.0, 0.0, // v0
            1.0, 0.0, 0.0, // v1
            0.0, 1.0, 0.0, // v2
        ];
        let indices = vec![0, 1, 2];

        let analyzer = MeshAnalyzer::new(vertices, indices);
        let (min, max) = analyzer.calculate_bounds();

        assert_eq!(min, [0.0, 0.0, 0.0]);
        assert_eq!(max, [1.0, 1.0, 0.0]);
    }
}
