/**
 * MeshToolsPanel - Tools for editing mesh properties
 */

import { useState, useCallback, useEffect } from 'react';
import {
  getMeshInfo,
  smoothMesh,
  repairMesh,
  decimateMesh,
  centerPivot,
  scaleMesh,
  generateCollisionMesh,
  type MeshInfo,
  type CollisionMethod,
  type CollisionMeshInfo,
} from '../../services/api/mesh';

interface MeshToolsPanelProps {
  assetId: string;
  onMeshUpdated?: () => void;
}

export function MeshToolsPanel({ assetId, onMeshUpdated }: MeshToolsPanelProps) {
  const [meshInfo, setMeshInfo] = useState<MeshInfo | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Tool settings
  const [smoothIterations, setSmoothIterations] = useState(1);
  const [smoothLambda, setSmoothLambda] = useState(0.5);
  const [decimateRatio, setDecimateRatio] = useState(0.5);
  const [scaleFactor, setScaleFactor] = useState(1.0);
  const [collisionMethod, setCollisionMethod] = useState<CollisionMethod>('convex_hull');
  const [collisionInfo, setCollisionInfo] = useState<CollisionMeshInfo | null>(null);

  // Load mesh info
  const loadMeshInfo = useCallback(async () => {
    try {
      const info = await getMeshInfo(assetId);
      setMeshInfo(info);
    } catch (err) {
      console.error('Failed to load mesh info:', err);
    }
  }, [assetId]);

  useEffect(() => {
    loadMeshInfo();
  }, [loadMeshInfo]);

  const handleOperation = useCallback(async (
    operation: () => Promise<{ message: string }>,
    operationName: string
  ) => {
    setIsLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const result = await operation();
      setSuccess(result.message);
      loadMeshInfo();
      onMeshUpdated?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : `${operationName} failed`);
    } finally {
      setIsLoading(false);
    }
  }, [loadMeshInfo, onMeshUpdated]);

  const handleSmooth = () => handleOperation(
    () => smoothMesh({ assetId, iterations: smoothIterations, lambdaFactor: smoothLambda }),
    'Smoothing'
  );

  const handleRepair = () => handleOperation(
    () => repairMesh({ assetId }),
    'Repair'
  );

  const handleDecimate = () => handleOperation(
    () => decimateMesh({ assetId, ratio: decimateRatio }),
    'Decimation'
  );

  const handleCenterPivot = () => handleOperation(
    () => centerPivot({ assetId }),
    'Center Pivot'
  );

  const handleScale = () => handleOperation(
    () => scaleMesh({ assetId, scaleFactor }),
    'Scale'
  );

  const handleGenerateCollision = async () => {
    setIsLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const result = await generateCollisionMesh({ assetId, method: collisionMethod });
      setSuccess(result.message);
      if (result.collision) {
        setCollisionInfo(result.collision);
      }
      onMeshUpdated?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Collision generation failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-medium text-white flex items-center gap-2">
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 4a2 2 0 114 0v1a1 1 0 001 1h3a1 1 0 011 1v3a1 1 0 01-1 1h-1a2 2 0 100 4h1a1 1 0 011 1v3a1 1 0 01-1 1h-3a1 1 0 01-1-1v-1a2 2 0 10-4 0v1a1 1 0 01-1 1H7a1 1 0 01-1-1v-3a1 1 0 00-1-1H4a2 2 0 110-4h1a1 1 0 001-1V7a1 1 0 011-1h3a1 1 0 001-1V4z" />
        </svg>
        Mesh Tools
      </h3>

      {/* Mesh Info */}
      {meshInfo && (
        <div className="p-3 bg-gray-800/50 rounded-lg text-sm">
          <div className="grid grid-cols-2 gap-2">
            <div className="text-gray-400">Vertices:</div>
            <div className="text-white">{meshInfo.vertexCount.toLocaleString()}</div>
            <div className="text-gray-400">Faces:</div>
            <div className="text-white">{meshInfo.faceCount.toLocaleString()}</div>
            <div className="text-gray-400">Normals:</div>
            <div className={meshInfo.hasNormals ? 'text-green-400' : 'text-yellow-400'}>
              {meshInfo.hasNormals ? 'Yes' : 'No'}
            </div>
            <div className="text-gray-400">UVs:</div>
            <div className={meshInfo.hasUvs ? 'text-green-400' : 'text-yellow-400'}>
              {meshInfo.hasUvs ? 'Yes' : 'No'}
            </div>
            <div className="text-gray-400">Watertight:</div>
            <div className={meshInfo.isWatertight ? 'text-green-400' : 'text-yellow-400'}>
              {meshInfo.isWatertight ? 'Yes' : 'No'}
            </div>
          </div>
        </div>
      )}

      {/* Status messages */}
      {error && (
        <div className="p-2 bg-red-900/20 border border-red-700/30 rounded text-sm text-red-400">
          {error}
        </div>
      )}
      {success && (
        <div className="p-2 bg-green-900/20 border border-green-700/30 rounded text-sm text-green-400">
          {success}
        </div>
      )}

      {/* Smoothing */}
      <div className="p-3 bg-gray-800/50 rounded-lg">
        <h4 className="text-sm font-medium text-gray-300 mb-2">Smoothing</h4>
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <label className="text-xs text-gray-400 w-20">Iterations:</label>
            <input
              type="range"
              min="1"
              max="10"
              value={smoothIterations}
              onChange={(e) => setSmoothIterations(Number(e.target.value))}
              className="flex-1"
            />
            <span className="text-xs text-white w-6">{smoothIterations}</span>
          </div>
          <div className="flex items-center gap-2">
            <label className="text-xs text-gray-400 w-20">Strength:</label>
            <input
              type="range"
              min="0"
              max="100"
              value={smoothLambda * 100}
              onChange={(e) => setSmoothLambda(Number(e.target.value) / 100)}
              className="flex-1"
            />
            <span className="text-xs text-white w-6">{Math.round(smoothLambda * 100)}%</span>
          </div>
          <button
            onClick={handleSmooth}
            disabled={isLoading}
            className="w-full py-1.5 text-xs font-medium text-white bg-blue-600 hover:bg-blue-500 disabled:bg-gray-600 disabled:cursor-not-allowed rounded transition-colors"
          >
            {isLoading ? 'Processing...' : 'Apply Smoothing'}
          </button>
        </div>
      </div>

      {/* Repair */}
      <div className="p-3 bg-gray-800/50 rounded-lg">
        <h4 className="text-sm font-medium text-gray-300 mb-2">Repair</h4>
        <p className="text-xs text-gray-400 mb-2">
          Fixes holes, normals, and removes degenerate faces.
        </p>
        <button
          onClick={handleRepair}
          disabled={isLoading}
          className="w-full py-1.5 text-xs font-medium text-white bg-orange-600 hover:bg-orange-500 disabled:bg-gray-600 disabled:cursor-not-allowed rounded transition-colors"
        >
          {isLoading ? 'Processing...' : 'Repair Mesh'}
        </button>
      </div>

      {/* Decimation */}
      <div className="p-3 bg-gray-800/50 rounded-lg">
        <h4 className="text-sm font-medium text-gray-300 mb-2">Decimation</h4>
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <label className="text-xs text-gray-400 w-20">Keep:</label>
            <input
              type="range"
              min="10"
              max="100"
              value={decimateRatio * 100}
              onChange={(e) => setDecimateRatio(Number(e.target.value) / 100)}
              className="flex-1"
            />
            <span className="text-xs text-white w-10">{Math.round(decimateRatio * 100)}%</span>
          </div>
          <p className="text-xs text-gray-400">
            Reduce to ~{meshInfo ? Math.round(meshInfo.faceCount * decimateRatio).toLocaleString() : '?'} faces
          </p>
          <button
            onClick={handleDecimate}
            disabled={isLoading}
            className="w-full py-1.5 text-xs font-medium text-white bg-purple-600 hover:bg-purple-500 disabled:bg-gray-600 disabled:cursor-not-allowed rounded transition-colors"
          >
            {isLoading ? 'Processing...' : 'Decimate'}
          </button>
        </div>
      </div>

      {/* Transform */}
      <div className="p-3 bg-gray-800/50 rounded-lg">
        <h4 className="text-sm font-medium text-gray-300 mb-2">Transform</h4>
        <div className="space-y-2">
          <button
            onClick={handleCenterPivot}
            disabled={isLoading}
            className="w-full py-1.5 text-xs font-medium text-white bg-teal-600 hover:bg-teal-500 disabled:bg-gray-600 disabled:cursor-not-allowed rounded transition-colors"
          >
            Center Pivot (Ground at Y=0)
          </button>

          <div className="flex items-center gap-2">
            <label className="text-xs text-gray-400 w-12">Scale:</label>
            <input
              type="number"
              step="0.1"
              min="0.01"
              max="100"
              value={scaleFactor}
              onChange={(e) => setScaleFactor(Number(e.target.value))}
              className="flex-1 px-2 py-1 text-xs bg-gray-700 border border-gray-600 rounded text-white"
            />
            <button
              onClick={handleScale}
              disabled={isLoading}
              className="px-3 py-1 text-xs font-medium text-white bg-teal-600 hover:bg-teal-500 disabled:bg-gray-600 disabled:cursor-not-allowed rounded transition-colors"
            >
              Apply
            </button>
          </div>
        </div>
      </div>

      {/* Collision Mesh */}
      <div className="p-3 bg-gray-800/50 rounded-lg">
        <h4 className="text-sm font-medium text-gray-300 mb-2">Collision Mesh</h4>
        <p className="text-xs text-gray-400 mb-2">
          Generate optimized collision geometry for physics engines.
        </p>
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <label className="text-xs text-gray-400 w-16">Method:</label>
            <select
              value={collisionMethod}
              onChange={(e) => setCollisionMethod(e.target.value as CollisionMethod)}
              className="flex-1 px-2 py-1 text-xs bg-gray-700 border border-gray-600 rounded text-white"
            >
              <option value="convex_hull">Convex Hull</option>
              <option value="simplified">Simplified</option>
              <option value="box">Bounding Box</option>
              <option value="capsule">Capsule</option>
              <option value="sphere">Sphere</option>
            </select>
          </div>
          <div className="text-xs text-gray-500">
            {collisionMethod === 'convex_hull' && 'Wraps mesh in convex shape - good for most objects'}
            {collisionMethod === 'simplified' && 'Simplified version of original - good for complex shapes'}
            {collisionMethod === 'box' && 'Axis-aligned bounding box - fastest but least accurate'}
            {collisionMethod === 'capsule' && 'Cylinder with rounded ends - good for characters'}
            {collisionMethod === 'sphere' && 'Simple sphere collider - good for balls/round objects'}
          </div>
          <button
            onClick={handleGenerateCollision}
            disabled={isLoading}
            className="w-full py-1.5 text-xs font-medium text-white bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-600 disabled:cursor-not-allowed rounded transition-colors"
          >
            {isLoading ? 'Generating...' : 'Generate Collision'}
          </button>
          {collisionInfo && (
            <div className="mt-2 p-2 bg-gray-900/50 rounded text-xs">
              <div className="flex justify-between">
                <span className="text-gray-400">Type:</span>
                <span className="text-white capitalize">{collisionInfo.method.replace('_', ' ')}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Vertices:</span>
                <span className="text-white">{collisionInfo.vertexCount.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Faces:</span>
                <span className="text-white">{collisionInfo.faceCount.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Size:</span>
                <span className="text-white">{(collisionInfo.fileSizeBytes / 1024).toFixed(1)} KB</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Refresh button */}
      <button
        onClick={loadMeshInfo}
        className="w-full py-1.5 text-xs font-medium text-gray-300 bg-gray-700 hover:bg-gray-600 rounded transition-colors flex items-center justify-center gap-1"
      >
        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        Refresh Info
      </button>
    </div>
  );
}
