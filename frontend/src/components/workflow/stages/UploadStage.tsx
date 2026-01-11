/**
 * UploadStage - Stage 1: Image upload
 */

import { useCallback, useState } from 'react';
import { useWorkflowStore } from '../../../stores/workflowStore';
import { useGenerationStore } from '../../../stores/generationStore';
import { generateFromImage } from '../../../services/api/generation';

export function UploadStage() {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const {
    sourceImage,
    sourceImagePreview,
    assetName,
    setSourceImage,
    setAssetName,
    setCurrentStage,
    setStageStatus,
    setProcessing,
    setActiveAssetId,
  } = useWorkflowStore();

  const { parameters } = useGenerationStore();

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
        setSourceImage(file);
      }
    },
    [setSourceImage]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const file = e.dataTransfer.files?.[0];
      if (file && file.type.startsWith('image/')) {
        setSourceImage(file);
      }
    },
    [setSourceImage]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
  }, []);

  const handleStartGeneration = useCallback(async () => {
    if (!sourceImage) return;

    setIsSubmitting(true);
    setSubmitError(null);

    try {
      // Call the generation API with mesh-only settings (no texture in stage 1)
      const response = await generateFromImage({
        file: sourceImage,
        name: assetName || sourceImage.name.replace(/\.[^/.]+$/, ''),
        parameters: {
          ...parameters,
          generateTexture: false, // Mesh stage only generates shape
        },
        priority: 'normal',
      });

      // Update workflow state
      setActiveAssetId(response.assetId);
      setProcessing(true, response.jobId);
      setStageStatus('upload', 'approved');
      setStageStatus('mesh', 'processing');
      setCurrentStage('mesh');

    } catch (error) {
      console.error('Failed to start generation:', error);
      setSubmitError(error instanceof Error ? error.message : 'Failed to start generation');
      setStageStatus('mesh', 'failed', 'Failed to submit generation job');
    } finally {
      setIsSubmitting(false);
    }
  }, [sourceImage, assetName, parameters, setActiveAssetId, setProcessing, setStageStatus, setCurrentStage]);

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-medium text-white">Upload Source Image</h3>
      <p className="text-sm text-gray-400">
        Upload an image of the object you want to convert to 3D.
        For best results, use images with a clear subject and simple background.
      </p>

      {/* Drop zone */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        className="relative border-2 border-dashed border-gray-600 rounded-lg p-6 hover:border-indigo-500 transition-colors cursor-pointer"
      >
        <input
          type="file"
          accept="image/*"
          onChange={handleFileChange}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
        />

        {sourceImagePreview ? (
          <div className="flex flex-col items-center">
            <img
              src={sourceImagePreview}
              alt="Preview"
              className="max-h-48 rounded-lg object-contain"
            />
            <p className="mt-2 text-sm text-gray-400">{sourceImage?.name}</p>
            <button
              onClick={(e) => {
                e.stopPropagation();
                setSourceImage(null);
              }}
              className="mt-2 text-xs text-red-400 hover:text-red-300"
            >
              Remove
            </button>
          </div>
        ) : (
          <div className="flex flex-col items-center text-center">
            <svg
              className="w-12 h-12 text-gray-500 mb-3"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
              />
            </svg>
            <p className="text-gray-400">
              Drag and drop an image, or click to browse
            </p>
            <p className="mt-1 text-xs text-gray-500">
              PNG, JPG, WEBP up to 10MB
            </p>
          </div>
        )}
      </div>

      {/* Asset name */}
      {sourceImage && (
        <div className="space-y-2">
          <label className="block text-sm text-gray-400">Asset Name</label>
          <input
            type="text"
            value={assetName}
            onChange={(e) => setAssetName(e.target.value)}
            placeholder="Enter asset name"
            className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded text-white placeholder-gray-500 focus:border-indigo-500 focus:outline-none"
          />
        </div>
      )}

      {/* Quality Preset */}
      {sourceImage && (
        <QualityPresetSelector />
      )}

      {/* Error display */}
      {submitError && (
        <div className="p-3 bg-red-900/20 border border-red-700/30 rounded text-sm text-red-400">
          {submitError}
        </div>
      )}

      {/* Start button */}
      {sourceImage && (
        <button
          onClick={handleStartGeneration}
          disabled={isSubmitting}
          className="w-full py-2.5 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-800 disabled:cursor-not-allowed rounded transition-colors"
        >
          {isSubmitting ? 'Submitting...' : 'Generate 3D Mesh'}
        </button>
      )}
    </div>
  );
}

/**
 * Quality preset selector
 */
function QualityPresetSelector() {
  const { parameters, applyPreset } = useGenerationStore();

  // Determine current preset based on parameters
  // Preset values: fast=15 steps, standard=25 steps, quality=40 steps
  const getCurrentPreset = () => {
    if (parameters.inferenceSteps <= 15) return 'fast';
    if (parameters.inferenceSteps >= 40) return 'quality';
    return 'standard';
  };

  const currentPreset = getCurrentPreset();

  const presets = [
    {
      id: 'fast',
      label: 'Draft',
      desc: '~30s, ~2.5k verts',
      extra: 'Quick preview',
      tooltip: 'Fast iteration without texture. Great for checking shape before committing.',
    },
    {
      id: 'standard',
      label: 'Godot Ready',
      desc: '~60s, ~5k verts',
      extra: 'Recommended',
      tooltip: 'Optimized for Godot/Unity/Unreal. Perfect for game characters and props.',
    },
    {
      id: 'quality',
      label: 'Detailed',
      desc: '~90s, ~15k verts',
      extra: 'Hero assets',
      tooltip: 'Higher detail for close-up or hero assets. Still game-ready.',
    },
  ];

  return (
    <div className="space-y-2">
      <label className="block text-sm text-gray-400">Quality Preset</label>
      <div className="grid grid-cols-3 gap-2">
        {presets.map((preset) => (
          <button
            key={preset.id}
            onClick={() => applyPreset(preset.id as 'fast' | 'standard' | 'quality')}
            title={preset.tooltip}
            className={`p-2 rounded border text-center transition-colors relative group ${
              currentPreset === preset.id
                ? 'border-indigo-500 bg-indigo-900/30 text-white'
                : 'border-gray-600 bg-gray-800 text-gray-400 hover:border-gray-500'
            }`}
          >
            <div className="text-sm font-medium">{preset.label}</div>
            <div className="text-xs text-gray-500">{preset.desc}</div>
            {preset.extra === 'Recommended' && (
              <span className="absolute -top-1 -right-1 px-1.5 py-0.5 text-[10px] bg-green-600 text-white rounded-full">
                Best
              </span>
            )}
          </button>
        ))}
      </div>
      <p className="text-xs text-gray-500 mt-1">
        Hover over presets for details. All outputs are game-engine ready.
      </p>
    </div>
  );
}
