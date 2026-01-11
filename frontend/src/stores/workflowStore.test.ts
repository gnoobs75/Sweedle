/**
 * Workflow Store Unit Tests
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { useWorkflowStore } from './workflowStore';

describe('workflowStore', () => {
  beforeEach(() => {
    // Reset store to initial state before each test
    useWorkflowStore.getState().resetWorkflow();
  });

  describe('initial state', () => {
    it('should have correct initial state', () => {
      const state = useWorkflowStore.getState();

      expect(state.isActive).toBe(false);
      expect(state.activeAssetId).toBeNull();
      expect(state.currentStage).toBe('upload');
      expect(state.isProcessing).toBe(false);
      expect(state.progress).toBe(0);
      expect(state.stages.upload.status).toBe('pending');
      expect(state.stages.mesh.status).toBe('pending');
      expect(state.stages.texture.status).toBe('pending');
      expect(state.stages.rigging.status).toBe('pending');
      expect(state.stages.export.status).toBe('pending');
    });
  });

  describe('startWorkflow', () => {
    it('should activate workflow and set upload to completed', () => {
      const mockFile = new File(['test'], 'test.png', { type: 'image/png' });
      useWorkflowStore.getState().startWorkflow(mockFile, 'Test Asset');

      const state = useWorkflowStore.getState();

      expect(state.isActive).toBe(true);
      expect(state.assetName).toBe('Test Asset');
      expect(state.sourceImage).toBe(mockFile);
      expect(state.stages.upload.status).toBe('completed');
      expect(state.stages.mesh.status).toBe('pending');
    });

    it('should generate asset name from file name if not provided', () => {
      const mockFile = new File(['test'], 'my-image.png', { type: 'image/png' });
      useWorkflowStore.getState().startWorkflow(mockFile);

      const state = useWorkflowStore.getState();
      expect(state.assetName).toBe('my-image');
    });
  });

  describe('setStageStatus', () => {
    it('should update stage status', () => {
      useWorkflowStore.getState().setStageStatus('mesh', 'processing');

      expect(useWorkflowStore.getState().stages.mesh.status).toBe('processing');
    });

    it('should set error on failed status', () => {
      useWorkflowStore.getState().setStageStatus('mesh', 'failed', 'Test error');

      const state = useWorkflowStore.getState();
      expect(state.stages.mesh.status).toBe('failed');
      expect(state.stages.mesh.error).toBe('Test error');
    });
  });

  describe('approveStage', () => {
    it('should mark current stage as approved and advance to next', () => {
      // Set up mesh stage as completed
      useWorkflowStore.getState().setCurrentStage('mesh');
      useWorkflowStore.getState().setStageStatus('mesh', 'completed');

      useWorkflowStore.getState().approveStage();

      const state = useWorkflowStore.getState();
      expect(state.stages.mesh.status).toBe('approved');
      expect(state.currentStage).toBe('texture');
    });

    it('should advance through all stages correctly', () => {
      // Mesh -> Texture
      useWorkflowStore.getState().setCurrentStage('mesh');
      useWorkflowStore.getState().setStageStatus('mesh', 'completed');
      useWorkflowStore.getState().approveStage();
      expect(useWorkflowStore.getState().currentStage).toBe('texture');

      // Texture -> Rigging
      useWorkflowStore.getState().setStageStatus('texture', 'completed');
      useWorkflowStore.getState().approveStage();
      expect(useWorkflowStore.getState().currentStage).toBe('rigging');

      // Rigging -> Export
      useWorkflowStore.getState().setStageStatus('rigging', 'completed');
      useWorkflowStore.getState().approveStage();
      expect(useWorkflowStore.getState().currentStage).toBe('export');
    });

    it('should stay at export stage when approving export', () => {
      useWorkflowStore.getState().setCurrentStage('export');
      useWorkflowStore.getState().setStageStatus('export', 'completed');
      useWorkflowStore.getState().approveStage();

      expect(useWorkflowStore.getState().currentStage).toBe('export');
      expect(useWorkflowStore.getState().stages.export.status).toBe('approved');
    });
  });

  describe('redoStage', () => {
    it('should reset current stage to pending', () => {
      useWorkflowStore.getState().setCurrentStage('mesh');
      useWorkflowStore.getState().setStageStatus('mesh', 'completed');
      useWorkflowStore.getState().setProcessing(true, 'job-123');

      useWorkflowStore.getState().redoStage();

      const state = useWorkflowStore.getState();
      expect(state.stages.mesh.status).toBe('pending');
      expect(state.isProcessing).toBe(false);
      expect(state.currentJobId).toBeNull();
      expect(state.progress).toBe(0);
    });

    it('should reset failed stage to pending', () => {
      useWorkflowStore.getState().setCurrentStage('texture');
      useWorkflowStore.getState().setStageStatus('texture', 'failed', 'Some error');

      useWorkflowStore.getState().redoStage();

      const state = useWorkflowStore.getState();
      expect(state.stages.texture.status).toBe('pending');
      expect(state.stages.texture.error).toBeUndefined();
    });
  });

  describe('skipToExport', () => {
    it('should skip from mesh to export', () => {
      useWorkflowStore.getState().setCurrentStage('mesh');
      useWorkflowStore.getState().setStageStatus('mesh', 'completed');

      useWorkflowStore.getState().skipToExport();

      const state = useWorkflowStore.getState();
      expect(state.stages.mesh.status).toBe('approved');
      expect(state.stages.texture.status).toBe('skipped');
      expect(state.stages.rigging.status).toBe('skipped');
      expect(state.stages.export.status).toBe('pending');
      expect(state.currentStage).toBe('export');
    });

    it('should skip from texture to export', () => {
      useWorkflowStore.getState().setCurrentStage('texture');
      useWorkflowStore.getState().setStageStatus('texture', 'completed');

      useWorkflowStore.getState().skipToExport();

      const state = useWorkflowStore.getState();
      expect(state.stages.texture.status).toBe('approved');
      expect(state.stages.rigging.status).toBe('skipped');
      expect(state.stages.export.status).toBe('pending');
      expect(state.currentStage).toBe('export');
    });
  });

  describe('cancelWorkflow', () => {
    it('should reset workflow to initial state', () => {
      // Set up an active workflow
      const mockFile = new File(['test'], 'test.png', { type: 'image/png' });
      useWorkflowStore.getState().startWorkflow(mockFile, 'Test Asset');
      useWorkflowStore.getState().setActiveAssetId('asset-123');
      useWorkflowStore.getState().setCurrentStage('mesh');
      useWorkflowStore.getState().setProcessing(true, 'job-456');

      useWorkflowStore.getState().cancelWorkflow();

      const state = useWorkflowStore.getState();
      expect(state.isActive).toBe(false);
      expect(state.activeAssetId).toBeNull();
      expect(state.currentStage).toBe('upload');
      expect(state.isProcessing).toBe(false);
      expect(state.sourceImage).toBeNull();
      expect(state.assetName).toBe('');
    });
  });

  describe('setProcessing', () => {
    it('should set processing state with job ID', () => {
      useWorkflowStore.getState().setProcessing(true, 'job-123');

      const state = useWorkflowStore.getState();
      expect(state.isProcessing).toBe(true);
      expect(state.currentJobId).toBe('job-123');
    });

    it('should clear processing state', () => {
      useWorkflowStore.getState().setProcessing(true, 'job-123');
      useWorkflowStore.getState().setProcessing(false);

      const state = useWorkflowStore.getState();
      expect(state.isProcessing).toBe(false);
      expect(state.currentJobId).toBeNull();
    });
  });

  describe('setProgress', () => {
    it('should update progress and message', () => {
      useWorkflowStore.getState().setProgress(0.5, 'Generating shape...');

      const state = useWorkflowStore.getState();
      expect(state.progress).toBe(0.5);
      expect(state.progressMessage).toBe('Generating shape...');
    });
  });

  describe('startWorkflowFromAsset', () => {
    it('should start workflow from existing asset at texture stage', () => {
      useWorkflowStore.getState().startWorkflowFromAsset('asset-123', 'texture');

      const state = useWorkflowStore.getState();
      expect(state.isActive).toBe(true);
      expect(state.activeAssetId).toBe('asset-123');
      expect(state.currentStage).toBe('texture');
      expect(state.stages.upload.status).toBe('approved');
      expect(state.stages.mesh.status).toBe('approved');
      expect(state.stages.texture.status).toBe('pending');
    });

    it('should start workflow from existing asset at rigging stage', () => {
      useWorkflowStore.getState().startWorkflowFromAsset('asset-456', 'rigging');

      const state = useWorkflowStore.getState();
      expect(state.currentStage).toBe('rigging');
      expect(state.stages.upload.status).toBe('approved');
      expect(state.stages.mesh.status).toBe('approved');
      expect(state.stages.texture.status).toBe('approved');
      expect(state.stages.rigging.status).toBe('pending');
    });
  });

  describe('setPipelineStatus', () => {
    it('should update pipeline status', () => {
      useWorkflowStore.getState().setPipelineStatus({
        shapeLoaded: true,
        vramAllocatedGb: 10,
      });

      const state = useWorkflowStore.getState();
      expect(state.pipelineStatus.shapeLoaded).toBe(true);
      expect(state.pipelineStatus.vramAllocatedGb).toBe(10);
      // Other values should remain default
      expect(state.pipelineStatus.textureLoaded).toBe(false);
    });
  });
});
