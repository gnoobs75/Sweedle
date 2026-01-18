/**
 * WorkflowWizard - Main 5-stage wizard container
 *
 * Replaces the GenerationPanel in the left panel,
 * providing a step-by-step workflow for:
 * 1. Upload & Mesh Generation
 * 2. Texturing
 * 3. Rigging
 * 4. Animation
 * 5. Export
 */

import { useEffect, useRef } from 'react';
import { useWorkflowStore } from '../../stores/workflowStore';
import { useSettingsStore } from '../../stores/settingsStore';
import { useGenerationLogStore } from '../../stores/generationLogStore';
import { WorkflowStepper } from './WorkflowStepper';
import { VRAMIndicator } from './VRAMIndicator';
import { ApprovalControls } from './ApprovalControls';
import { UploadStage, MeshStage, TextureStage, RiggingStage, AnimationStage, ExportStage } from './stages';
import { TutorialPanel, TutorialToggle } from '../tutorial';
import { getTutorialForStage } from '../../content/tutorials';
import { GenerationLogModal } from '../generation/GenerationLogModal';

export function WorkflowWizard() {
  const { isActive, currentStage, stages, resetWorkflow, isProcessing, currentJobId: workflowJobId } = useWorkflowStore();
  const { tutorialMode } = useSettingsStore();
  const {
    isModalOpen,
    closeModal,
    logs,
    progress,
    stage: logStage,
    isComplete,
    isFailed,
    title,
    openModal,
  } = useGenerationLogStore();

  // Track previous job ID to detect when a new job starts
  const prevJobIdRef = useRef<string | null>(null);

  // Determine the current stage ID for tutorial
  const getCurrentStageId = (): string => {
    if (currentStage === 'upload') {
      if (stages.upload.status === 'completed') {
        return 'mesh';
      }
      return 'upload';
    }
    return currentStage;
  };

  const currentStageId = getCurrentStageId();
  const tutorial = getTutorialForStage(currentStageId);

  // Auto-open modal when mesh or texture processing starts
  useEffect(() => {
    // Only trigger when we get a NEW job ID during processing
    if (isProcessing && workflowJobId && workflowJobId !== prevJobIdRef.current) {
      prevJobIdRef.current = workflowJobId;

      // Determine title based on current stage
      let modalTitle = 'NEURAL PROCESSING';
      if (currentStage === 'mesh' || currentStage === 'upload') {
        modalTitle = 'MESH GENERATION';
      } else if (currentStage === 'texture') {
        modalTitle = 'TEXTURE SYNTHESIS';
      }

      openModal(workflowJobId, undefined, modalTitle);
    }

    // Reset when processing stops
    if (!isProcessing) {
      prevJobIdRef.current = null;
    }
  }, [isProcessing, workflowJobId, currentStage, openModal]);

  // Determine which stage component to show
  const renderStageContent = () => {
    // If we're at upload stage and haven't uploaded yet, show upload
    if (currentStage === 'upload') {
      // Check if we need to transition to mesh stage
      if (stages.upload.status === 'completed') {
        return <MeshStage />;
      }
      return <UploadStage />;
    }

    // After upload is complete, show the current stage
    switch (currentStage) {
      case 'mesh':
        return <MeshStage />;
      case 'texture':
        return <TextureStage />;
      case 'rigging':
        return <RiggingStage />;
      case 'animation':
        return <AnimationStage />;
      case 'export':
        return <ExportStage />;
      default:
        return <UploadStage />;
    }
  };

  return (
    <div className="flex flex-col h-full bg-gray-900">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700">
        <h2 className="text-lg font-semibold text-white">Asset Workflow</h2>
        <div className="flex items-center gap-2">
          <TutorialToggle compact />
          {isActive && (
            <button
              onClick={resetWorkflow}
              className="text-xs text-gray-400 hover:text-gray-300 transition-colors"
            >
              Start New
            </button>
          )}
        </div>
      </div>

      {/* Step indicator */}
      <WorkflowStepper />

      {/* VRAM status */}
      <VRAMIndicator />

      {/* Current stage content */}
      <div className="flex-1 overflow-auto p-4 space-y-4">
        {/* Tutorial Panel - shown when tutorial mode is enabled */}
        {tutorialMode && tutorial && (
          <TutorialPanel tutorial={tutorial} stageId={currentStageId} />
        )}

        {/* Stage content */}
        {renderStageContent()}
      </div>

      {/* Approval controls */}
      <ApprovalControls />

      {/* Generation Log Modal - auto-opens when processing starts */}
      <GenerationLogModal
        isOpen={isModalOpen}
        onClose={closeModal}
        logs={logs}
        progress={progress}
        stage={logStage}
        isComplete={isComplete}
        isFailed={isFailed}
        title={title}
      />
    </div>
  );
}
