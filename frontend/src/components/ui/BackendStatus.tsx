/**
 * BackendStatus - Shows backend server connection status
 * Pings /health endpoint periodically
 */

import { useState, useEffect, useCallback } from 'react';
import { cn } from '../../lib/utils';
import { logger } from '../../lib/logger';

// Detect if running in Tauri
// Tauri v2 uses __TAURI_INTERNALS__, v1 used __TAURI__
function isTauri(): boolean {
  return typeof window !== 'undefined' &&
    ('__TAURI_INTERNALS__' in window || '__TAURI__' in window);
}

// Get health endpoint URL
function getHealthUrl(): string {
  return isTauri() ? 'http://localhost:8000/health' : '/health';
}

interface HealthResponse {
  status: string;
  app: string;
  version: string;
  worker_running: boolean;
  queue_size: number;
  websocket_connections: number;
}

type ConnectionStatus = 'connected' | 'disconnected' | 'checking';

export function BackendStatus() {
  const [status, setStatus] = useState<ConnectionStatus>('checking');
  const [healthData, setHealthData] = useState<HealthResponse | null>(null);
  const [lastCheck, setLastCheck] = useState<Date | null>(null);
  const [showDetails, setShowDetails] = useState(false);

  const checkHealth = useCallback(async () => {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);

      const response = await fetch(getHealthUrl(), {
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      if (response.ok) {
        const data: HealthResponse = await response.json();
        setHealthData(data);
        setStatus('connected');
        logger.debug('Health', 'Backend health check passed', data);
      } else {
        setStatus('disconnected');
        setHealthData(null);
        logger.warn('Health', 'Backend returned non-OK status', { status: response.status });
      }
    } catch (error) {
      setStatus('disconnected');
      setHealthData(null);
      logger.error('Health', 'Backend health check failed', {
        error: error instanceof Error ? error.message : String(error),
      });
    }
    setLastCheck(new Date());
  }, []);

  // Initial check and periodic polling
  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 10000); // Check every 10 seconds
    return () => clearInterval(interval);
  }, [checkHealth]);

  const statusConfig = {
    connected: {
      color: 'bg-green-500',
      pulseColor: 'bg-green-400',
      text: 'Connected',
      textColor: 'text-green-400',
    },
    disconnected: {
      color: 'bg-red-500',
      pulseColor: 'bg-red-400',
      text: 'Disconnected',
      textColor: 'text-red-400',
    },
    checking: {
      color: 'bg-yellow-500',
      pulseColor: 'bg-yellow-400',
      text: 'Checking...',
      textColor: 'text-yellow-400',
    },
  };

  const config = statusConfig[status];

  return (
    <div className="relative">
      <button
        onClick={() => setShowDetails(!showDetails)}
        className={cn(
          'flex items-center gap-2 px-3 py-1.5 rounded-lg',
          'bg-surface-light/50 hover:bg-surface-light transition-colors',
          'border border-border/50'
        )}
        title={`Backend: ${config.text}`}
      >
        {/* Status indicator with pulse animation */}
        <span className="relative flex h-3 w-3">
          {status === 'connected' && (
            <span
              className={cn(
                'animate-ping absolute inline-flex h-full w-full rounded-full opacity-75',
                config.pulseColor
              )}
            />
          )}
          <span
            className={cn(
              'relative inline-flex rounded-full h-3 w-3',
              config.color
            )}
          />
        </span>
        <span className={cn('text-xs font-medium', config.textColor)}>
          Backend
        </span>
      </button>

      {/* Details dropdown */}
      {showDetails && (
        <div className="absolute top-full left-0 mt-2 w-64 p-3 bg-surface border border-border rounded-lg shadow-xl z-50">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold text-text-primary">
                Server Status
              </span>
              <span className={cn('text-xs font-medium', config.textColor)}>
                {config.text}
              </span>
            </div>

            {healthData && (
              <>
                <div className="border-t border-border pt-2 space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="text-text-muted">App</span>
                    <span className="text-text-secondary">{healthData.app}</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-text-muted">Version</span>
                    <span className="text-text-secondary">{healthData.version}</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-text-muted">Worker</span>
                    <span className={healthData.worker_running ? 'text-green-400' : 'text-red-400'}>
                      {healthData.worker_running ? 'Running' : 'Stopped'}
                    </span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-text-muted">Queue Size</span>
                    <span className="text-text-secondary">{healthData.queue_size}</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-text-muted">WS Connections</span>
                    <span className="text-text-secondary">{healthData.websocket_connections}</span>
                  </div>
                </div>
              </>
            )}

            {lastCheck && (
              <div className="border-t border-border pt-2">
                <div className="flex justify-between text-xs">
                  <span className="text-text-muted">Last Check</span>
                  <span className="text-text-secondary">
                    {lastCheck.toLocaleTimeString()}
                  </span>
                </div>
              </div>
            )}

            <button
              onClick={(e) => {
                e.stopPropagation();
                checkHealth();
              }}
              className="w-full mt-2 px-2 py-1 text-xs bg-primary/20 hover:bg-primary/30 text-primary rounded transition-colors"
            >
              Check Now
            </button>
          </div>
        </div>
      )}

      {/* Click outside to close */}
      {showDetails && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setShowDetails(false)}
        />
      )}
    </div>
  );
}
