/**
 * LandmarkEditor - Position key landmarks to generate skeleton
 *
 * Instead of editing 45+ individual bones, users position 8 key landmarks
 * and the system generates the full bone chains between them.
 */

import { useState, useCallback, useEffect, useMemo } from 'react';
import { useRiggingStore } from '../../stores/riggingStore';
import { useWorkflowStore } from '../../stores/workflowStore';
import { Spinner } from '../ui/Spinner';

interface LandmarkEditorProps {
  onComplete: () => void;
  onCancel: () => void;
}

interface Landmark {
  name: string;
  position: [number, number, number];
  description: string;
  color: string;
}

interface LandmarkInfo {
  name: string;
  description: string;
  color: string;
  defaultPosition: [number, number, number];
}

// API functions
async function fetchFittedLandmarks(assetId: string, characterType: string): Promise<{
  landmarks: Record<string, [number, number, number]>;
  mesh_bounds: { min: [number, number, number]; max: [number, number, number] };
}> {
  const formData = new FormData();
  formData.append('character_type', characterType);

  const response = await fetch(`/api/rigging/landmarks/fit/${assetId}`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`Failed to fit landmarks: ${response.statusText}`);
  }

  return response.json();
}

async function fetchLandmarkInfo(characterType: string): Promise<LandmarkInfo[]> {
  const response = await fetch(`/api/rigging/landmarks/info/${characterType}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch landmark info: ${response.statusText}`);
  }
  const data = await response.json();
  return data.landmarks;
}

async function applyLandmarksToAsset(
  assetId: string,
  characterType: string,
  landmarks: Record<string, [number, number, number]>
): Promise<{ skeleton: any; bone_count: number }> {
  const formData = new FormData();
  formData.append('character_type', characterType);
  formData.append('landmarks', JSON.stringify(landmarks));

  const response = await fetch(`/api/rigging/landmarks/apply/${assetId}`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Failed to apply landmarks');
  }

  return response.json();
}

