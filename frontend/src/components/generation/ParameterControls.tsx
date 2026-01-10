/**
 * ParameterControls Component - Generation parameter inputs
 */

import { useGenerationStore } from '../../stores/generationStore';
import { Slider } from '../ui/Slider';
import { Select } from '../ui/Select';
import { Toggle } from '../ui/Toggle';
import { Input } from '../ui/Input';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';
import { cn } from '../../lib/utils';
import type { GenerationMode, OutputFormat } from '../../types';

interface ParameterControlsProps {
  disabled?: boolean;
  className?: string;
}

const QUALITY_PRESETS = [
  {
    id: 'fast',
    label: 'Fast',
    description: '~30 seconds',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
      </svg>
    ),
  },
  {
    id: 'standard',
    label: 'Standard',
    description: '~1 minute',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
  {
    id: 'quality',
    label: 'Quality',
    description: '~2 minutes',
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
      </svg>
    ),
  },
];

export function ParameterControls({
  disabled = false,
  className,
}: ParameterControlsProps) {
  const {
    parameters,
    setParameter,
    setParameters,
    applyPreset,
    resetParameters,
  } = useGenerationStore();

  return (
    <div className={cn('space-y-6', className)}>
      {/* Quality Presets */}
      <div>
        <label className="block text-sm font-medium text-text-secondary mb-3">
          Quality Preset
        </label>
        <div className="grid grid-cols-3 gap-2">
          {QUALITY_PRESETS.map((preset) => (
            <button
              key={preset.id}
              onClick={() => applyPreset(preset.id as 'fast' | 'standard' | 'quality')}
              disabled={disabled}
              className={cn(
                'flex flex-col items-center gap-1 p-3 rounded-lg border transition-all',
                'hover:border-primary/50 hover:bg-surface-light',
                'disabled:opacity-50 disabled:cursor-not-allowed',
                parameters.mode === preset.id
                  ? 'border-primary bg-primary/10 text-primary'
                  : 'border-border text-text-secondary'
              )}
            >
              {preset.icon}
              <span className="text-sm font-medium">{preset.label}</span>
              <span className="text-xs text-text-muted">{preset.description}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Advanced Parameters */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-text-secondary">
            Advanced Settings
          </h3>
          <Button
            variant="ghost"
            size="sm"
            onClick={resetParameters}
            disabled={disabled}
          >
            Reset
          </Button>
        </div>

        {/* Inference Steps */}
        <Slider
          label="Inference Steps"
          value={parameters.inferenceSteps}
          onChange={(v) => setParameter('inferenceSteps', v)}
          min={5}
          max={100}
          step={5}
          disabled={disabled}
          hint="More steps = higher quality, slower generation"
        />

        {/* Guidance Scale */}
        <Slider
          label="Guidance Scale"
          value={parameters.guidanceScale}
          onChange={(v) => setParameter('guidanceScale', v)}
          min={1}
          max={15}
          step={0.5}
          valueFormatter={(v) => v.toFixed(1)}
          disabled={disabled}
          hint="Higher values follow the input more closely"
        />

        {/* Octree Resolution */}
        <div>
          <label className="block text-sm font-medium text-text-secondary mb-1.5">
            Mesh Resolution
          </label>
          <div className="grid grid-cols-4 gap-2">
            {[128, 256, 384, 512].map((res) => (
              <button
                key={res}
                onClick={() => setParameter('octreeResolution', res)}
                disabled={disabled}
                className={cn(
                  'py-2 px-3 text-sm font-medium rounded-lg border transition-all',
                  'disabled:opacity-50 disabled:cursor-not-allowed',
                  parameters.octreeResolution === res
                    ? 'border-primary bg-primary/10 text-primary'
                    : 'border-border text-text-secondary hover:border-primary/50'
                )}
              >
                {res}
              </button>
            ))}
          </div>
          <p className="mt-1.5 text-xs text-text-muted">
            Higher resolution = more detail, larger file size
          </p>
        </div>

        {/* Seed */}
        <Input
          label="Seed (Optional)"
          type="number"
          value={parameters.seed ?? ''}
          onChange={(e) =>
            setParameter(
              'seed',
              e.target.value ? parseInt(e.target.value, 10) : undefined
            )
          }
          placeholder="Random"
          disabled={disabled}
          hint="Set a seed for reproducible results"
          rightIcon={
            <button
              onClick={() =>
                setParameter('seed', Math.floor(Math.random() * 2147483647))
              }
              className="p-1 hover:bg-surface-lighter rounded transition-colors"
              title="Generate random seed"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
          }
        />

        {/* Texture Generation */}
        <Toggle
          label="Generate Texture"
          description="OFF = faster shape-only (add texture later from viewer)"
          checked={parameters.generateTexture}
          onChange={(e) => setParameter('generateTexture', e.target.checked)}
          disabled={disabled}
        />

        {/* Face Count Limit */}
        <Input
          label="Max Face Count (Optional)"
          type="number"
          value={parameters.faceCount ?? ''}
          onChange={(e) =>
            setParameter(
              'faceCount',
              e.target.value ? parseInt(e.target.value, 10) : undefined
            )
          }
          placeholder="No limit"
          disabled={disabled}
          hint="Limit polygon count for game-ready meshes"
        />

        {/* Output Format */}
        <Select
          label="Output Format"
          value={parameters.outputFormat}
          onChange={(e) => setParameter('outputFormat', e.target.value as OutputFormat)}
          disabled={disabled}
          options={[
            { value: 'glb', label: 'GLB (Recommended)' },
            { value: 'obj', label: 'OBJ + MTL' },
            { value: 'fbx', label: 'FBX' },
          ]}
        />
      </div>
    </div>
  );
}

/**
 * Compact parameter controls for simple mode
 */
export function SimpleParameterControls({
  disabled = false,
  className,
}: ParameterControlsProps) {
  const { parameters, applyPreset } = useGenerationStore();

  return (
    <div className={cn('space-y-3', className)}>
      <label className="block text-sm font-medium text-text-secondary">
        Quality
      </label>
      <div className="flex gap-2">
        {QUALITY_PRESETS.map((preset) => (
          <button
            key={preset.id}
            onClick={() => applyPreset(preset.id as 'fast' | 'standard' | 'quality')}
            disabled={disabled}
            className={cn(
              'flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg border transition-all',
              'disabled:opacity-50 disabled:cursor-not-allowed',
              parameters.mode === preset.id
                ? 'border-primary bg-primary/10 text-primary'
                : 'border-border text-text-secondary hover:border-primary/50'
            )}
          >
            {preset.icon}
            <span className="text-sm font-medium">{preset.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
