/**
 * Animation timeline with playback controls.
 *
 * Note: Animation playback is handled by the GLBViewer's AnimationMixer.
 * This component just provides UI controls and displays the current time.
 */

import { useAnimationStore } from '../../stores/animationStore';

export function AnimationTimeline() {
  const {
    isPlaying,
    currentTime,
    clips,
    activeClipId,
    play,
    pause,
    stop,
    seek,
  } = useAnimationStore();

  // Get active clip duration
  const activeClip = clips.find((c) => c.id === activeClipId);
  const duration = activeClip?.duration || 4.0;
  const loopMode = activeClip?.loop_mode || 'loop';

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 100);
    return `${mins}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(2, '0')}`;
  };

  if (!activeClipId || clips.length === 0) {
    return null;
  }

  return (
    <div className="p-4 bg-gray-800/30 border-t border-gray-700">
      {/* Transport Controls */}
      <div className="flex items-center justify-center gap-4 mb-4">
        {/* Stop */}
        <button
          onClick={stop}
          className="p-2 text-gray-400 hover:text-white transition-colors"
          title="Stop"
        >
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <rect x="5" y="5" width="10" height="10" rx="1" />
          </svg>
        </button>

        {/* Play/Pause */}
        <button
          onClick={isPlaying ? pause : play}
          className="p-3 bg-indigo-600 hover:bg-indigo-500 rounded-full text-white transition-colors"
          title={isPlaying ? 'Pause' : 'Play'}
        >
          {isPlaying ? (
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <rect x="5" y="4" width="3" height="12" rx="1" />
              <rect x="12" y="4" width="3" height="12" rx="1" />
            </svg>
          ) : (
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path d="M6.5 4.5a1 1 0 011.5-.86l8 5a1 1 0 010 1.72l-8 5A1 1 0 016.5 14.5v-10z" />
            </svg>
          )}
        </button>

        {/* Loop mode indicator */}
        <div className="text-xs text-gray-400 capitalize">
          {loopMode === 'loop' && '🔁 Loop'}
          {loopMode === 'once' && '1️⃣ Once'}
          {loopMode === 'pingpong' && '↔️ Ping-pong'}
        </div>
      </div>

      {/* Timeline Slider */}
      <div className="flex items-center gap-3">
        <span className="text-xs text-gray-400 w-14 text-right font-mono">
          {formatTime(currentTime)}
        </span>
        <input
          type="range"
          min={0}
          max={duration}
          step={0.01}
          value={currentTime}
          onChange={(e) => seek(parseFloat(e.target.value))}
          className="flex-1 h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer
                     [&::-webkit-slider-thumb]:appearance-none
                     [&::-webkit-slider-thumb]:w-4
                     [&::-webkit-slider-thumb]:h-4
                     [&::-webkit-slider-thumb]:bg-indigo-500
                     [&::-webkit-slider-thumb]:rounded-full
                     [&::-webkit-slider-thumb]:cursor-pointer"
        />
        <span className="text-xs text-gray-400 w-14 font-mono">
          {formatTime(duration)}
        </span>
      </div>

      {/* Active clip name */}
      <div className="text-center text-xs text-gray-500 mt-2">
        Playing: {activeClip?.name}
      </div>
    </div>
  );
}
