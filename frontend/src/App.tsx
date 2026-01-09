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
import { ExportPanel } from './components/export/ExportPanel';
import { ToastContainer, DebugPanel } from './components/ui';
import { logger } from './lib/logger';

function App() {
  // Initialize WebSocket connection
  useWebSocket();

  const { activePanels, activeModal, modalData, closeModal } = useUIStore();

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

      {/* Export Modal */}
      {(activeModal === 'export' || activeModal === 'bulk-export') && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="w-full max-w-2xl max-h-[90vh] overflow-auto m-4">
            <ExportPanel
              assetId={modalData?.assetId as string | undefined}
              assetIds={modalData?.assetIds as string[] | undefined}
              onClose={closeModal}
            />
          </div>
        </div>
      )}
    </>
  );
}

export default App;
