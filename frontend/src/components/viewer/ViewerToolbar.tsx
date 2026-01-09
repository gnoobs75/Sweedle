/**
 * ViewerToolbar Component - Controls for 3D viewer
 */

import { useState } from 'react';
import { useViewerStore } from '../../stores/viewerStore';
import { useRiggingStore } from '../../stores/riggingStore';
import { Button } from '../ui/Button';
import { Slider } from '../ui/Slider';
import { Select } from '../ui/Select';
import { Tooltip } from '../ui/Tooltip';
import { cn } from '../../lib/utils';

interface ViewerToolbarProps {
  className?: string;
}

const ENVIRONMENT_PRESETS = [
  { value: 'studio', label: 'Studio' },
  { value: 'sunset', label: 'Sunset' },
  { value: 'dawn', label: 'Dawn' },
  { value: 'night', label: 'Night' },
  { value: 'warehouse', label: 'Warehouse' },
  { value: 'forest', label: 'Forest' },
  { value: 'apartment', label: 'Apartment' },
  { value: 'city', label: 'City' },
  { value: 'park', label: 'Park' },
  { value: 'lobby', label: 'Lobby' },
];

const BACKGROUND_COLORS = [
  { value: '#1a1a2e', label: 'Dark Blue' },
  { value: '#0f0f1a', label: 'Dark' },
  { value: '#2d2d44', label: 'Slate' },
  { value: '#1a2e1a', label: 'Dark Green' },
  { value: '#2e1a1a', label: 'Dark Red' },
  { value: '#3d3d3d', label: 'Gray' },
  { value: '#000000', label: 'Black' },
];

export function ViewerToolbar({ className }: ViewerToolbarProps) {
  const {
    settings,
    setSetting,
    resetSettings,
    resetCamera,
    currentLodLevel,
    availableLodLevels,
    setLodLevel,
  } = useViewerStore();

  const { skeletonData, showSkeleton, setShowSkeleton, selectedBone } = useRiggingStore();

  const [showSettings, setShowSettings] = useState(false);

  return (
    <div className={cn('flex items-center justify-between px-4 h-12', className)}>
      {/* Left - View Controls */}
      <div className="flex items-center gap-1">
        <Tooltip content="Wireframe (W)" position="bottom">
          <Button
            variant={settings.showWireframe ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setSetting('showWireframe', !settings.showWireframe)}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z"
              />
            </svg>
          </Button>
        </Tooltip>

        <Tooltip content="Grid (G)" position="bottom">
          <Button
            variant={settings.showGrid ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setSetting('showGrid', !settings.showGrid)}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 6h16M4 12h16M4 18h16"
              />
            </svg>
          </Button>
        </Tooltip>

        <Tooltip content="Axes (A)" position="bottom">
          <Button
            variant={settings.showAxes ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setSetting('showAxes', !settings.showAxes)}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M7 21l5-5 5 5M12 16V3m0 0l-3 3m3-3l3 3"
              />
            </svg>
          </Button>
        </Tooltip>

        {/* Skeleton toggle - only show when skeleton data is available */}
        {skeletonData && (
          <Tooltip content={`Skeleton (S)${selectedBone ? ` - ${selectedBone}` : ''}`} position="bottom">
            <Button
              variant={showSkeleton ? 'primary' : 'ghost'}
              size="sm"
              onClick={() => setShowSkeleton(!showSkeleton)}
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 4v1m0 14v1m-7-8h1m12 0h1m-2.636-5.364l-.707.707m-9.314 9.314l-.707.707m0-10.728l.707.707m9.314 9.314l.707.707M12 8a4 4 0 100 8 4 4 0 000-8z"
                />
              </svg>
            </Button>
          </Tooltip>
        )}

        <div className="w-px h-6 bg-border mx-2" />

        <Tooltip content="Auto Rotate (R)" position="bottom">
          <Button
            variant={settings.autoRotate ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setSetting('autoRotate', !settings.autoRotate)}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
          </Button>
        </Tooltip>

        {/* LOD Selector */}
        {availableLodLevels.length > 1 && (
          <>
            <div className="w-px h-6 bg-border mx-2" />
            <div className="flex items-center gap-1">
              <span className="text-xs text-text-muted">LOD:</span>
              {availableLodLevels.map((level, index) => (
                <Button
                  key={level}
                  variant={currentLodLevel === index ? 'primary' : 'ghost'}
                  size="sm"
                  onClick={() => setLodLevel(index)}
                  className="px-2 min-w-0"
                >
                  {index}
                </Button>
              ))}
            </div>
          </>
        )}
      </div>

      {/* Right - Settings & Camera */}
      <div className="flex items-center gap-1">
        <Tooltip content="Reset Camera (Home)" position="bottom">
          <Button variant="ghost" size="sm" onClick={resetCamera}>
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 13a3 3 0 11-6 0 3 3 0 016 0z"
              />
            </svg>
          </Button>
        </Tooltip>

        <Tooltip content="Settings" position="bottom">
          <Button
            variant={showSettings ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setShowSettings(!showSettings)}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
              />
            </svg>
          </Button>
        </Tooltip>

        {/* Settings Dropdown */}
        {showSettings && (
          <div className="absolute right-4 top-14 w-64 bg-surface border border-border rounded-xl shadow-xl z-50 p-4 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-text-primary">
                Viewer Settings
              </h3>
              <Button variant="ghost" size="sm" onClick={resetSettings}>
                Reset
              </Button>
            </div>

            <Select
              label="Environment"
              value={settings.environmentMap}
              onChange={(e) => setSetting('environmentMap', e.target.value)}
              options={ENVIRONMENT_PRESETS}
            />

            <div>
              <label className="block text-sm font-medium text-text-secondary mb-2">
                Background
              </label>
              <div className="flex flex-wrap gap-2">
                {BACKGROUND_COLORS.map((color) => (
                  <button
                    key={color.value}
                    onClick={() => setSetting('backgroundColor', color.value)}
                    className={cn(
                      'w-8 h-8 rounded-lg border-2 transition-all',
                      settings.backgroundColor === color.value
                        ? 'border-primary scale-110'
                        : 'border-transparent hover:border-primary/50'
                    )}
                    style={{ backgroundColor: color.value }}
                    title={color.label}
                  />
                ))}
              </div>
            </div>

            <Slider
              label="Exposure"
              value={settings.exposure}
              onChange={(v) => setSetting('exposure', v)}
              min={0.1}
              max={3}
              step={0.1}
              valueFormatter={(v) => v.toFixed(1)}
            />
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Compact toolbar for embedded viewers
 */
export function CompactViewerToolbar({ className }: ViewerToolbarProps) {
  const { settings, setSetting, resetCamera } = useViewerStore();

  return (
    <div className={cn('flex items-center gap-1', className)}>
      <Button
        variant={settings.showWireframe ? 'primary' : 'ghost'}
        size="sm"
        onClick={() => setSetting('showWireframe', !settings.showWireframe)}
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5z" />
        </svg>
      </Button>
      <Button
        variant={settings.autoRotate ? 'primary' : 'ghost'}
        size="sm"
        onClick={() => setSetting('autoRotate', !settings.autoRotate)}
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
      </Button>
      <Button variant="ghost" size="sm" onClick={resetCamera}>
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
      </Button>
    </div>
  );
}
