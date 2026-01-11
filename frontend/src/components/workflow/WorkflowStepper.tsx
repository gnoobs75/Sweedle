/**
 * WorkflowStepper - Visual step indicator for the wizard
 */

import { useWorkflowStore, type WorkflowStage, type StageStatus } from '../../stores/workflowStore';

interface StepConfig {
  id: WorkflowStage;
  label: string;
  number: number;
}

const steps: StepConfig[] = [
  { id: 'upload', label: 'Upload', number: 1 },
  { id: 'mesh', label: 'Mesh', number: 2 },
  { id: 'texture', label: 'Texture', number: 3 },
  { id: 'rigging', label: 'Rig', number: 4 },
  { id: 'export', label: 'Export', number: 5 },
];

function getStepStyles(status: StageStatus, isCurrent: boolean): string {
  if (isCurrent) {
    return 'bg-indigo-600 text-white border-indigo-600';
  }
  switch (status) {
    case 'completed':
    case 'approved':
      return 'bg-green-600 text-white border-green-600';
    case 'processing':
      return 'bg-indigo-500 text-white border-indigo-500 animate-pulse';
    case 'skipped':
      return 'bg-gray-500 text-gray-300 border-gray-500';
    case 'failed':
      return 'bg-red-600 text-white border-red-600';
    default:
      return 'bg-gray-700 text-gray-400 border-gray-600';
  }
}

function getConnectorStyles(status: StageStatus): string {
  switch (status) {
    case 'completed':
    case 'approved':
      return 'bg-green-600';
    case 'skipped':
      return 'bg-gray-500';
    default:
      return 'bg-gray-600';
  }
}

export function WorkflowStepper() {
  const { currentStage, stages } = useWorkflowStore();

  return (
    <div className="flex items-center justify-between px-4 py-3 bg-gray-800/50 border-b border-gray-700">
      {steps.map((step, index) => {
        const status = stages[step.id].status;
        const isCurrent = currentStage === step.id;

        return (
          <div key={step.id} className="flex items-center flex-1">
            {/* Step circle */}
            <div className="flex flex-col items-center">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center border-2 text-sm font-medium transition-colors ${getStepStyles(status, isCurrent)}`}
              >
                {status === 'completed' || status === 'approved' ? (
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                ) : status === 'skipped' ? (
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7M5 5l7 7-7 7" />
                  </svg>
                ) : (
                  step.number
                )}
              </div>
              <span className={`mt-1 text-xs ${isCurrent ? 'text-indigo-400 font-medium' : 'text-gray-500'}`}>
                {step.label}
              </span>
            </div>

            {/* Connector line */}
            {index < steps.length - 1 && (
              <div className={`flex-1 h-0.5 mx-2 ${getConnectorStyles(status)}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}
