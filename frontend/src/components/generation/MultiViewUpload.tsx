/**
 * MultiViewUpload - Upload multiple view images for enhanced 3D generation
 */

import { useState, useCallback } from 'react';
import {
  generateFromMultiView,
  type MultiViewAngle,
  type MultiViewImage,
  type GenerationParameters,
} from '../../services/api/generation';

interface MultiViewUploadProps {
  onGenerationStarted?: (jobId: string, assetId: string) => void;
  parameters: GenerationParameters;
}

interface ViewSlot {
  angle: MultiViewAngle;
  label: string;
  description: string;
  required: boolean;
  file?: File;
  preview?: string;
}

const VIEW_SLOTS: ViewSlot[] = [
  { angle: 'front', label: 'Front', description: 'View from the front', required: true },
  { angle: 'back', label: 'Back', description: 'View from behind', required: true },
  { angle: 'left', label: 'Left', description: 'View from left side', required: false },
  { angle: 'right', label: 'Right', description: 'View from right side', required: false },
  { angle: 'top', label: 'Top', description: 'View from above', required: false },
  { angle: 'bottom', label: 'Bottom', description: 'View from below', required: false },
];

export function MultiViewUpload({ onGenerationStarted, parameters }: MultiViewUploadProps) {
  const [viewSlots, setViewSlots] = useState<ViewSlot[]>(VIEW_SLOTS.map(s => ({ ...s })));
  const [name, setName] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileSelect = useCallback((angle: MultiViewAngle, file: File | null) => {
    setViewSlots(prev => prev.map(slot => {
      if (slot.angle === angle) {
        return {
          ...slot,
          file: file || undefined,
          preview: file ? URL.createObjectURL(file) : undefined,
        };
      }
      return slot;
    }));
  }, []);

  const handleDrop = useCallback((angle: MultiViewAngle, e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) {
      handleFileSelect(angle, file);
    }
  }, [handleFileSelect]);

  const getFilledSlots = useCallback(() => {
    return viewSlots.filter(s => s.file);
  }, [viewSlots]);

  const canGenerate = useCallback(() => {
    const filled = getFilledSlots();
    // Need at least 2 images, and both required slots (front/back) must be filled
    const hasFront = viewSlots.find(s => s.angle === 'front')?.file;
    const hasBack = viewSlots.find(s => s.angle === 'back')?.file;
    return filled.length >= 2 && hasFront && hasBack;
  }, [getFilledSlots, viewSlots]);

  const handleGenerate = async () => {
    if (!canGenerate()) return;

    setIsGenerating(true);
    setError(null);

    try {
      const images: MultiViewImage[] = viewSlots
        .filter(s => s.file)
        .map(s => ({ file: s.file!, angle: s.angle }));

      const result = await generateFromMultiView({
        images,
        name: name || undefined,
        parameters,
      });

      onGenerationStarted?.(result.jobId, result.assetId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start generation');
    } finally {
      setIsGenerating(false);
    }
  };

  const clearAll = () => {
    setViewSlots(VIEW_SLOTS.map(s => ({ ...s })));
    setName('');
    setError(null);
  };

  const filledCount = getFilledSlots().length;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium text-white flex items-center gap-2">
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          Multi-View Input
        </h3>
        {filledCount > 0 && (
          <button
            onClick={clearAll}
            className="text-xs text-gray-400 hover:text-white"
          >
            Clear All
          </button>
        )}
      </div>

      <p className="text-xs text-gray-400">
        Upload images from different angles for better 3D reconstruction.
        Front and Back views are required. More views = better quality.
      </p>

      {/* View Slots Grid */}
      <div className="grid grid-cols-2 gap-3">
        {viewSlots.map((slot) => (
          <div
            key={slot.angle}
            className={`relative border-2 border-dashed rounded-lg p-2 transition-colors ${
              slot.file
                ? 'border-green-500 bg-green-900/10'
                : slot.required
                ? 'border-yellow-500/50 bg-yellow-900/5'
                : 'border-gray-700 hover:border-gray-600'
            }`}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => handleDrop(slot.angle, e)}
          >
            {slot.file ? (
              <div className="relative">
                <img
                  src={slot.preview}
                  alt={slot.label}
                  className="w-full h-20 object-cover rounded"
                />
                <button
                  onClick={() => handleFileSelect(slot.angle, null)}
                  className="absolute -top-1 -right-1 w-5 h-5 bg-red-600 rounded-full flex items-center justify-center text-white text-xs hover:bg-red-500"
                >
                  ×
                </button>
                <div className="absolute bottom-1 left-1 px-1.5 py-0.5 bg-black/70 rounded text-[10px] text-white">
                  {slot.label}
                </div>
              </div>
            ) : (
              <label className="flex flex-col items-center justify-center h-20 cursor-pointer">
                <input
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={(e) => handleFileSelect(slot.angle, e.target.files?.[0] || null)}
                />
                <svg className="w-6 h-6 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                <span className="text-xs text-gray-400 mt-1">{slot.label}</span>
                {slot.required && (
                  <span className="text-[10px] text-yellow-500">Required</span>
                )}
              </label>
            )}
          </div>
        ))}
      </div>

      {/* Status */}
      <div className="flex items-center gap-2 text-xs">
        <span className={filledCount >= 2 ? 'text-green-400' : 'text-yellow-400'}>
          {filledCount}/6 views added
        </span>
        {filledCount < 2 && (
          <span className="text-gray-500">• Need at least 2 views</span>
        )}
        {filledCount >= 4 && (
          <span className="text-green-500">• Excellent coverage!</span>
        )}
      </div>

      {/* Name Input */}
      <div>
        <label className="block text-xs text-gray-400 mb-1">Asset Name (optional)</label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g., Character Model"
          className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm text-white placeholder-gray-500"
        />
      </div>

      {/* Error */}
      {error && (
        <div className="p-2 bg-red-900/20 border border-red-700/30 rounded text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Generate Button */}
      <button
        onClick={handleGenerate}
        disabled={!canGenerate() || isGenerating}
        className={`w-full py-3 text-sm font-medium rounded-lg transition-colors flex items-center justify-center gap-2 ${
          canGenerate() && !isGenerating
            ? 'bg-indigo-600 hover:bg-indigo-500 text-white'
            : 'bg-gray-700 text-gray-400 cursor-not-allowed'
        }`}
      >
        {isGenerating ? (
          <>
            <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            Starting Generation...
          </>
        ) : (
          <>
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            Generate from {filledCount} Views
          </>
        )}
      </button>

      {/* Tips */}
      <div className="p-3 bg-gray-800/50 rounded-lg">
        <h4 className="text-xs font-medium text-gray-300 mb-2">Tips for best results</h4>
        <ul className="text-[10px] text-gray-400 space-y-1">
          <li>• Use consistent lighting across all images</li>
          <li>• Keep the object centered in each photo</li>
          <li>• Use a plain background (white, black, or transparent)</li>
          <li>• Match the scale/distance in each view</li>
          <li>• Front + Back + Left + Right gives 4-view coverage</li>
        </ul>
      </div>
    </div>
  );
}
