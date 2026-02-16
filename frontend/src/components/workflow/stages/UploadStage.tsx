/**
 * UploadStage - Stage 1: Image upload or text-to-image generation
 */

import { useCallback, useState } from 'react';
import { useWorkflowStore } from '../../../stores/workflowStore';
import { useGenerationStore } from '../../../stores/generationStore';
import { generateFromImage } from '../../../services/api/generation';
import { importModel } from '../../../services/api/assets';
import { TextPromptInput } from '../TextPromptInput';
import { FolderImporter } from '../../queue/FolderImporter';

type InputMode = 'upload' | 'generate' | 'batch' | 'import';

export function UploadStage() {
  const [inputMode, setInputMode] = useState<InputMode>('upload');
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

  // Handle when text-to-image generates an image
  const handleImageGenerated = useCallback((file: File, previewUrl: string) => {
    // Create object URL for preview (or use the provided one)
    setSourceImage(file);
    // Switch to showing the generated image in upload mode view
    setInputMode('upload');
  }, [setSourceImage]);

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
      <h3 className="text-lg font-medium text-white">Create Source Image</h3>

      {/* Input mode tabs */}
      <div className="flex gap-1 p-1 bg-gray-800 rounded-lg">
        <button
          onClick={() => setInputMode('upload')}
          className={`flex-1 py-2 px-3 text-sm font-medium rounded transition-colors ${
            inputMode === 'upload'
              ? 'bg-indigo-600 text-white'
              : 'text-gray-400 hover:text-white hover:bg-gray-700'
          }`}
        >
          <span className="flex items-center justify-center gap-2">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            Upload
          </span>
        </button>
        <button
          onClick={() => setInputMode('generate')}
          className={`flex-1 py-2 px-3 text-sm font-medium rounded transition-colors ${
            inputMode === 'generate'
              ? 'bg-indigo-600 text-white'
              : 'text-gray-400 hover:text-white hover:bg-gray-700'
          }`}
        >
          <span className="flex items-center justify-center gap-2">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
            Text
          </span>
        </button>
        <button
          onClick={() => setInputMode('batch')}
          className={`flex-1 py-2 px-3 text-sm font-medium rounded transition-colors ${
            inputMode === 'batch'
              ? 'bg-indigo-600 text-white'
              : 'text-gray-400 hover:text-white hover:bg-gray-700'
          }`}
        >
          <span className="flex items-center justify-center gap-2">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
            </svg>
            Batch
          </span>
        </button>
        <button
          onClick={() => setInputMode('import')}
          className={`flex-1 py-2 px-3 text-sm font-medium rounded transition-colors ${
            inputMode === 'import'
              ? 'bg-indigo-600 text-white'
              : 'text-gray-400 hover:text-white hover:bg-gray-700'
          }`}
        >
          <span className="flex items-center justify-center gap-2">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            Import
          </span>
        </button>
      </div>

      {/* Upload mode content */}
      {inputMode === 'upload' && (
        <>
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
        </>
      )}

      {/* Generate from text mode content */}
      {inputMode === 'generate' && (
        <TextPromptInput onImageGenerated={handleImageGenerated} />
      )}

      {/* Batch import mode content */}
      {inputMode === 'batch' && (
        <div className="mt-2">
          <p className="text-sm text-gray-400 mb-4">
            Drop multiple images to queue them all for 3D generation.
            Jobs will process in background while you continue working.
          </p>
          <FolderImporter
            className="border border-gray-700 rounded-lg"
            onClose={() => setInputMode('upload')}
          />
        </div>
      )}

      {/* Import existing model mode content */}
      {inputMode === 'import' && (
        <ModelImportPanel />
      )}
    </div>
  );
}

/**
 * Model Import Panel for importing existing 3D models
 */
