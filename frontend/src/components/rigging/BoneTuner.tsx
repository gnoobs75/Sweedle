/**
 * BoneTuner - Intuitive bone position tuning for beginners
 *
 * Shows after auto-rigging to let users fix any misplaced bones
 * with drag controls and quick position presets.
 */

import { useState, useCallback, useMemo } from 'react';
import { useRiggingStore } from '../../stores/riggingStore';
import { useWorkflowStore } from '../../stores/workflowStore';
import { Spinner } from '../ui/Spinner';
import { updateSkeleton } from '../../services/api/rigging';

interface BoneTunerProps {
  onComplete: () => void;
  onCancel: () => void;
}

type EditMode = 'select' | 'drag';

// Quick position presets for common bone fixes
interface QuickPosition {
  name: string;
  description: string;
  icon: string;
  getPosition: (meshBounds: { min: [number, number, number]; max: [number, number, number] }) => {
    head: [number, number, number];
    tail: [number, number, number];
  };
}

export function BoneTuner({ onComplete, onCancel }: BoneTunerProps) {
  const {
    skeletonData,
    selectedBone,
    setSelectedBone,
    floatingBones,
    editedBones,
    updateBonePosition,
    applyEdits,
    revertEdits,
    meshBounds,
    setDragMode,
    dragMode,
    requestSnapToMesh,
  } = useRiggingStore();

  const { activeAssetId } = useWorkflowStore();
  const [isFixing, setIsFixing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [editMode, setEditMode] = useState<EditMode>('select');
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Quick position presets for the selected bone
  const quickPositions = useMemo<QuickPosition[]>(() => {
    if (!meshBounds) return [];

    const { min, max } = meshBounds;
    const center = [
      (min[0] + max[0]) / 2,
      (min[1] + max[1]) / 2,
      (min[2] + max[2]) / 2,
    ] as [number, number, number];
    const size = [max[0] - min[0], max[1] - min[1], max[2] - min[2]];

    return [
      {
        name: 'Back',
        description: 'Move to rear of model',
        icon: '⬅️',
        getPosition: () => ({
          head: [center[0], center[1], max[2] - size[2] * 0.1],
          tail: [center[0], center[1] - size[1] * 0.1, max[2]],
        }),
      },
      {
        name: 'Front',
        description: 'Move to front of model',
        icon: '➡️',
        getPosition: () => ({
          head: [center[0], center[1], min[2] + size[2] * 0.1],
          tail: [center[0], center[1] - size[1] * 0.1, min[2]],
        }),
      },
      {
        name: 'Top',
        description: 'Move to top of model',
        icon: '⬆️',
        getPosition: () => ({
          head: [center[0], max[1] - size[1] * 0.1, center[2]],
          tail: [center[0], max[1], center[2]],
        }),
      },
      {
        name: 'Center',
        description: 'Move to center',
        icon: '⊙',
        getPosition: () => ({
          head: center,
          tail: [center[0], center[1] + size[1] * 0.1, center[2]],
        }),
      },
    ];
  }, [meshBounds]);

  // Apply quick position to selected bone
  const applyQuickPosition = useCallback(
    (preset: QuickPosition) => {
      if (!selectedBone || !meshBounds) return;
      const { head, tail } = preset.getPosition(meshBounds);
      updateBonePosition(selectedBone, head, tail);
    },
    [selectedBone, meshBounds, updateBonePosition]
  );

  // Snap selected bone to mesh surface
  const handleSnapToMesh = useCallback(
    (target: 'head' | 'tail' | 'both') => {
      if (!selectedBone) return;
      requestSnapToMesh(selectedBone, target);
    },
    [selectedBone, requestSnapToMesh]
  );

  // Get current bone data (edited or original)
  const getBoneData = useCallback(
    (boneName: string) => {
      const edit = editedBones.get(boneName);
      if (edit) {
        return { head: edit.headPosition, tail: edit.tailPosition };
      }
      const bone = skeletonData?.bones.find((b) => b.name === boneName);
      if (bone) {
        return { head: bone.headPosition, tail: bone.tailPosition };
      }
      return null;
    },
    [editedBones, skeletonData]
  );

  // Check if a bone is outside mesh bounds
  const isBoneFloating = useCallback(
    (boneName: string): boolean => {
      return floatingBones.includes(boneName);
    },
    [floatingBones]
  );

  // Handle position change for selected bone
  const handlePositionChange = useCallback(
    (axis: 'x' | 'y' | 'z', value: number, isHead: boolean) => {
      if (!selectedBone) return;

      const current = getBoneData(selectedBone);
      if (!current) return;

      const axisIndex = axis === 'x' ? 0 : axis === 'y' ? 1 : 2;
      const newHead = [...current.head] as [number, number, number];
      const newTail = [...current.tail] as [number, number, number];

      if (isHead) {
        newHead[axisIndex] = value;
      } else {
        newTail[axisIndex] = value;
      }

      updateBonePosition(selectedBone, newHead, newTail);
    },
    [selectedBone, getBoneData, updateBonePosition]
  );

  // Auto-fix floating bones by clamping to mesh bounds
  const handleFixFloating = useCallback(async () => {
    if (!skeletonData || !meshBounds) return;

    setIsFixing(true);

    // Small delay for UX
    await new Promise((resolve) => setTimeout(resolve, 300));

    const margin = 0.05; // 5% margin inside bounds
    const boundsSize = [
      meshBounds.max[0] - meshBounds.min[0],
      meshBounds.max[1] - meshBounds.min[1],
      meshBounds.max[2] - meshBounds.min[2],
    ];

    const clamp = (val: number, min: number, max: number) =>
      Math.max(min, Math.min(max, val));

    // Fix each floating bone
    for (const boneName of floatingBones) {
      const current = getBoneData(boneName);
      if (!current) continue;

      const newHead: [number, number, number] = [
        clamp(
          current.head[0],
          meshBounds.min[0] + boundsSize[0] * margin,
          meshBounds.max[0] - boundsSize[0] * margin
        ),
        clamp(
          current.head[1],
          meshBounds.min[1] + boundsSize[1] * margin,
          meshBounds.max[1] - boundsSize[1] * margin
        ),
        clamp(
          current.head[2],
          meshBounds.min[2] + boundsSize[2] * margin,
          meshBounds.max[2] - boundsSize[2] * margin
        ),
      ];

      const newTail: [number, number, number] = [
        clamp(
          current.tail[0],
          meshBounds.min[0] + boundsSize[0] * margin,
          meshBounds.max[0] - boundsSize[0] * margin
        ),
        clamp(
          current.tail[1],
          meshBounds.min[1] + boundsSize[1] * margin,
          meshBounds.max[1] - boundsSize[1] * margin
        ),
        clamp(
          current.tail[2],
          meshBounds.min[2] + boundsSize[2] * margin,
          meshBounds.max[2] - boundsSize[2] * margin
        ),
      ];

      updateBonePosition(boneName, newHead, newTail);
    }

    setIsFixing(false);
  }, [skeletonData, meshBounds, floatingBones, getBoneData, updateBonePosition]);

  // Apply edits and complete
  const handleComplete = useCallback(async () => {
    // If there are edits, save them to the backend first
    if (editedBones.size > 0 && activeAssetId) {
      setIsSaving(true);
      setSaveError(null);

      try {
        const edits = Array.from(editedBones.values()).map((edit) => ({
          boneName: edit.boneName,
          headPosition: edit.headPosition,
          tailPosition: edit.tailPosition,
        }));

        await updateSkeleton(activeAssetId, edits);
      } catch (error) {
        console.error('Failed to save skeleton edits:', error);
        setSaveError('Failed to save changes. Continuing anyway...');
        // Continue even if save fails - local changes still apply
      } finally {
        setIsSaving(false);
      }
    }

    applyEdits();
    onComplete();
  }, [applyEdits, onComplete, editedBones, activeAssetId]);

  // Cancel and revert
  const handleCancel = useCallback(() => {
    revertEdits();
    onCancel();
  }, [revertEdits, onCancel]);

  const selectedBoneData = selectedBone ? getBoneData(selectedBone) : null;
  const hasFloatingBones = floatingBones.length > 0;
  const hasEdits = editedBones.size > 0;

  return (
    <div className="space-y-4">
      {/* Header with status */}
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-medium text-white">Tune Skeleton</h4>
        {hasFloatingBones ? (
          <span className="text-xs px-2 py-1 bg-red-900/50 text-red-400 rounded-full">
            {floatingBones.length} bone{floatingBones.length > 1 ? 's' : ''} outside mesh
          </span>
        ) : (
          <span className="text-xs px-2 py-1 bg-green-900/50 text-green-400 rounded-full">
            All bones OK
          </span>
        )}
      </div>

      {/* Instructions */}
      <div className="p-3 bg-blue-900/20 border border-blue-700/30 rounded-lg text-sm text-blue-300">
        <p className="font-medium mb-1">How to tune:</p>
        <ul className="text-xs text-blue-400 space-y-1 ml-4 list-disc">
          <li>Click a bone in the viewer to select it</li>
          <li>Enable <span className="text-green-400">Drag Mode</span> to drag bones in 3D</li>
          <li>Use <span className="text-amber-400">Quick Position</span> buttons for fast fixes</li>
        </ul>
      </div>

      {/* Drag Mode Toggle */}
      <div className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg">
        <div>
          <p className="text-sm font-medium text-white">3D Drag Mode</p>
          <p className="text-xs text-gray-400">Drag bone handles in the viewer</p>
        </div>
        <button
          onClick={() => setDragMode?.(!dragMode)}
          className={`relative w-12 h-6 rounded-full transition-colors ${
            dragMode ? 'bg-green-600' : 'bg-gray-600'
          }`}
        >
          <span
            className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${
              dragMode ? 'translate-x-7' : 'translate-x-1'
            }`}
          />
        </button>
      </div>

      {/* Fix Floating Bones button */}
      {hasFloatingBones && (
        <button
          onClick={handleFixFloating}
          disabled={isFixing}
          className="w-full py-3 bg-amber-600 hover:bg-amber-500 disabled:bg-gray-600
                     text-white font-medium rounded-lg transition-colors
                     flex items-center justify-center gap-2"
        >
          {isFixing ? (
            <>
              <Spinner size="sm" variant="white" />
              Fixing...
            </>
          ) : (
            <>
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M11 4a2 2 0 114 0v1a1 1 0 001 1h3a1 1 0 011 1v3a1 1 0 01-1 1h-1a2 2 0 100 4h1a1 1 0 011 1v3a1 1 0 01-1 1h-3a1 1 0 01-1-1v-1a2 2 0 10-4 0v1a1 1 0 01-1 1H7a1 1 0 01-1-1v-3a1 1 0 00-1-1H4a2 2 0 110-4h1a1 1 0 001-1V7a1 1 0 011-1h3a1 1 0 001-1V4z" />
              </svg>
              Fix Floating Bones
            </>
          )}
        </button>
      )}

      {/* Floating bones list */}
      {hasFloatingBones && (
        <div className="p-3 bg-red-900/20 border border-red-700/30 rounded-lg">
          <p className="text-xs text-red-400 mb-2">Bones outside mesh:</p>
          <div className="flex flex-wrap gap-1">
            {floatingBones.map((bone) => (
              <button
                key={bone}
                onClick={() => setSelectedBone(bone)}
                className={`text-xs px-2 py-1 rounded transition-colors ${
                  selectedBone === bone
                    ? 'bg-red-600 text-white'
                    : 'bg-red-900/50 text-red-300 hover:bg-red-800/50'
                }`}
              >
                {bone}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Selected bone editor */}
      {selectedBone && selectedBoneData && (
        <div className="p-3 bg-gray-800/50 border border-gray-700 rounded-lg space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-white">{selectedBone}</span>
            {isBoneFloating(selectedBone) && (
              <span className="text-xs text-red-400">Outside mesh</span>
            )}
          </div>

          {/* Quick Position Buttons */}
          <div>
            <p className="text-xs text-gray-400 mb-2">Quick Position:</p>
            <div className="grid grid-cols-4 gap-1">
              {quickPositions.map((preset) => (
                <button
                  key={preset.name}
                  onClick={() => applyQuickPosition(preset)}
                  title={preset.description}
                  className="py-2 px-1 bg-gray-700 hover:bg-indigo-600 text-white
                             text-xs rounded transition-colors flex flex-col items-center gap-0.5"
                >
                  <span className="text-sm">{preset.icon}</span>
                  <span>{preset.name}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Snap to Mesh Surface */}
          <div>
            <p className="text-xs text-gray-400 mb-2">Snap to Mesh Surface:</p>
            <div className="grid grid-cols-3 gap-1">
              <button
                onClick={() => handleSnapToMesh('head')}
                title="Snap head joint to nearest mesh surface"
                className="py-2 px-2 bg-green-700 hover:bg-green-600 text-white
                           text-xs rounded transition-colors flex items-center justify-center gap-1"
              >
                <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                  <circle cx="10" cy="10" r="4" />
                </svg>
                Head
              </button>
              <button
                onClick={() => handleSnapToMesh('tail')}
                title="Snap tail joint to nearest mesh surface"
                className="py-2 px-2 bg-orange-700 hover:bg-orange-600 text-white
                           text-xs rounded transition-colors flex items-center justify-center gap-1"
              >
                <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                  <circle cx="10" cy="10" r="4" />
                </svg>
                Tail
              </button>
              <button
                onClick={() => handleSnapToMesh('both')}
                title="Snap both joints to nearest mesh surface"
                className="py-2 px-2 bg-purple-700 hover:bg-purple-600 text-white
                           text-xs rounded transition-colors flex items-center justify-center gap-1"
              >
                <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M10 2a1 1 0 011 1v1.323l3.954 1.582 1.599-.8a1 1 0 01.894 1.79l-1.233.616 1.738 5.42a1 1 0 01-.285 1.05A3.989 3.989 0 0115 15a3.989 3.989 0 01-2.667-1.019 1 1 0 01-.285-1.05l1.715-5.349L11 6.477V16h2a1 1 0 110 2H7a1 1 0 110-2h2V6.477L6.237 7.582l1.715 5.349a1 1 0 01-.285 1.05A3.989 3.989 0 015 15a3.989 3.989 0 01-2.667-1.019 1 1 0 01-.285-1.05l1.738-5.42-1.233-.617a1 1 0 01.894-1.788l1.599.799L9 4.323V3a1 1 0 011-1z" />
                </svg>
                Both
              </button>
            </div>
          </div>

          {/* Advanced Controls Toggle */}
          <button
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="w-full text-xs text-gray-400 hover:text-white flex items-center justify-center gap-1"
          >
            <span>{showAdvanced ? '▼' : '▶'}</span>
            <span>Manual Position Controls</span>
          </button>

          {/* Advanced Manual Controls */}
          {showAdvanced && (
            <>
              {/* Head position */}
              <div>
                <p className="text-xs text-gray-400 mb-2">Head Position (joint start)</p>
                <div className="grid grid-cols-3 gap-2">
                  {(['x', 'y', 'z'] as const).map((axis, i) => (
                    <div key={axis}>
                      <label className="text-xs text-gray-500 uppercase">{axis}</label>
                      <input
                        type="number"
                        step="0.01"
                        value={selectedBoneData.head[i].toFixed(3)}
                        onChange={(e) =>
                          handlePositionChange(axis, parseFloat(e.target.value) || 0, true)
                        }
                        className="w-full px-2 py-1 text-xs bg-gray-900 border border-gray-700
                                   rounded text-white focus:border-indigo-500 focus:outline-none"
                      />
                    </div>
                  ))}
                </div>
              </div>

              {/* Tail position */}
              <div>
                <p className="text-xs text-gray-400 mb-2">Tail Position (joint end)</p>
                <div className="grid grid-cols-3 gap-2">
                  {(['x', 'y', 'z'] as const).map((axis, i) => (
                    <div key={axis}>
                      <label className="text-xs text-gray-500 uppercase">{axis}</label>
                      <input
                        type="number"
                        step="0.01"
                        value={selectedBoneData.tail[i].toFixed(3)}
                        onChange={(e) =>
                          handlePositionChange(axis, parseFloat(e.target.value) || 0, false)
                        }
                        className="w-full px-2 py-1 text-xs bg-gray-900 border border-gray-700
                                   rounded text-white focus:border-indigo-500 focus:outline-none"
                      />
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {/* No selection hint */}
      {!selectedBone && (
        <div className="p-4 bg-gray-800/30 rounded-lg text-center">
          <p className="text-sm text-gray-400">
            Click a bone in the 3D viewer to select and edit it
          </p>
        </div>
      )}

      {/* Save error message */}
      {saveError && (
        <div className="p-2 bg-yellow-900/30 border border-yellow-700/30 rounded text-xs text-yellow-400">
          {saveError}
        </div>
      )}

      {/* Action buttons */}
      <div className="flex gap-2 pt-2">
        <button
          onClick={handleCancel}
          disabled={isSaving}
          className="flex-1 py-2.5 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800
                     text-white font-medium rounded-lg transition-colors"
        >
          Cancel
        </button>
        <button
          onClick={handleComplete}
          disabled={isSaving}
          className="flex-1 py-2.5 bg-green-600 hover:bg-green-500 disabled:bg-gray-600
                     text-white font-medium rounded-lg transition-colors
                     flex items-center justify-center gap-2"
        >
          {isSaving ? (
            <>
              <Spinner size="sm" variant="white" />
              Saving...
            </>
          ) : (
            <>
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              {hasFloatingBones ? 'Continue Anyway' : 'Looks Good!'}
            </>
          )}
        </button>
      </div>

      {/* Edit status */}
      {hasEdits && (
        <p className="text-xs text-center text-gray-500">
          {editedBones.size} bone{editedBones.size > 1 ? 's' : ''} modified
        </p>
      )}
    </div>
  );
}
