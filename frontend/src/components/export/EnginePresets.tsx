/**
 * EnginePresets Component - Game engine selection and configuration
 */

import { useCallback, useState } from 'react';
import { Card } from '../ui/Card';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Checkbox } from '../ui/Checkbox';
import { cn } from '../../lib/utils';
import type { EngineType } from '../../types';

interface EngineConfig {
  id: EngineType;
  name: string;
  icon: React.ReactNode;
  description: string;
  formats: string[];
  defaultPath: string;
  features: string[];
}

const ENGINES: EngineConfig[] = [
  {
    id: 'unity',
    name: 'Unity',
    icon: (
      <svg viewBox="0 0 24 24" className="w-8 h-8" fill="currentColor">
        <path d="M10.4 17.8l-2.8-4.8 2.8-4.8 2.8 4.8-2.8 4.8zm9.4-6.8l-2.4 4.2-5.6-9.6h4.8l3.2 5.4zm-9.4 8.4l5.6-9.6 2.4 4.2-4.8 8.2-3.2-2.8zm-8-2.4l2.4-4.2 2.4 4.2-2.4 4.2-2.4-4.2z" />
      </svg>
    ),
    description: 'Export with Unity-compatible settings and LOD groups',
    formats: ['GLB', 'FBX'],
    defaultPath: 'C:\\Users\\{user}\\UnityProjects\\',
    features: ['LOD Groups', 'Material Generation', 'Prefab Creation'],
  },
  {
    id: 'unreal',
    name: 'Unreal Engine',
    icon: (
      <svg viewBox="0 0 24 24" className="w-8 h-8" fill="currentColor">
        <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm0 2c5.523 0 10 4.477 10 10s-4.477 10-10 10S2 17.523 2 12 6.477 2 12 2zm-1 4v8l6-4-6-4z" />
      </svg>
    ),
    description: 'Export with ORM packed textures and Nanite-ready meshes',
    formats: ['GLB', 'FBX'],
    defaultPath: 'C:\\Users\\{user}\\UnrealProjects\\',
    features: ['ORM Textures', 'Nanite Ready', 'Blueprint Creation'],
  },
  {
    id: 'godot',
    name: 'Godot 4',
    icon: (
      <svg viewBox="0 0 24 24" className="w-8 h-8" fill="currentColor">
        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-13h2v6h-2zm0 8h2v2h-2z" />
      </svg>
    ),
    description: 'Export GLB with Godot 4 scene file for LOD switching',
    formats: ['GLB'],
    defaultPath: 'C:\\Users\\{user}\\GodotProjects\\',
    features: ['GLB Direct', 'Scene Generation', 'LOD Nodes'],
  },
];

interface EnginePresetsProps {
  selectedEngine: EngineType | null;
  onSelectEngine: (engine: EngineType) => void;
  projectPath: string;
  onProjectPathChange: (path: string) => void;
  className?: string;
}

export function EnginePresets({
  selectedEngine,
  onSelectEngine,
  projectPath,
  onProjectPathChange,
  className,
}: EnginePresetsProps) {
  const selectedConfig = ENGINES.find((e) => e.id === selectedEngine);

  return (
    <div className={cn('space-y-4', className)}>
      {/* Engine Selection */}
      <div>
        <label className="block text-sm font-medium text-text-secondary mb-2">
          Target Engine
        </label>
        <div className="grid grid-cols-3 gap-3">
          {ENGINES.map((engine) => (
            <button
              key={engine.id}
              onClick={() => onSelectEngine(engine.id)}
              className={cn(
                'p-4 rounded-xl border-2 text-center transition-all',
                'hover:border-primary/50 hover:bg-surface-light',
                selectedEngine === engine.id
                  ? 'border-primary bg-primary/10'
                  : 'border-border bg-surface'
              )}
            >
              <div
                className={cn(
                  'flex justify-center mb-2 transition-colors',
                  selectedEngine === engine.id
                    ? 'text-primary'
                    : 'text-text-muted'
                )}
              >
                {engine.icon}
              </div>
              <p className="text-sm font-medium text-text-primary">
                {engine.name}
              </p>
            </button>
          ))}
        </div>
      </div>

      {/* Engine Details */}
      {selectedConfig && (
        <Card variant="outlined" padding="sm" className="animate-fadeIn">
          <div className="flex items-start gap-4">
            <div className="text-primary">{selectedConfig.icon}</div>
            <div className="flex-1">
              <h4 className="font-medium text-text-primary mb-1">
                {selectedConfig.name}
              </h4>
              <p className="text-sm text-text-muted mb-3">
                {selectedConfig.description}
              </p>
              <div className="flex flex-wrap gap-2">
                {selectedConfig.features.map((feature) => (
                  <span
                    key={feature}
                    className="px-2 py-1 bg-surface-light rounded text-xs text-text-secondary"
                  >
                    {feature}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Project Path */}
      {selectedEngine && (
        <div className="animate-fadeIn">
          <Input
            label="Project Path"
            value={projectPath}
            onChange={(e) => onProjectPathChange(e.target.value)}
            placeholder={selectedConfig?.defaultPath || 'Enter project path...'}
            rightIcon={
              <button
                onClick={() => {
                  // TODO: Open folder picker via Electron/Tauri
                  console.log('Open folder picker');
                }}
                className="p-1 hover:bg-surface-lighter rounded transition-colors"
                title="Browse..."
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
                  />
                </svg>
              </button>
            }
          />
          <p className="text-xs text-text-muted mt-1">
            Supported formats: {selectedConfig?.formats.join(', ')}
          </p>
        </div>
      )}
    </div>
  );
}

/**
 * Export options configuration
 */
interface ExportOptionsProps {
  includeLods: boolean;
  onIncludeLodsChange: (value: boolean) => void;
  compress: boolean;
  onCompressChange: (value: boolean) => void;
  generateMaterials: boolean;
  onGenerateMaterialsChange: (value: boolean) => void;
  className?: string;
}

export function ExportOptions({
  includeLods,
  onIncludeLodsChange,
  compress,
  onCompressChange,
  generateMaterials,
  onGenerateMaterialsChange,
  className,
}: ExportOptionsProps) {
  return (
    <div className={cn('space-y-3', className)}>
      <label className="block text-sm font-medium text-text-secondary mb-2">
        Export Options
      </label>

      <Checkbox
        checked={includeLods}
        onChange={(e) => onIncludeLodsChange(e.target.checked)}
        label="Generate LOD levels"
        description="Create multiple detail levels for performance"
      />

      <Checkbox
        checked={compress}
        onChange={(e) => onCompressChange(e.target.checked)}
        label="Draco compression"
        description="Compress meshes for smaller file sizes"
      />

      <Checkbox
        checked={generateMaterials}
        onChange={(e) => onGenerateMaterialsChange(e.target.checked)}
        label="Generate materials"
        description="Create engine-specific material assets"
      />
    </div>
  );
}
