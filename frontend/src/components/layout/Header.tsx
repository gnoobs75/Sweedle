/**
 * Header Component
 */

import { useUIStore } from '../../stores/uiStore';
import { useQueueStore } from '../../stores/queueStore';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { BackendStatus } from '../ui/BackendStatus';
import { cn } from '../../lib/utils';

export function Header() {
  const { mode, toggleMode, activePanels, togglePanel } = useUIStore();
  const { queueStatus } = useQueueStore();

  return (
    <header className="h-14 flex items-center justify-between px-4 border-b border-border bg-surface">
      {/* Logo */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <svg
            className="w-8 h-8 text-primary"
            viewBox="0 0 32 32"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M16 2L4 9v14l12 7 12-7V9L16 2z"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinejoin="round"
            />
            <path
              d="M16 16L4 9M16 16v14M16 16l12-7"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinejoin="round"
            />
          </svg>
          <span className="text-xl font-bold text-text-primary">Sweedle</span>
        </div>
        <Badge variant="primary" size="sm">
          v0.1.0
        </Badge>
      </div>

      {/* Center - Mode Toggle */}
      <div className="flex items-center gap-2">
        <div className="flex bg-surface-light rounded-lg p-1">
          <button
            onClick={() => mode !== 'simple' && toggleMode()}
            className={cn(
              'px-4 py-1.5 text-sm font-medium rounded-md transition-all',
              mode === 'simple'
                ? 'bg-primary text-white shadow-sm'
                : 'text-text-secondary hover:text-text-primary'
            )}
          >
            Simple
          </button>
          <button
            onClick={() => mode !== 'advanced' && toggleMode()}
            className={cn(
              'px-4 py-1.5 text-sm font-medium rounded-md transition-all',
              mode === 'advanced'
                ? 'bg-primary text-white shadow-sm'
                : 'text-text-secondary hover:text-text-primary'
            )}
          >
            Advanced
          </button>
        </div>
      </div>

      {/* Right - Panel Toggles & Queue */}
      <div className="flex items-center gap-3">
        {/* Panel Toggles */}
        <div className="flex items-center gap-1">
          <Button
            variant={activePanels.includes('generation') ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => togglePanel('generation')}
            title="Generation Panel"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
          </Button>
          <Button
            variant={activePanels.includes('library') ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => togglePanel('library')}
            title="Asset Library"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
            </svg>
          </Button>
          <Button
            variant={activePanels.includes('queue') ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => togglePanel('queue')}
            title="Job Queue"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
            </svg>
          </Button>
        </div>

        {/* Backend Status */}
        <BackendStatus />

        {/* Queue Status */}
        <div className="flex items-center gap-2 px-3 py-1.5 bg-surface-light rounded-lg">
          <span className="text-xs text-text-muted">Queue:</span>
          <span className="text-sm font-mono font-medium text-text-primary">
            {queueStatus.queueSize}
          </span>
          {queueStatus.processingCount > 0 && (
            <Badge variant="primary" size="sm" dot>
              Processing
            </Badge>
          )}
        </div>
      </div>
    </header>
  );
}
