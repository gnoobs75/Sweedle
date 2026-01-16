/**
 * AnimationStage - Stage 4: Add animations to rigged model
 */

import { useWorkflowStore } from '../../../stores/workflowStore';
import { useAnimationStore } from '../../../stores/animationStore';
import { useRiggingStore } from '../../../stores/riggingStore';
import { AnimationStudio } from '../../animation';

export function AnimationStage() {
  const { stages } = useWorkflowStore();
  const { clips } = useAnimationStore();
  const { skeletonData } = useRiggingStore();

  const status = stages.animation.status;
  const isSkipped = status === 'skipped';
  const isApproved = status === 'approved';

  // If rigging was skipped, show message
  if (!skeletonData) {
    return (
      <div className="space-y-4">
        <h3 className="text-lg font-medium text-white">Animation</h3>

        <div className="p-4 bg-gray-800/50 border border-gray-700 rounded-lg">
          <div className="flex items-center gap-2 text-amber-400">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
            <span className="font-medium">Rigging Required</span>
          </div>
          <p className="mt-2 text-sm text-gray-400">
            Animation requires a rigged model. The rigging step was skipped, so you
            cannot add animations. Click "Skip to Export" to export without animations.
          </p>
        </div>
      </div>
    );
  }

  if (isSkipped) {
    return (
      <div className="space-y-4">
        <h3 className="text-lg font-medium text-white">Animation</h3>

        <div className="p-4 bg-gray-800/50 border border-gray-700 rounded-lg">
          <div className="flex items-center gap-2 text-gray-400">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M13 5l7 7-7 7M5 5l7 7-7 7"
              />
            </svg>
            <span className="font-medium">Stage Skipped</span>
          </div>
          <p className="mt-2 text-sm text-gray-500">
            Animation was skipped. The model will be exported without animations.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-medium text-white">Animation</h3>

      {isApproved ? (
        <div className="space-y-4">
          <div className="p-4 bg-green-900/20 border border-green-700/30 rounded-lg">
            <div className="flex items-center gap-2 text-green-400">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
              <span className="font-medium">Animations Ready</span>
            </div>
          </div>

          {clips.length > 0 && (
            <div className="p-3 bg-gray-800/50 rounded-lg">
              <h4 className="text-sm font-medium text-gray-300 mb-2">
                Applied Animations
              </h4>
              <ul className="space-y-1">
                {clips.map((clip) => (
                  <li key={clip.id} className="text-sm text-gray-400 flex items-center gap-2">
                    <span className="w-2 h-2 bg-indigo-400 rounded-full" />
                    {clip.name} ({clip.duration.toFixed(1)}s)
                  </li>
                ))}
              </ul>
            </div>
          )}

          <p className="text-sm text-gray-400">
            {clips.length > 0
              ? `${clips.length} animation(s) will be included in the export.`
              : 'No animations added. The model will be exported with rigging only.'}
          </p>

          <div className="p-3 bg-gray-800/30 rounded text-sm text-gray-400">
            <strong className="text-gray-300">Next:</strong> Click "Approve & Continue" to
            proceed to export.
          </div>
        </div>
      ) : (
        <>
          <p className="text-sm text-gray-400">
            Add animations to bring your {skeletonData.characterType} model to life.
            Select from preset animations or skip to export without animations.
          </p>

          {/* Embed Animation Studio */}
          <div className="bg-gray-800/30 rounded-lg border border-gray-700 overflow-hidden">
            <AnimationStudio />
          </div>

          {clips.length > 0 && (
            <div className="p-3 bg-indigo-900/20 border border-indigo-700/30 rounded text-sm text-indigo-300">
              <strong>{clips.length}</strong> animation(s) applied. Click "Approve &
              Continue" when ready.
            </div>
          )}
        </>
      )}
    </div>
  );
}
