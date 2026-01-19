/**
 * Mesh utilities for bone snapping and surface projection
 */

import * as THREE from 'three';

/**
 * Find the nearest point on a mesh surface to a given position
 */
export function findNearestPointOnMesh(
  mesh: THREE.Mesh,
  position: THREE.Vector3
): THREE.Vector3 | null {
  const geometry = mesh.geometry;
  if (!geometry) return null;

  // Ensure we have position attribute
  const positionAttr = geometry.getAttribute('position');
  if (!positionAttr) return null;

  let nearestPoint: THREE.Vector3 | null = null;
  let nearestDistance = Infinity;

  // Get world matrix for transforming vertices
  mesh.updateMatrixWorld();
  const worldMatrix = mesh.matrixWorld;

  // Check each triangle
  const index = geometry.index;
  const vertices: THREE.Vector3[] = [];

  // Extract all vertices in world space
  for (let i = 0; i < positionAttr.count; i++) {
    const vertex = new THREE.Vector3(
      positionAttr.getX(i),
      positionAttr.getY(i),
      positionAttr.getZ(i)
    );
    vertex.applyMatrix4(worldMatrix);
    vertices.push(vertex);
  }

  // If indexed geometry, iterate through triangles
  if (index) {
    for (let i = 0; i < index.count; i += 3) {
      const a = vertices[index.getX(i)];
      const b = vertices[index.getX(i + 1)];
      const c = vertices[index.getX(i + 2)];

      const closestPoint = closestPointOnTriangle(position, a, b, c);
      const distance = position.distanceTo(closestPoint);

      if (distance < nearestDistance) {
        nearestDistance = distance;
        nearestPoint = closestPoint.clone();
      }
    }
  } else {
    // Non-indexed geometry
    for (let i = 0; i < vertices.length; i += 3) {
      const a = vertices[i];
      const b = vertices[i + 1];
      const c = vertices[i + 2];

      if (!a || !b || !c) continue;

      const closestPoint = closestPointOnTriangle(position, a, b, c);
      const distance = position.distanceTo(closestPoint);

      if (distance < nearestDistance) {
        nearestDistance = distance;
        nearestPoint = closestPoint.clone();
      }
    }
  }

  return nearestPoint;
}

/**
 * Find the closest point on a triangle to a given point
 */
function closestPointOnTriangle(
  p: THREE.Vector3,
  a: THREE.Vector3,
  b: THREE.Vector3,
  c: THREE.Vector3
): THREE.Vector3 {
  const ab = new THREE.Vector3().subVectors(b, a);
  const ac = new THREE.Vector3().subVectors(c, a);
  const ap = new THREE.Vector3().subVectors(p, a);

  const d1 = ab.dot(ap);
  const d2 = ac.dot(ap);

  // Check if point is in vertex region outside A
  if (d1 <= 0 && d2 <= 0) return a.clone();

  const bp = new THREE.Vector3().subVectors(p, b);
  const d3 = ab.dot(bp);
  const d4 = ac.dot(bp);

  // Check if point is in vertex region outside B
  if (d3 >= 0 && d4 <= d3) return b.clone();

  // Check if point is in edge region AB
  const vc = d1 * d4 - d3 * d2;
  if (vc <= 0 && d1 >= 0 && d3 <= 0) {
    const v = d1 / (d1 - d3);
    return a.clone().add(ab.multiplyScalar(v));
  }

  const cp = new THREE.Vector3().subVectors(p, c);
  const d5 = ab.dot(cp);
  const d6 = ac.dot(cp);

  // Check if point is in vertex region outside C
  if (d6 >= 0 && d5 <= d6) return c.clone();

  // Check if point is in edge region AC
  const vb = d5 * d2 - d1 * d6;
  if (vb <= 0 && d2 >= 0 && d6 <= 0) {
    const w = d2 / (d2 - d6);
    return a.clone().add(ac.multiplyScalar(w));
  }

  // Check if point is in edge region BC
  const va = d3 * d6 - d5 * d4;
  if (va <= 0 && d4 - d3 >= 0 && d5 - d6 >= 0) {
    const w = (d4 - d3) / (d4 - d3 + (d5 - d6));
    return b.clone().add(new THREE.Vector3().subVectors(c, b).multiplyScalar(w));
  }

  // Point is inside triangle
  const denom = 1 / (va + vb + vc);
  const v = vb * denom;
  const w = vc * denom;

  return a
    .clone()
    .add(ab.multiplyScalar(v))
    .add(new THREE.Vector3().subVectors(c, a).multiplyScalar(w));
}

/**
 * Project a point onto the mesh surface along a direction (usually -Y for dropping onto ground)
 */
export function projectPointOntoMesh(
  mesh: THREE.Mesh,
  position: THREE.Vector3,
  direction: THREE.Vector3 = new THREE.Vector3(0, -1, 0)
): THREE.Vector3 | null {
  const raycaster = new THREE.Raycaster(position, direction.normalize());
  const intersects = raycaster.intersectObject(mesh, true);

  if (intersects.length > 0) {
    return intersects[0].point.clone();
  }

  // Try opposite direction if no hit
  raycaster.set(position, direction.negate());
  const reverseIntersects = raycaster.intersectObject(mesh, true);

  if (reverseIntersects.length > 0) {
    return reverseIntersects[0].point.clone();
  }

  return null;
}

/**
 * Get the bounding box of a mesh in world coordinates
 */
export function getMeshBounds(mesh: THREE.Mesh): THREE.Box3 {
  const box = new THREE.Box3();
  mesh.updateMatrixWorld();
  box.setFromObject(mesh);
  return box;
}
