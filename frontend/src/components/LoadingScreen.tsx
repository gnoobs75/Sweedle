/**
 * LoadingScreen - Shows while waiting for backend to be ready
 */

import { useEffect, useState } from 'react';

interface ReadinessStatus {
  ready: boolean;
  status_message: string;
  components: {
    worker: boolean;
    queue: boolean;
    websocket: boolean;
    pipeline: boolean;
    gpu: boolean;
  };
  gpu: {
    available: boolean;
    name: string;
    vram_gb: number;
  } | null;
}

interface LoadingScreenProps {
  onReady: () => void;
}

export function LoadingScreen({ onReady }: LoadingScreenProps) {
  const [status, setStatus] = useState<ReadinessStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);
  const [dots, setDots] = useState('');

  // Animate loading dots
  useEffect(() => {
    const interval = setInterval(() => {
      setDots((prev) => (prev.length >= 3 ? '' : prev + '.'));
    }, 500);
    return () => clearInterval(interval);
  }, []);

  // Poll backend readiness
  useEffect(() => {
    let cancelled = false;
    let timeoutId: number;

    const checkReady = async () => {
      try {
        const response = await fetch('/api/ready');
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        const data: ReadinessStatus = await response.json();

        if (cancelled) return;

        setStatus(data);
        setError(null);

        if (data.ready) {
          // Small delay to show "Ready" message
          setTimeout(() => {
            if (!cancelled) onReady();
          }, 500);
        } else {
          // Poll again in 1 second
          timeoutId = window.setTimeout(checkReady, 1000);
        }
      } catch (err) {
        if (cancelled) return;

        setRetryCount((prev) => prev + 1);
        setError(
          retryCount < 5
            ? 'Connecting to backend...'
            : 'Backend not responding. Is it running?'
        );

        // Retry with backoff
        const delay = Math.min(1000 * Math.pow(1.5, retryCount), 5000);
        timeoutId = window.setTimeout(checkReady, delay);
      }
    };

    checkReady();

    return () => {
      cancelled = true;
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, [onReady, retryCount]);

  const components = status?.components;

  return (
    <div className="fixed inset-0 bg-gray-900 flex flex-col items-center justify-center z-50">
      {/* Logo / Title */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-white tracking-tight">
          Sweedle
        </h1>
        <p className="text-gray-400 text-center mt-1">3D Asset Generator</p>
      </div>

      {/* Loading spinner */}
      <div className="relative mb-8">
        <div className="w-16 h-16 border-4 border-gray-700 border-t-indigo-500 rounded-full animate-spin" />
      </div>

      {/* Status message */}
      <div className="text-center mb-6">
        <p className="text-lg text-white">
          {error || status?.status_message || 'Connecting'}
          {!status?.ready && dots}
        </p>
      </div>

      {/* Component status checklist */}
      {components && (
        <div className="bg-gray-800/50 rounded-lg p-4 min-w-[280px]">
          <div className="space-y-2">
            <StatusItem label="Job Queue" ready={components.queue} />
            <StatusItem label="WebSocket" ready={components.websocket} />
            <StatusItem label="AI Pipeline" ready={components.pipeline} />
            <StatusItem label="Background Worker" ready={components.worker} />
            <StatusItem
              label={`GPU${status.gpu ? ` (${status.gpu.name})` : ''}`}
              ready={components.gpu}
              optional
            />
          </div>
        </div>
      )}

      {/* GPU info */}
      {status?.gpu && (
        <p className="mt-4 text-sm text-gray-500">
          {status.gpu.vram_gb}GB VRAM available
        </p>
      )}

      {/* Error hint */}
      {error && retryCount >= 5 && (
        <div className="mt-6 p-3 bg-red-900/20 border border-red-700/30 rounded text-sm text-red-400 max-w-md text-center">
          <p>Make sure the backend is running:</p>
          <code className="block mt-2 text-xs bg-gray-800 p-2 rounded">
            cd backend && python -m uvicorn src.main:app
          </code>
        </div>
      )}
    </div>
  );
}

interface StatusItemProps {
  label: string;
  ready: boolean;
  optional?: boolean;
}

function StatusItem({ label, ready, optional }: StatusItemProps) {
  return (
    <div className="flex items-center gap-3">
      <div
        className={`w-4 h-4 rounded-full flex items-center justify-center ${
          ready
            ? 'bg-green-500'
            : optional
            ? 'bg-gray-600'
            : 'bg-gray-700 animate-pulse'
        }`}
      >
        {ready && (
          <svg
            className="w-2.5 h-2.5 text-white"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={3}
              d="M5 13l4 4L19 7"
            />
          </svg>
        )}
      </div>
      <span
        className={`text-sm ${
          ready ? 'text-gray-300' : optional ? 'text-gray-500' : 'text-gray-400'
        }`}
      >
        {label}
      </span>
    </div>
  );
}