function ModelImportPanel() {
  const [modelFile, setModelFile] = useState<File | null>(null);
  const [modelName, setModelName] = useState('');
  const [isImporting, setIsImporting] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);
  const [importSuccess, setImportSuccess] = useState<{
    assetId: string;
    name: string;
    vertexCount: number;
    faceCount: number;
  } | null>(null);

  const { setActiveAssetId, setStageStatus, setCurrentStage } = useWorkflowStore();

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setModelFile(file);
      setImportError(null);
      setImportSuccess(null);
      // Set default name from filename
      if (!modelName) {
        setModelName(file.name.replace(/\.[^/.]+$/, ''));
      }
    }
  }, [modelName]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    const validExtensions = ['.glb', '.gltf', '.fbx', '.obj'];
    if (file && validExtensions.some(ext => file.name.toLowerCase().endsWith(ext))) {
      setModelFile(file);
      setImportError(null);
      setImportSuccess(null);
      if (!modelName) {
        setModelName(file.name.replace(/\.[^/.]+$/, ''));
      }
    } else {
      setImportError('Please drop a valid 3D model file (GLB, GLTF, FBX, or OBJ)');
    }
  }, [modelName]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
  }, []);

  const handleImport = useCallback(async () => {
    if (!modelFile) return;

    setIsImporting(true);
    setImportError(null);

    try {
      const result = await importModel(modelFile, modelName || modelFile.name);

      if (result.success) {
        setImportSuccess({
          assetId: result.assetId,
          name: result.name,
          vertexCount: result.vertexCount,
          faceCount: result.faceCount,
        });
      } else {
        throw new Error(result.error || 'Import failed');
      }
    } catch (error) {
      console.error('Import failed:', error);
      setImportError(error instanceof Error ? error.message : 'Import failed');
    } finally {
      setIsImporting(false);
    }
  }, [modelFile, modelName]);

  const handleProceedToRigging = useCallback(() => {
    if (!importSuccess) return;

    // Set the imported asset as active and skip to rigging stage
    setActiveAssetId(importSuccess.assetId);
    setStageStatus('upload', 'approved');
    setStageStatus('mesh', 'skipped');
    setStageStatus('texture', 'skipped');
    setCurrentStage('rigging');
  }, [importSuccess, setActiveAssetId, setStageStatus, setCurrentStage]);

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-400">
        Import an existing 3D model to add rigging and animations.
        Supports GLB, GLTF, FBX, and OBJ formats.
      </p>

      {/* Drop zone */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        className="relative border-2 border-dashed border-gray-600 rounded-lg p-6 hover:border-indigo-500 transition-colors cursor-pointer"
      >
        <input
          type="file"
          accept=".glb,.gltf,.fbx,.obj"
          onChange={handleFileChange}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
        />

        {modelFile ? (
          <div className="flex flex-col items-center">
            <svg className="w-12 h-12 text-indigo-400 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
            </svg>
            <p className="text-sm text-white">{modelFile.name}</p>
            <p className="mt-1 text-xs text-gray-500">
              {(modelFile.size / 1024 / 1024).toFixed(2)} MB
            </p>
            <button
              onClick={(e) => {
                e.stopPropagation();
                setModelFile(null);
                setImportSuccess(null);
              }}
              className="mt-2 text-xs text-red-400 hover:text-red-300"
            >
              Remove
            </button>
          </div>
        ) : (
          <div className="flex flex-col items-center text-center">
            <svg className="w-12 h-12 text-gray-500 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
            </svg>
            <p className="text-gray-400">
              Drag and drop a 3D model, or click to browse
            </p>
            <p className="mt-1 text-xs text-gray-500">
              GLB, GLTF, FBX, OBJ
            </p>
          </div>
        )}
      </div>

      {/* Model name */}
      {modelFile && !importSuccess && (
        <div className="space-y-2">
          <label className="block text-sm text-gray-400">Asset Name</label>
          <input
            type="text"
            value={modelName}
            onChange={(e) => setModelName(e.target.value)}
            placeholder="Enter asset name"
            className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded text-white placeholder-gray-500 focus:border-indigo-500 focus:outline-none"
          />
        </div>
      )}

      {/* Error display */}
      {importError && (
        <div className="p-3 bg-red-900/20 border border-red-700/30 rounded text-sm text-red-400">
          {importError}
        </div>
      )}

      {/* Success display */}
      {importSuccess && (
        <div className="p-4 bg-green-900/20 border border-green-700/30 rounded space-y-3">
          <div className="flex items-center gap-2 text-green-400">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            <span className="font-medium">Model imported successfully!</span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="text-gray-400">
              Vertices: <span className="text-white">{importSuccess.vertexCount.toLocaleString()}</span>
            </div>
            <div className="text-gray-400">
              Faces: <span className="text-white">{importSuccess.faceCount.toLocaleString()}</span>
            </div>
          </div>
          <button
            onClick={handleProceedToRigging}
            className="w-full py-2.5 text-sm font-medium text-white bg-green-600 hover:bg-green-500 rounded transition-colors"
          >
            Proceed to Rigging
          </button>
        </div>
      )}

      {/* Import button */}
      {modelFile && !importSuccess && (
        <button
          onClick={handleImport}
          disabled={isImporting}
          className="w-full py-2.5 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-800 disabled:cursor-not-allowed rounded transition-colors"
        >
          {isImporting ? 'Importing...' : 'Import Model'}
        </button>
      )}

      {/* Info note */}
      <p className="text-xs text-gray-500">
        Imported models will be available in your library and can be rigged with
        humanoid or quadruped skeletons.
      </p>
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
