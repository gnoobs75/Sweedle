/**
 * DebugPanel - View and export application logs
 * Toggle with Ctrl+Shift+D
 */

import { useState, useEffect, useCallback } from 'react';
import { logger, type LogEntry, type LogLevel } from '../../lib/logger';
import { cn } from '../../lib/utils';
import { Button } from './Button';

const LEVEL_COLORS: Record<LogLevel, string> = {
  debug: 'text-text-muted',
  info: 'text-primary',
  warn: 'text-warning',
  error: 'text-error',
};

const LEVEL_BG: Record<LogLevel, string> = {
  debug: 'bg-surface-light',
  info: 'bg-primary/10',
  warn: 'bg-warning/10',
  error: 'bg-error/10',
};

export function DebugPanel() {
  const [isOpen, setIsOpen] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [filter, setFilter] = useState<LogLevel | 'all'>('all');
  const [categoryFilter, setCategoryFilter] = useState<string>('');
  const [autoScroll, setAutoScroll] = useState(true);

  // Toggle with keyboard shortcut
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.shiftKey && e.key === 'D') {
        e.preventDefault();
        setIsOpen(prev => !prev);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Subscribe to log updates
  useEffect(() => {
    setLogs(logger.getLogs());
    return logger.subscribe(setLogs);
  }, []);

  // Auto-scroll effect
  useEffect(() => {
    if (autoScroll && isOpen) {
      const container = document.getElementById('debug-log-container');
      if (container) {
        container.scrollTop = container.scrollHeight;
      }
    }
  }, [logs, autoScroll, isOpen]);

  const filteredLogs = logs.filter(log => {
    if (filter !== 'all' && log.level !== filter) return false;
    if (categoryFilter && !log.category.toLowerCase().includes(categoryFilter.toLowerCase())) {
      return false;
    }
    return true;
  });

  const categories = [...new Set(logs.map(log => log.category))];

  const handleExport = useCallback(() => {
    const data = logger.exportLogs();
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `sweedle-logs-${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, []);

  const handleClear = useCallback(() => {
    logger.clear();
  }, []);

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    const time = date.toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
    const ms = date.getMilliseconds().toString().padStart(3, '0');
    return `${time}.${ms}`;
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-4 left-4 z-50 p-2 bg-surface-light/80 backdrop-blur rounded-lg border border-border hover:bg-surface-lighter transition-colors text-xs text-text-muted"
        title="Open Debug Panel (Ctrl+Shift+D)"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
        </svg>
      </button>
    );
  }

  return (
    <div className="fixed bottom-4 left-4 z-50 w-[600px] max-w-[calc(100vw-2rem)] bg-surface/95 backdrop-blur-sm rounded-lg border border-border shadow-2xl flex flex-col max-h-[60vh]">
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-border">
        <div className="flex items-center gap-3">
          <h3 className="text-sm font-semibold text-text-primary">Debug Logs</h3>
          <span className="text-xs text-text-muted">{filteredLogs.length} entries</span>
        </div>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="ghost" onClick={handleExport}>
            Export
          </Button>
          <Button size="sm" variant="ghost" onClick={handleClear}>
            Clear
          </Button>
          <button
            onClick={() => setIsOpen(false)}
            className="p-1 hover:bg-surface-light rounded"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-2 p-2 border-b border-border bg-surface-light/50">
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value as LogLevel | 'all')}
          className="text-xs bg-surface border border-border rounded px-2 py-1 text-text-primary"
        >
          <option value="all">All Levels</option>
          <option value="debug">Debug</option>
          <option value="info">Info</option>
          <option value="warn">Warning</option>
          <option value="error">Error</option>
        </select>

        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          className="text-xs bg-surface border border-border rounded px-2 py-1 text-text-primary"
        >
          <option value="">All Categories</option>
          {categories.map(cat => (
            <option key={cat} value={cat}>{cat}</option>
          ))}
        </select>

        <label className="flex items-center gap-1 text-xs text-text-muted ml-auto">
          <input
            type="checkbox"
            checked={autoScroll}
            onChange={(e) => setAutoScroll(e.target.checked)}
            className="w-3 h-3"
          />
          Auto-scroll
        </label>
      </div>

      {/* Log entries */}
      <div
        id="debug-log-container"
        className="flex-1 overflow-y-auto p-2 font-mono text-xs space-y-1"
      >
        {filteredLogs.length === 0 ? (
          <p className="text-text-muted text-center py-4">No logs yet</p>
        ) : (
          filteredLogs.map((log) => (
            <div
              key={log.id}
              className={cn(
                'rounded px-2 py-1',
                LEVEL_BG[log.level]
              )}
            >
              <div className="flex items-start gap-2">
                <span className="text-text-muted whitespace-nowrap">
                  {formatTime(log.timestamp)}
                </span>
                <span className={cn('font-semibold uppercase w-12', LEVEL_COLORS[log.level])}>
                  {log.level}
                </span>
                <span className="text-primary/70">[{log.category}]</span>
                <span className="text-text-primary flex-1">{log.message}</span>
              </div>
              {log.data !== undefined && (
                <pre className="mt-1 ml-[7.5rem] text-text-secondary overflow-x-auto">
                  {typeof log.data === 'string' ? log.data : JSON.stringify(log.data, null, 2)}
                </pre>
              )}
              {log.stack && (
                <pre className="mt-1 ml-[7.5rem] text-error/70 overflow-x-auto text-[10px]">
                  {log.stack}
                </pre>
              )}
            </div>
          ))
        )}
      </div>

      {/* Footer hint */}
      <div className="px-3 py-1.5 border-t border-border text-[10px] text-text-muted">
        Press Ctrl+Shift+D to toggle
      </div>
    </div>
  );
}