export function LandmarkEditor({ onComplete, onCancel }: LandmarkEditorProps) {
  const {
    characterType,
    setSkeletonData,
    setMeshBounds,
    // Sync with store for 3D visualization
    landmarks: storeLandmarks,
    setLandmarks: setStoreLandmarks,
    landmarkInfo: storeLandmarkInfo,
    setLandmarkInfo: setStoreLandmarkInfo,
    selectedLandmark,
    setSelectedLandmark,
  } = useRiggingStore();
  const { activeAssetId } = useWorkflowStore();

  // Use store state for landmarks so 3D visualization can see them
  const landmarks = storeLandmarks;
  const setLandmarks = setStoreLandmarks;
  const [landmarkInfo, setLandmarkInfoLocal] = useState<LandmarkInfo[]>([]);

  // Sync landmark info to store
  const setLandmarkInfo = useCallback((info: LandmarkInfo[]) => {
    setLandmarkInfoLocal(info);
    setStoreLandmarkInfo(info.map(l => ({ name: l.name, color: l.color, description: l.description })));
  }, [setStoreLandmarkInfo]);
  // selectedLandmark comes from store (synced above)
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [meshBoundsData, setMeshBoundsData] = useState<{ min: [number, number, number]; max: [number, number, number] } | null>(null);

  const effectiveType = characterType === 'auto' ? 'quadruped' : characterType;

  // Load fitted landmarks on mount
  useEffect(() => {
    if (!activeAssetId) return;

    const loadData = async () => {
      setIsLoading(true);
      setError(null);

      try {
        // Fetch landmark info and fitted positions in parallel
        const [info, fitted] = await Promise.all([
          fetchLandmarkInfo(effectiveType),
          fetchFittedLandmarks(activeAssetId, effectiveType),
        ]);

        setLandmarkInfo(info);
        setLandmarks(fitted.landmarks);
        setMeshBoundsData(fitted.mesh_bounds);
        setMeshBounds({ min: fitted.mesh_bounds.min, max: fitted.mesh_bounds.max });
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load landmarks');
      } finally {
        setIsLoading(false);
      }
    };

    loadData();
  }, [activeAssetId, effectiveType, setMeshBounds]);

  // Get updateLandmark from store for 3D drag updates
  const { updateLandmark } = useRiggingStore();

  // Handle position input change
  const handlePositionChange = useCallback(
    (name: string, axis: 'x' | 'y' | 'z', value: number) => {
      const current = landmarks[name];
      if (!current) return;

      const newPos: [number, number, number] = [...current];
      const axisIndex = axis === 'x' ? 0 : axis === 'y' ? 1 : 2;
      newPos[axisIndex] = value;

      // Update via store so 3D visualization syncs
      updateLandmark(name, newPos);
    },
    [landmarks, updateLandmark]
  );

  // Apply landmarks and generate skeleton
  const handleApply = useCallback(async () => {
    if (!activeAssetId) return;

    setIsSaving(true);
    setError(null);

    try {
      const result = await applyLandmarksToAsset(activeAssetId, effectiveType, landmarks);

      // Update store with new skeleton
      setSkeletonData({
        rootBone: result.skeleton.root_bone,
        bones: result.skeleton.bones.map((b: any) => ({
          name: b.name,
          parent: b.parent,
          headPosition: b.head_position,
          tailPosition: b.tail_position,
          rotation: b.rotation,
        })),
        characterType: effectiveType as 'humanoid' | 'quadruped',
        boneCount: result.bone_count,
      });

      onComplete();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to apply landmarks');
    } finally {
      setIsSaving(false);
    }
  }, [activeAssetId, effectiveType, landmarks, setSkeletonData, onComplete]);

  // Get landmark color
  const getLandmarkColor = useCallback(
    (name: string): string => {
      const info = landmarkInfo.find((l) => l.name === name);
      return info?.color || '#ffffff';
    },
    [landmarkInfo]
  );

  // Group landmarks by body region
  const landmarkGroups = useMemo(() => {
    const groups: Record<string, string[]> = {
      Body: ['Hips', 'Chest'],
      Head: ['Head'],
      Tail: ['TailTip'],
      'Front Legs': ['FrontLeftPaw', 'FrontRightPaw'],
      'Back Legs': ['BackLeftPaw', 'BackRightPaw'],
    };

    // Filter to only include landmarks that exist
    return Object.fromEntries(
      Object.entries(groups)
        .map(([group, names]) => [group, names.filter((n) => n in landmarks)])
        .filter(([, names]) => (names as string[]).length > 0)
    );
  }, [landmarks]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Spinner size="lg" />
        <span className="ml-3 text-gray-400">Loading landmarks...</span>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-medium text-white">Position Landmarks</h4>
        <span className="text-xs px-2 py-1 bg-purple-900/50 text-purple-400 rounded-full">
          {Object.keys(landmarks).length} landmarks
        </span>
      </div>

      {/* Instructions */}
      <div className="p-3 bg-purple-900/20 border border-purple-700/30 rounded-lg text-sm text-purple-300">
        <p className="font-medium mb-1">How it works:</p>
        <ul className="text-xs text-purple-400 space-y-1 ml-4 list-disc">
          <li>Position the <span className="text-white">8 key landmarks</span> on your model</li>
          <li>The system generates all bones between landmarks automatically</li>
          <li>Much easier than editing 45 individual bones!</li>
        </ul>
      </div>

      {/* Error display */}
      {error && (
        <div className="p-3 bg-red-900/30 border border-red-700/30 rounded text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Landmark groups */}
      <div className="space-y-3">
        {Object.entries(landmarkGroups).map(([group, names]) => (
          <div key={group} className="space-y-2">
            <h5 className="text-xs font-medium text-gray-400 uppercase tracking-wider">{group}</h5>
            <div className="space-y-1">
              {(names as string[]).map((name) => {
                const pos = landmarks[name];
                const info = landmarkInfo.find((l) => l.name === name);
                const isSelected = selectedLandmark === name;

                return (
                  <div
                    key={name}
                    className={`p-2 rounded-lg transition-colors cursor-pointer ${
                      isSelected
                        ? 'bg-purple-900/50 border border-purple-500'
                        : 'bg-gray-800/50 border border-gray-700 hover:border-gray-600'
                    }`}
                    onClick={() => setSelectedLandmark(isSelected ? null : name)}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span
                          className="w-3 h-3 rounded-full"
                          style={{ backgroundColor: getLandmarkColor(name) }}
                        />
                        <span className="text-sm text-white">{name}</span>
                      </div>
                      {info && (
                        <span className="text-xs text-gray-500">{info.description}</span>
                      )}
                    </div>

                    {/* Position controls (expanded when selected) */}
                    {isSelected && pos && (
                      <div className="grid grid-cols-3 gap-2 mt-2">
                        {(['x', 'y', 'z'] as const).map((axis, i) => (
                          <div key={axis}>
                            <label className="text-xs text-gray-500 uppercase">{axis}</label>
                            <input
                              type="number"
                              step="0.01"
                              value={pos[i].toFixed(3)}
                              onChange={(e) =>
                                handlePositionChange(name, axis, parseFloat(e.target.value) || 0)
                              }
                              className="w-full px-2 py-1 text-xs bg-gray-900 border border-gray-700
                                         rounded text-white focus:border-purple-500 focus:outline-none"
                            />
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Mesh bounds info */}
      {meshBoundsData && (
        <div className="p-2 bg-gray-800/30 rounded text-xs text-gray-500">
          Mesh bounds: X[{meshBoundsData.min[0].toFixed(2)}, {meshBoundsData.max[0].toFixed(2)}]
          Y[{meshBoundsData.min[1].toFixed(2)}, {meshBoundsData.max[1].toFixed(2)}]
          Z[{meshBoundsData.min[2].toFixed(2)}, {meshBoundsData.max[2].toFixed(2)}]
        </div>
      )}

      {/* Action buttons */}
      <div className="flex gap-2 pt-2">
        <button
          onClick={onCancel}
          disabled={isSaving}
          className="flex-1 py-2.5 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800
                     text-white font-medium rounded-lg transition-colors"
        >
          Skip Rigging
        </button>
        <button
          onClick={handleApply}
          disabled={isSaving}
          className="flex-1 py-2.5 bg-purple-600 hover:bg-purple-500 disabled:bg-gray-600
                     text-white font-medium rounded-lg transition-colors
                     flex items-center justify-center gap-2"
        >
          {isSaving ? (
            <>
              <Spinner size="sm" variant="white" />
              Generating...
            </>
          ) : (
            <>
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              Generate Skeleton
            </>
          )}
        </button>
      </div>
    </div>
  );
}
