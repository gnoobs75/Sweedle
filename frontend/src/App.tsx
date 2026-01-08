/**
 * Sweedle - Main Application
 */

import { useEffect } from 'react';
import { AppShell } from './components/layout';
import { useWebSocket } from './hooks/useWebSocket';
import { useUIStore } from './stores/uiStore';
import { GenerationPanel } from './components/generation/GenerationPanel';
import { ViewerPanel } from './components/viewer/ViewerPanel';
import { LibraryPanel } from './components/library/LibraryPanel';
import { ToastContainer, DebugPanel } from './components/ui';
import { logger } from './lib/logger';

function App() {
  // Initialize WebSocket connection
  useWebSocket();

  const { activePanels } = useUIStore();

  // Log app initialization (once)
  useEffect(() => {
    logger.info('App', 'Sweedle initialized', {
      timestamp: new Date().toISOString(),
      activePanels
    });
  }, []);

  return (
    <>
      <AppShell
        leftPanel={
          activePanels.includes('generation') ? <GenerationPanel /> : null
        }
        centerPanel={<ViewerPanel />}
        rightPanel={
          activePanels.includes('library') ? <LibraryPanel /> : null
        }
      />
      <ToastContainer />
      <DebugPanel />
    </>
  );
}

export default App;
