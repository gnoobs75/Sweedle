/**
 * GPUMonitor - Live GPU/VRAM monitoring widget
 * Shows real-time GPU stats with visual indicators
 */

import { useState, useEffect, useCallback } from 'react';
import { cn } from '../../lib/utils';

interface GPUStats {
  name: string;
  vram_used_gb: number;
  vram_reserved_gb: number;
  vram_total_gb: number;
  vram_percent: number;
  utilization_percent?: number;
  temperature_c?: number;
}

interface DeviceStats {
  timestamp: number;
  cpu_percent: number;
  ram_used_gb: number;
  ram_total_gb: number;
  ram_percent: number;
  gpu: GPUStats | null;
  worker?: {
    running: boolean;
    current_job: string | null;
  };
  queue?: {
    size: number;
    processing: boolean;
  };
}

interface GPUMonitorProps {
  className?: string;
  compact?: boolean;
  pollInterval?: number;
}

export function GPUMonitor({
  className,
  compact = false,
  pollInterval = 1000
}: GPUMonitorProps) {
  const [stats, setStats] = useState<DeviceStats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isExpanded, setIsExpanded] = useState(!compact);

  const fetchStats = useCallback(async () => {
    try {
      const response = await fetch('http://localhost:8000/api/device/stats');
      if (!response.ok) throw new Error('Failed to fetch stats');
      const data = await response.json();
      setStats(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Connection error');
    }
  }, []);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, pollInterval);
    return () => clearInterval(interval);
  }, [fetchStats, pollInterval]);

  const getVramColor = (percent: number) => {
    if (percent < 50) return 'bg-green-500';
    if (percent < 75) return 'bg-yellow-500';
    if (percent < 90) return 'bg-orange-500';
    return 'bg-red-500';
  };

  const getTempColor = (temp: number) => {
    if (temp < 60) return 'text-green-400';
    if (temp < 75) return 'text-yellow-400';
    if (temp < 85) return 'text-orange-400';
    return 'text-red-400';
  };

  if (error) {
    return (
      <div className={cn(
        'bg-surface-light/80 backdrop-blur rounded-lg border border-border p-2 text-xs text-error',
        className
      )}>
        GPU Monitor: {error}
      </div>
    );
  }

  if (!stats) {
    return (
      <div className={cn(
        'bg-surface-light/80 backdrop-blur rounded-lg border border-border p-2 text-xs text-text-muted animate-pulse',
        className
      )}>
        Loading GPU stats...
      </div>
    );
  }

  // Compact mode - just show VRAM bar
  if (compact && !isExpanded) {
    return (
      <button
        onClick={() => setIsExpanded(true)}
        className={cn(
          'bg-surface-light/80 backdrop-blur rounded-lg border border-border p-2 text-xs hover:bg-surface-light transition-colors',
          className
        )}
      >
        <div className="flex items-center gap-2">
          <span className="text-text-muted">VRAM:</span>
          {stats.gpu ? (
            <>
              <div className="w-16 h-2 bg-surface rounded-full overflow-hidden">
                <div
                  className={cn('h-full transition-all', getVramColor(stats.gpu.vram_percent))}
                  style={{ width: `${stats.gpu.vram_percent}%` }}
                />
              </div>
              <span className="text-text-primary font-mono">
                {stats.gpu.vram_used_gb.toFixed(1)}G
              </span>
            </>
          ) : (
            <span className="text-text-muted">N/A</span>
          )}
        </div>
      </button>
    );
  }

  return (
    <div className={cn(
      'bg-surface-light/90 backdrop-blur rounded-lg border border-border shadow-lg',
      className
    )}>
      {/* Header */}
      <div
        className="flex items-center justify-between px-3 py-2 border-b border-border cursor-pointer hover:bg-surface-light/50"
        onClick={() => compact && setIsExpanded(false)}
      >
        <div className="flex items-center gap-2">
          <div className={cn(
            'w-2 h-2 rounded-full',
            stats.worker?.running ? 'bg-green-500 animate-pulse' : 'bg-gray-500'
          )} />
          <span className="text-xs font-semibold text-text-primary">System Monitor</span>
        </div>
        {stats.worker?.current_job && (
          <span className="text-[10px] text-primary font-mono">Processing...</span>
        )}
      </div>

      <div className="p-3 space-y-3">
        {/* GPU Section */}
        {stats.gpu ? (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs text-text-muted truncate max-w-[180px]" title={stats.gpu.name}>
                {stats.gpu.name}
              </span>
              {stats.gpu.temperature_c && (
                <span className={cn('text-xs font-mono', getTempColor(stats.gpu.temperature_c))}>
                  {stats.gpu.temperature_c}C
                </span>
              )}
            </div>

            {/* VRAM Bar */}
            <div className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-text-muted">VRAM</span>
                <span className="font-mono text-text-primary">
                  {stats.gpu.vram_used_gb.toFixed(1)} / {stats.gpu.vram_total_gb.toFixed(0)} GB
                </span>
              </div>
              <div className="w-full h-3 bg-surface rounded-full overflow-hidden">
                <div
                  className={cn('h-full transition-all duration-300', getVramColor(stats.gpu.vram_percent))}
                  style={{ width: `${Math.min(stats.gpu.vram_percent, 100)}%` }}
                />
              </div>
              <div className="flex items-center justify-between text-[10px] text-text-muted">
                <span>Allocated: {stats.gpu.vram_used_gb.toFixed(2)} GB</span>
                <span>Reserved: {stats.gpu.vram_reserved_gb.toFixed(2)} GB</span>
              </div>
            </div>

            {/* GPU Utilization */}
            {stats.gpu.utilization_percent !== undefined && (
              <div className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-text-muted">GPU Load</span>
                  <span className="font-mono text-text-primary">{stats.gpu.utilization_percent}%</span>
                </div>
                <div className="w-full h-2 bg-surface rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary transition-all duration-300"
                    style={{ width: `${stats.gpu.utilization_percent}%` }}
                  />
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="text-xs text-text-muted text-center py-2">
            No GPU detected
          </div>
        )}

        {/* Divider */}
        <div className="border-t border-border" />

        {/* CPU & RAM */}
        <div className="grid grid-cols-2 gap-3">
          {/* CPU */}
          <div className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="text-text-muted">CPU</span>
              <span className="font-mono text-text-primary">{stats.cpu_percent.toFixed(0)}%</span>
            </div>
            <div className="w-full h-2 bg-surface rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-500 transition-all duration-300"
                style={{ width: `${stats.cpu_percent}%` }}
              />
            </div>
          </div>

          {/* RAM */}
          <div className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="text-text-muted">RAM</span>
              <span className="font-mono text-text-primary">{stats.ram_used_gb.toFixed(0)}G</span>
            </div>
            <div className="w-full h-2 bg-surface rounded-full overflow-hidden">
              <div
                className="h-full bg-purple-500 transition-all duration-300"
                style={{ width: `${stats.ram_percent}%` }}
              />
            </div>
          </div>
        </div>

        {/* Queue Status */}
        {stats.queue && stats.queue.size > 0 && (
          <>
            <div className="border-t border-border" />
            <div className="flex items-center justify-between text-xs">
              <span className="text-text-muted">Queue</span>
              <span className="text-primary font-mono">{stats.queue.size} job(s)</span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

/**
 * Compact VRAM indicator for toolbar
 */
export function VRAMIndicator({ className }: { className?: string }) {
  const [stats, setStats] = useState<DeviceStats | null>(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/device/stats');
        if (response.ok) {
          setStats(await response.json());
        }
      } catch {
        // Silently fail
      }
    };

    fetchStats();
    const interval = setInterval(fetchStats, 2000);
    return () => clearInterval(interval);
  }, []);

  if (!stats?.gpu) return null;

  const getColor = (percent: number) => {
    if (percent < 50) return 'text-green-400';
    if (percent < 75) return 'text-yellow-400';
    if (percent < 90) return 'text-orange-400';
    return 'text-red-400';
  };

  return (
    <div className={cn('flex items-center gap-1 text-xs font-mono', className)}>
      <svg className="w-3 h-3 text-text-muted" fill="currentColor" viewBox="0 0 20 20">
        <path d="M13 7H7v6h6V7z" />
        <path fillRule="evenodd" d="M3 3a2 2 0 012-2h10a2 2 0 012 2v14a2 2 0 01-2 2H5a2 2 0 01-2-2V3zm2 0v14h10V3H5z" clipRule="evenodd" />
      </svg>
      <span className={getColor(stats.gpu.vram_percent)}>
        {stats.gpu.vram_used_gb.toFixed(1)}G
      </span>
      <span className="text-text-muted">/</span>
      <span className="text-text-muted">{stats.gpu.vram_total_gb.toFixed(0)}G</span>
    </div>
  );
}
