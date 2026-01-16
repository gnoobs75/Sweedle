/**
 * MixamoUpload - Upload and import Mixamo FBX animations.
 */

import { useState, useCallback } from 'react';
import { useViewerStore } from '../../stores/viewerStore';
import { useAnimationStore } from '../../stores/animationStore';
import { validateMixamoFbx, importMixamoAnimation } from '../../services/api/mixamo';
import type { MixamoValidateResult } from '../../services/api/mixamo';
import { Spinner } from '../ui/Spinner';

export function MixamoUpload() {
  const { currentAssetId } = useViewerStore();
  const { addClip, setError, clearError } = useAnimationStore();

  const [file, setFile] = useState<File | null>(null);
  const [customName, setCustomName] = useState('');
  const [validation, setValidation] = useState<MixamoValidateResult | null>(null);
  const [isValidating, setIsValidating] = useState(false);
  const [isImporting, setIsImporting] = useState(false);

  const handleFileSelect = useCallback(async (selectedFile: File) => {
    setFile(selectedFile);
    setValidation(null);
    setCustomName('');
    clearError();

    // Auto-validate on file select
    setIsValidating(true);
    try {
      const result = await validateMixamoFbx(selectedFile, currentAssetId || undefined);
      setValidation(result);
      // Pre-fill name from FBX
      if (result.animationName) {
        setCustomName(result.animationName);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to validate FBX');
    } finally {
      setIsValidating(false);
    }
  }, [currentAssetId, clearError, setError]);

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      handleFileSelect(selectedFile);
    }
  }, [handleFileSelect]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const droppedFile = e.dataTransfer.files?.[0];
    if (droppedFile && droppedFile.name.toLowerCase().endsWith('.fbx')) {
      handleFileSelect(droppedFile);
    }
  }, [handleFileSelect]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
  }, []);

  const handleImport = useCallback(async () => {
    if (!file || !currentAssetId || !validation?.isValid) return;

    setIsImporting(true);
    clearError();

    try {
      const clip = await importMixamoAnimation(
        file,
        currentAssetId,
        customName || undefined
      );
      addClip(clip);

      // Reset form
      setFile(null);
      setValidation(null);
      setCustomName('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to import animation');
    } finally {
      setIsImporting(false);
    }
  }, [file, currentAssetId, validation, customName, addClip, clearError, setError]);

  const handleClear = useCallback(() => {
    setFile(null);
    setValidation(null);
    setCustomName('');
    clearError();
  }, [clearError]);

  return (
    <div className="space-y-4">
      {/* Info Banner */}
      <div className="p-3 bg-indigo-900/20 border border-indigo-700/30 rounded-lg">
        <div className="flex items-start gap-2">
          <svg className="w-5 h-5 text-indigo-400 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>
            <p className="text-sm text-indigo-300 font-medium">Import from Mixamo</p>
            <p className="text-xs text-gray-400 mt-1">
              Download animations from{' '}
              <a
                href="https://www.mixamo.com/"
                target="_blank"
                rel="noopener noreferrer"
                className="text-indigo-400 hover:text-indigo-300 underline"
              >
                mixamo.com
              </a>
              {' '}as FBX format (without skin) and upload here.
            </p>
          </div>
        </div>
      </div>

      {/* Drop Zone */}
      {!file ? (
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          className="relative border-2 border-dashed border-gray-600 rounded-lg p-8 hover:border-indigo-500 transition-colors cursor-pointer"
        >
          <input
            type="file"
            accept=".fbx"
            onChange={handleFileChange}
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          />
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
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
            <p className="text-gray-400">
              Drop a Mixamo FBX file here, or click to browse
            </p>
            <p className="mt-1 text-xs text-gray-500">
              Download from Mixamo with "FBX" format selected
            </p>
          </div>
        </div>
      ) : (
        /* Validation Result */
        <div className="space-y-4">
          {/* File Info */}
          <div className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg border border-gray-700">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-indigo-600/20 rounded-lg flex items-center justify-center">
                <svg className="w-5 h-5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div>
                <p className="text-sm font-medium text-white">{file.name}</p>
                <p className="text-xs text-gray-500">
                  {(file.size / 1024).toFixed(1)} KB
                </p>
              </div>
            </div>
            <button
              onClick={handleClear}
              className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
              aria-label="Remove file"
            >
              <svg className="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Validation Status */}
          {isValidating ? (
            <div className="flex items-center justify-center p-4">
              <Spinner size="md" variant="primary" />
              <span className="ml-3 text-gray-400">Validating FBX...</span>
            </div>
          ) : validation ? (
            <div className="space-y-3">
              {/* Status Banner */}
              <div className={`p-3 rounded-lg border ${
                validation.isValid
                  ? 'bg-green-900/20 border-green-700/30'
                  : 'bg-red-900/20 border-red-700/30'
              }`}>
                <div className={`flex items-center gap-2 ${
                  validation.isValid ? 'text-green-400' : 'text-red-400'
                }`}>
                  {validation.isValid ? (
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  ) : (
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  )}
                  <span className="font-medium">
                    {validation.isValid ? 'Compatible Animation' : 'Incompatible Animation'}
                  </span>
                </div>
              </div>

              {/* Animation Details */}
              <div className="p-3 bg-gray-800/50 rounded-lg border border-gray-700">
                <h4 className="text-sm font-medium text-gray-300 mb-3">Animation Details</h4>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <span className="text-gray-500">Name:</span>{' '}
                    <span className="text-white">{validation.animationName}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">Duration:</span>{' '}
                    <span className="text-white">{validation.durationSeconds.toFixed(2)}s</span>
                  </div>
                  <div>
                    <span className="text-gray-500">Frame Rate:</span>{' '}
                    <span className="text-white">{validation.fps} FPS</span>
                  </div>
                  <div>
                    <span className="text-gray-500">Bone Coverage:</span>{' '}
                    <span className={validation.coveragePercent >= 80 ? 'text-green-400' : 'text-amber-400'}>
                      {validation.coveragePercent.toFixed(0)}%
                    </span>
                  </div>
                </div>
                <div className="mt-2 text-xs text-gray-500">
                  {validation.mappedBones} of {validation.sourceBones} bones mapped
                </div>
              </div>

              {/* Warnings */}
              {validation.warnings.length > 0 && (
                <div className="p-3 bg-amber-900/20 border border-amber-700/30 rounded-lg">
                  <div className="flex items-start gap-2">
                    <svg className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    <div>
                      <p className="text-sm text-amber-400 font-medium">Warnings</p>
                      <ul className="mt-1 text-xs text-gray-400 space-y-1">
                        {validation.warnings.map((warning, i) => (
                          <li key={i}>{warning}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              )}

              {/* Custom Name Input */}
              {validation.isValid && (
                <div className="space-y-2">
                  <label className="block text-sm text-gray-400">
                    Animation Name (optional)
                  </label>
                  <input
                    type="text"
                    value={customName}
                    onChange={(e) => setCustomName(e.target.value)}
                    placeholder={validation.animationName}
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded text-white placeholder-gray-500 focus:border-indigo-500 focus:outline-none"
                  />
                </div>
              )}

              {/* Import Button */}
              {validation.isValid && (
                <button
                  onClick={handleImport}
                  disabled={isImporting}
                  className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {isImporting ? (
                    <>
                      <Spinner size="sm" variant="white" />
                      Importing...
                    </>
                  ) : (
                    <>
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                      </svg>
                      Import Animation
                    </>
                  )}
                </button>
              )}
            </div>
          ) : null}
        </div>
      )}

      {/* Help Text */}
      <div className="p-3 bg-gray-800/30 rounded-lg">
        <h4 className="text-sm font-medium text-gray-300 mb-2">How to get Mixamo animations:</h4>
        <ol className="text-xs text-gray-400 space-y-1 list-decimal list-inside">
          <li>Go to mixamo.com and sign in (free)</li>
          <li>Select an animation from the library</li>
          <li>Click "Download" and select "FBX" format</li>
          <li>Choose "Without Skin" for animation-only export</li>
          <li>Upload the downloaded FBX file here</li>
        </ol>
      </div>
    </div>
  );
}
