/**
 * Animation parameter adjustment sliders.
 */

import type { AnimationParameters } from '../../stores/animationStore';

interface ParameterSlidersProps {
  parameters: AnimationParameters;
  onChange: (params: Partial<AnimationParameters>) => void;
  disabled?: boolean;
}

export function ParameterSliders({
  parameters,
  onChange,
  disabled = false,
}: ParameterSlidersProps) {
  return (
    <div className="space-y-4">
      {/* Speed Slider */}
      <div>
        <div className="flex justify-between items-center mb-1">
          <label className="text-sm text-gray-300">Speed</label>
          <span className="text-sm text-gray-400">{parameters.speed.toFixed(1)}x</span>
        </div>
        <input
          type="range"
          min={0.1}
          max={3.0}
          step={0.1}
          value={parameters.speed}
          onChange={(e) => onChange({ speed: parseFloat(e.target.value) })}
          disabled={disabled}
          className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer
                     disabled:opacity-50 disabled:cursor-not-allowed
                     [&::-webkit-slider-thumb]:appearance-none
                     [&::-webkit-slider-thumb]:w-4
                     [&::-webkit-slider-thumb]:h-4
                     [&::-webkit-slider-thumb]:bg-indigo-500
                     [&::-webkit-slider-thumb]:rounded-full
                     [&::-webkit-slider-thumb]:cursor-pointer"
        />
        <div className="flex justify-between text-xs text-gray-500 mt-1">
          <span>Slow</span>
          <span>Fast</span>
        </div>
      </div>

      {/* Intensity Slider */}
      <div>
        <div className="flex justify-between items-center mb-1">
          <label className="text-sm text-gray-300">Intensity</label>
          <span className="text-sm text-gray-400">
            {(parameters.intensity * 100).toFixed(0)}%
          </span>
        </div>
        <input
          type="range"
          min={0.1}
          max={2.0}
          step={0.1}
          value={parameters.intensity}
          onChange={(e) => onChange({ intensity: parseFloat(e.target.value) })}
          disabled={disabled}
          className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer
                     disabled:opacity-50 disabled:cursor-not-allowed
                     [&::-webkit-slider-thumb]:appearance-none
                     [&::-webkit-slider-thumb]:w-4
                     [&::-webkit-slider-thumb]:h-4
                     [&::-webkit-slider-thumb]:bg-indigo-500
                     [&::-webkit-slider-thumb]:rounded-full
                     [&::-webkit-slider-thumb]:cursor-pointer"
        />
        <div className="flex justify-between text-xs text-gray-500 mt-1">
          <span>Subtle</span>
          <span>Exaggerated</span>
        </div>
      </div>
    </div>
  );
}
