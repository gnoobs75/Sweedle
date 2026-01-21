/**
 * Animation preset selector component.
 * Displays a grid of available animation presets.
 */

import type { AnimationPreset } from '../../stores/animationStore';

interface PresetSelectorProps {
  presets: AnimationPreset[];
  selectedId: string | null;
  onSelect: (presetId: string | null) => void;
}

// Icons for different animation types
const animationIcons: Record<string, string> = {
  // Common animations
  idle: '🧘',
  walk: '🚶',
  run: '🏃',
  attack: '⚔️',
  jump: '🦘',
  die: '💀',
  sit: '🪑',
  lie_down: '🛏️',
  // Humanoid-specific
  crouch: '🧎',
  dodge: '💨',
  wave: '👋',
  cheer: '🙌',
  pickup: '🤲',
  // Quadruped-specific
  trot: '🐕',
  gallop: '🐎',
  tail_wag: '🐕‍🦺',
  bite: '🦷',
  shake: '💦',
  pounce: '🐆',
  howl: '🐺',
  roll_over: '🔄',
  play_dead: '☠️',
};

export function PresetSelector({ presets, selectedId, onSelect }: PresetSelectorProps) {
  if (presets.length === 0) {
    return (
      <div className="text-center text-gray-400 py-8">
        No animation presets available for this character type.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-3">
      {presets.map((preset) => {
        const isSelected = preset.id === selectedId;
        const icon = animationIcons[preset.animationType] || '🎬';

        return (
          <button
            key={preset.id}
            onClick={() => onSelect(isSelected ? null : preset.id)}
            className={`
              relative p-4 rounded-lg border-2 text-left transition-all
              ${
                isSelected
                  ? 'border-indigo-500 bg-indigo-500/10'
                  : 'border-gray-700 bg-gray-800/50 hover:border-gray-600 hover:bg-gray-800'
              }
            `}
          >
            {/* Icon and Name */}
            <div className="flex items-center gap-2 mb-2">
              <span className="text-2xl">{icon}</span>
              <span className="font-medium text-white">{preset.name}</span>
            </div>

            {/* Description */}
            <p className="text-xs text-gray-400 mb-2 line-clamp-2">
              {preset.description}
            </p>

            {/* Duration badge */}
            <div className="flex items-center gap-2">
              <span className="text-xs px-2 py-0.5 bg-gray-700 rounded text-gray-300">
                {preset.duration}s
              </span>
              {preset.tags.includes('loop') && (
                <span className="text-xs px-2 py-0.5 bg-blue-900/50 rounded text-blue-300">
                  Loop
                </span>
              )}
              {preset.tags.includes('once') && (
                <span className="text-xs px-2 py-0.5 bg-amber-900/50 rounded text-amber-300">
                  One-shot
                </span>
              )}
            </div>

            {/* Selected indicator */}
            {isSelected && (
              <div className="absolute top-2 right-2">
                <svg
                  className="w-5 h-5 text-indigo-400"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                    clipRule="evenodd"
                  />
                </svg>
              </div>
            )}
          </button>
        );
      })}
    </div>
  );
}
