/**
 * AppShell Component - Main application layout
 */

import { type ReactNode } from 'react';
import { cn } from '../../lib/utils';
import { useUIStore } from '../../stores/uiStore';
import { Header } from './Header';
import { ResizablePanel } from './ResizablePanel';

export interface AppShellProps {
  leftPanel?: ReactNode;
  centerPanel?: ReactNode;
  rightPanel?: ReactNode;
}

export function AppShell({ leftPanel, centerPanel, rightPanel }: AppShellProps) {
  const { panelLayout, setPanelLayout, isConnected } = useUIStore();

  return (
    <div className="h-screen flex flex-col bg-background text-text-primary overflow-hidden">
      <Header />

      <main className="flex-1 flex overflow-hidden">
        {/* Left Panel */}
        {leftPanel && (
          <ResizablePanel
            direction="horizontal"
            resizeFrom="end"
            defaultSize={panelLayout.left}
            minSize={280}
            maxSize={500}
            onResize={(size) => setPanelLayout({ left: size })}
            className="border-r border-border bg-surface"
          >
            <div className="h-full overflow-y-auto">{leftPanel}</div>
          </ResizablePanel>
        )}

        {/* Center Panel (Flexible) */}
        <div className="flex-1 min-w-0 bg-background overflow-hidden">
          {centerPanel}
        </div>

        {/* Right Panel */}
        {rightPanel && (
          <ResizablePanel
            direction="horizontal"
            resizeFrom="start"
            defaultSize={panelLayout.right}
            minSize={280}
            maxSize={500}
            onResize={(size) => setPanelLayout({ right: size })}
            className="border-l border-border bg-surface"
          >
            <div className="h-full overflow-y-auto">{rightPanel}</div>
          </ResizablePanel>
        )}
      </main>

      {/* Connection Status */}
      <div
        className={cn(
          'absolute bottom-4 right-4 flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium transition-all',
          isConnected
            ? 'bg-success/20 text-success'
            : 'bg-error/20 text-error'
        )}
      >
        <span
          className={cn(
            'w-2 h-2 rounded-full',
            isConnected ? 'bg-success animate-pulse' : 'bg-error'
          )}
        />
        {isConnected ? 'Connected' : 'Disconnected'}
      </div>
    </div>
  );
}
