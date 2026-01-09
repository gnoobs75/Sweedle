/**
 * CharacterTypeSelector - Select character type for rigging.
 */

import type { CharacterType } from '../../stores/riggingStore';

interface CharacterTypeSelectorProps {
  value: CharacterType;
  onChange: (type: CharacterType) => void;
  detectedType?: CharacterType | null;
}

const CHARACTER_TYPES: { value: CharacterType; label: string; description: string; icon: string }[] = [
  {
    value: 'auto',
    label: 'Auto-Detect',
    description: 'Automatically detect character type',
    icon: 'M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z',
  },
  {
    value: 'humanoid',
    label: 'Humanoid',
    description: 'Bipedal characters (humans, robots)',
    icon: 'M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z',
  },
  {
    value: 'quadruped',
    label: 'Quadruped',
    description: 'Four-legged creatures (animals)',
    icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6',
  },
];

export function CharacterTypeSelector({
  value,
  onChange,
  detectedType,
}: CharacterTypeSelectorProps) {
  return (
    <div className="p-3 bg-surface-light rounded-lg border border-border">
      <h4 className="text-xs font-semibold text-text-muted uppercase mb-3">Character Type</h4>

      <div className="space-y-2">
        {CHARACTER_TYPES.map((type) => (
          <label
            key={type.value}
            className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
              value === type.value
                ? 'border-primary bg-primary/10'
                : 'border-transparent hover:bg-surface-hover'
            }`}
          >
            <input
              type="radio"
              name="characterType"
              value={type.value}
              checked={value === type.value}
              onChange={() => onChange(type.value)}
              className="mt-0.5 text-primary"
            />
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <svg className="w-5 h-5 text-text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={type.icon} />
                </svg>
                <span className="font-medium text-text-primary">{type.label}</span>
                {type.value === 'auto' && detectedType && (
                  <span className="text-xs px-2 py-0.5 bg-primary/20 text-primary rounded">
                    Detected: {detectedType}
                  </span>
                )}
              </div>
              <p className="text-xs text-text-muted mt-1">{type.description}</p>
            </div>
          </label>
        ))}
      </div>
    </div>
  );
}
