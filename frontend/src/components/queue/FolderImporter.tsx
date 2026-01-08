/**
 * FolderImporter Component - Bulk import images from a folder
 */

import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { useQueueStore } from '../../stores/queueStore';
import { useGenerationStore } from '../../stores/generationStore';
import { useUIStore } from '../../stores/uiStore';
import { submitImageTo3D } from '../../services/api/generation';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';
import { ProgressBar } from '../ui/ProgressBar';
import { cn } from '../../lib/utils';

interface FolderImporterProps {
  onClose?: () => void;
  className?: string;
}

interface FilePreview {
  file: File;
  preview: string;
  selected: boolean;
}

export function FolderImporter({ onClose, className }: FolderImporterProps) {
  const { addJob } = useQueueStore();
  const { parameters } = useGenerationStore();
  const { addNotification } = useUIStore();

  const [files, setFiles] = useState<FilePreview[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitProgress, setSubmitProgress] = useState(0);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newFiles = acceptedFiles.map((file) => ({
      file,
      preview: URL.createObjectURL(file),
      selected: true,
    }));
    setFiles((prev) => [...prev, ...newFiles]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.png', '.jpg', '.jpeg', '.webp'],
    },
    multiple: true,
  });

  const toggleFile = useCallback((index: number) => {
    setFiles((prev) =>
      prev.map((f, i) => (i === index ? { ...f, selected: !f.selected } : f))
    );
  }, []);

  const toggleAll = useCallback(() => {
    const allSelected = files.every((f) => f.selected);
    setFiles((prev) => prev.map((f) => ({ ...f, selected: !allSelected })));
  }, [files]);

  const removeFile = useCallback((index: number) => {
    setFiles((prev) => {
      const file = prev[index];
      URL.revokeObjectURL(file.preview);
      return prev.filter((_, i) => i !== index);
    });
  }, []);

  const clearAll = useCallback(() => {
    files.forEach((f) => URL.revokeObjectURL(f.preview));
    setFiles([]);
  }, [files]);

  const handleSubmit = useCallback(async () => {
    const selectedFiles = files.filter((f) => f.selected);
    if (selectedFiles.length === 0) return;

    setIsSubmitting(true);
    setSubmitProgress(0);

    let successCount = 0;
    let failCount = 0;

    for (let i = 0; i < selectedFiles.length; i++) {
      const { file } = selectedFiles[i];

      try {
        const result = await submitImageTo3D(file, {
          removeBackground: parameters.removeBackground,
          foregroundRatio: parameters.foregroundRatio,
          octreeResolution: parameters.octreeResolution,
          numInferenceSteps: parameters.inferenceSteps,
          guidanceScale: parameters.guidanceScale,
          textureSize: parameters.textureSize,
        });

        addJob({
          id: result.jobId,
          type: 'image_to_3d',
          status: 'queued',
          sourceImagePath: URL.createObjectURL(file),
          progress: 0,
          createdAt: new Date().toISOString(),
        });

        successCount++;
      } catch (error) {
        console.error('Failed to submit:', file.name, error);
        failCount++;
      }

      setSubmitProgress(((i + 1) / selectedFiles.length) * 100);
    }

    setIsSubmitting(false);

    if (successCount > 0) {
      addNotification({
        type: 'success',
        title: 'Batch Import Complete',
        message: `${successCount} job${successCount !== 1 ? 's' : ''} added to queue`,
      });
    }

    if (failCount > 0) {
      addNotification({
        type: 'error',
        title: 'Some Imports Failed',
        message: `${failCount} file${failCount !== 1 ? 's' : ''} failed to import`,
      });
    }

    // Clean up and close
    clearAll();
    onClose?.();
  }, [files, parameters, addJob, addNotification, clearAll, onClose]);

  const selectedCount = files.filter((f) => f.selected).length;

  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* Header */}
      <div className="p-4 border-b border-border flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-text-primary">Batch Import</h2>
          <p className="text-sm text-text-muted">
            Drop multiple images to add to the queue
          </p>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="p-1 text-text-muted hover:text-text-primary transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Dropzone */}
        <div
          {...getRootProps()}
          className={cn(
            'border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all',
            isDragActive
              ? 'border-primary bg-primary/10'
              : 'border-border hover:border-primary/50 hover:bg-surface-light'
          )}
        >
          <input {...getInputProps()} />
          <svg
            className={cn(
              'w-12 h-12 mx-auto mb-3 transition-colors',
              isDragActive ? 'text-primary' : 'text-text-muted'
            )}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
            />
          </svg>
          <p className="text-text-secondary mb-1">
            {isDragActive ? 'Drop images here' : 'Drag & drop images or click to browse'}
          </p>
          <p className="text-sm text-text-muted">
            PNG, JPG, or WebP
          </p>
        </div>

        {/* File List */}
        {files.length > 0 && (
          <Card variant="outlined" padding="sm">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <button
                  onClick={toggleAll}
                  className="p-1 hover:bg-surface-light rounded transition-colors"
                >
                  <svg className="w-5 h-5 text-text-secondary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    {files.every((f) => f.selected) ? (
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    ) : (
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h8m-4-4v8m8-4a9 9 0 11-18 0 9 9 0 0118 0z" />
                    )}
                  </svg>
                </button>
                <span className="text-sm text-text-secondary">
                  {selectedCount} of {files.length} selected
                </span>
              </div>
              <Button variant="ghost" size="sm" onClick={clearAll}>
                Clear All
              </Button>
            </div>

            <div className="grid grid-cols-4 gap-2 max-h-64 overflow-y-auto">
              {files.map((file, index) => (
                <div
                  key={index}
                  className={cn(
                    'relative aspect-square rounded-lg overflow-hidden group cursor-pointer',
                    'border-2 transition-all',
                    file.selected ? 'border-primary' : 'border-transparent opacity-50'
                  )}
                  onClick={() => toggleFile(index)}
                >
                  <img
                    src={file.preview}
                    alt={file.file.name}
                    className="w-full h-full object-cover"
                  />

                  {/* Selection indicator */}
                  {file.selected && (
                    <div className="absolute top-1 right-1 w-5 h-5 bg-primary rounded-full flex items-center justify-center">
                      <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                  )}

                  {/* Remove button */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      removeFile(index);
                    }}
                    className="absolute top-1 left-1 w-5 h-5 bg-error rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>

                  {/* File name */}
                  <div className="absolute inset-x-0 bottom-0 p-1 bg-gradient-to-t from-black/70 to-transparent">
                    <p className="text-xs text-white truncate">{file.file.name}</p>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* Generation Settings Note */}
        {files.length > 0 && (
          <p className="text-xs text-text-muted text-center">
            Jobs will use your current generation settings
          </p>
        )}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-border">
        {isSubmitting ? (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-text-secondary">Submitting jobs...</span>
              <span className="text-text-primary font-mono">{Math.round(submitProgress)}%</span>
            </div>
            <ProgressBar value={submitProgress} max={100} variant="primary" />
          </div>
        ) : (
          <div className="flex gap-2">
            <Button
              variant="primary"
              className="flex-1"
              onClick={handleSubmit}
              disabled={selectedCount === 0}
            >
              <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              Add {selectedCount} to Queue
            </Button>
            {onClose && (
              <Button variant="ghost" onClick={onClose}>
                Cancel
              </Button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
