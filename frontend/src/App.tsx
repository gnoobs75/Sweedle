/**
 * Sweedle - Main Application
 */

import { useEffect, useState } from 'react';
import { AppShell } from './components/layout';
import { useWebSocket } from './hooks/useWebSocket';
import { useUIStore } from './stores/uiStore';
import { WorkflowWizard } from './components/workflow';
import { ViewerPanel } from './components/viewer/ViewerPanel';
import { LibraryPanel } from './components/library/LibraryPanel';
import { ExportPanel } from './components/export/ExportPanel';
import { RiggingPanel } from './components/rigging/RiggingPanel';
import { ToastContainer, DebugPanel, GPUMonitor } from './components/ui';
import { LoadingScreen } from './components/LoadingScreen';
import { logger } from './lib/logger';

function App() {
  const [backendReady, setBackendReady] = useState(false);

  // Initialize WebSocket connection (only after backend is ready)
  useWebSocket();

  const { activePanels, activeModal, modalData, closeModal } = useUIStore();

  // Log app initialization (once backend is ready)
  useEffect(() => {
    if (backendReady) {
      logger.info('App', 'Sweedle initialized', {
        timestamp: new Date().toISOString(),
        activePanels
      });
    }
  }, [backendReady]);

  // Show loading screen until backend is ready
  if (!backendReady) {
    return <LoadingScreen onReady={() => setBackendReady(true)} />;
  }

  return (
    <>
      <AppShell
        leftPanel={
          activePanels.includes('generation') ? <WorkflowWizard /> : null
        }
        centerPanel={<ViewerPanel />}
        rightPanel={
          activePanels.includes('library') ? <LibraryPanel /> : null
        }
      />
      <ToastContainer />
      <DebugPanel />

      {/* GPU Monitor - bottom right */}
      <div className="fixed bottom-4 right-4 z-40">
        <GPUMonitor compact pollInterval={1000} />
      </div>

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

      {/* Rigging Modal */}
      {activeModal === 'rigging' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="w-full max-w-lg max-h-[90vh] overflow-auto m-4">
            <RiggingPanel
              assetId={modalData?.assetId as string | undefined}
              onClose={closeModal}
            />
          </div>
        </div>
      )}
    </>
  );
}

export default App;
