/**
 * List of applied animations with actions.
 */

import { useState } from 'react';
import { useAnimationStore, type AnimationClip } from '../../stores/animationStore';
import { Spinner } from '../ui/Spinner';

// Icons for different animation types
const animationIcons: Record<string, string> = {
  idle: '🧘',
  walk: '🚶',
  run: '🏃',
  attack: '⚔️',
  trot: '🐕',
  tail_wag: '🐕‍🦺',
  bite: '🦷',
};

interface AnimationListProps {
  clips: AnimationClip[];
  onDelete?: (clipId: string) => Promise<void>;
}

export function AnimationList({ clips, onDelete }: AnimationListProps) {
  const { activeClipId, setActiveClip } = useAnimationStore();
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const handleDelete = async (clipId: string) => {
    if (!onDelete) return;
    setDeletingId(clipId);
    try {
      await onDelete(clipId);
    } finally {
      setDeletingId(null);
    }
  };

  if (clips.length === 0) {
    return (
      <div className="text-center text-gray-500 text-sm py-4">
        No animations applied yet.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {clips.map((clip) => {
        const isActive = clip.id === activeClipId;
        const icon = animationIcons[clip.animationType] || '🎬';

        return (
          <div
            key={clip.id}
            className={`
              flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-all
              ${
                isActive
                  ? 'bg-indigo-900/30 border border-indigo-500/50'
                  : 'bg-gray-800/30 border border-gray-700 hover:bg-gray-800/50'
              }
            `}
            onClick={() => setActiveClip(clip.id)}
          >
            {/* Icon */}
            <span className="text-lg">{icon}</span>

            {/* Info */}
            <div className="flex-1 min-w-0">
              <div className="font-medium text-white text-sm truncate">
                {clip.name}
              </div>
              <div className="text-xs text-gray-400">
                {clip.duration.toFixed(1)}s &middot; {clip.loop_mode}
              </div>
            </div>

            {/* Active indicator */}
            {isActive && (
              <div className="w-2 h-2 bg-indigo-400 rounded-full animate-pulse" />
            )}

            {/* Delete button */}
            {onDelete && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleDelete(clip.id);
                }}
                disabled={deletingId === clip.id}
                className="p-1.5 text-gray-500 hover:text-red-400 transition-colors disabled:opacity-50"
                title="Remove animation"
              >
                {deletingId === clip.id ? (
                  <Spinner size="sm" variant="default" />
                ) : (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                    />
                  </svg>
                )}
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
}
