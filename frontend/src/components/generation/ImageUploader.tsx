/**
 * ImageUploader Component - Drag-and-drop image upload
 */

import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { cn } from '../../lib/utils';
import { Button } from '../ui/Button';

interface ImageUploaderProps {
  value: File | null;
  preview: string | null;
  onChange: (file: File | null) => void;
  disabled?: boolean;
  className?: string;
}

const ACCEPTED_TYPES = {
  'image/png': ['.png'],
  'image/jpeg': ['.jpg', '.jpeg'],
  'image/webp': ['.webp'],
};

const MAX_SIZE = 10 * 1024 * 1024; // 10MB

export function ImageUploader({
  value,
  preview,
  onChange,
  disabled = false,
  className,
}: ImageUploaderProps) {
  const [error, setError] = useState<string | null>(null);

  const onDrop = useCallback(
    (acceptedFiles: File[], rejectedFiles: any[]) => {
      setError(null);

      if (rejectedFiles.length > 0) {
        const rejection = rejectedFiles[0];
        if (rejection.errors[0]?.code === 'file-too-large') {
          setError('File is too large. Maximum size is 10MB.');
        } else if (rejection.errors[0]?.code === 'file-invalid-type') {
          setError('Invalid file type. Please upload PNG, JPG, or WEBP.');
        } else {
          setError('Failed to upload file. Please try again.');
        }
        return;
      }

      if (acceptedFiles.length > 0) {
        onChange(acceptedFiles[0]);
      }
    },
    [onChange]
  );

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    accept: ACCEPTED_TYPES,
    maxSize: MAX_SIZE,
    multiple: false,
    disabled,
  });

  const handleRemove = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      onChange(null);
      setError(null);
    },
    [onChange]
  );

  const handlePaste = useCallback(
    async (e: React.ClipboardEvent) => {
      const items = e.clipboardData?.items;
      if (!items) return;

      for (const item of items) {
        if (item.type.startsWith('image/')) {
          const file = item.getAsFile();
          if (file) {
            if (file.size > MAX_SIZE) {
              setError('Pasted image is too large. Maximum size is 10MB.');
              return;
            }
            onChange(file);
            return;
          }
        }
      }
    },
    [onChange]
  );

  return (
    <div className={cn('w-full', className)}>
      <div
        {...getRootProps()}
        onPaste={handlePaste}
        tabIndex={0}
        className={cn(
          'relative rounded-xl border-2 border-dashed transition-all cursor-pointer',
          'focus:outline-none focus:ring-2 focus:ring-primary/50',
          isDragActive && !isDragReject && 'border-primary bg-primary/10',
          isDragReject && 'border-error bg-error/10',
          !isDragActive && !preview && 'border-border hover:border-primary/50 hover:bg-surface-light',
          preview && 'border-transparent',
          disabled && 'opacity-50 cursor-not-allowed',
          error && 'border-error'
        )}
      >
        <input {...getInputProps()} />

        {preview ? (
          <div className="relative group">
            <img
              src={preview}
              alt="Source image"
              className="w-full rounded-xl object-contain max-h-64"
            />
            {/* Overlay on hover */}
            <div
              className={cn(
                'absolute inset-0 flex items-center justify-center gap-2 rounded-xl',
                'bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity'
              )}
            >
              <Button
                variant="secondary"
                size="sm"
                onClick={handleRemove}
                disabled={disabled}
              >
                <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
                Remove
              </Button>
              <Button variant="secondary" size="sm" disabled={disabled}>
                <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                Replace
              </Button>
            </div>
          </div>
        ) : (
          <div className="py-12 px-6 text-center">
            {isDragActive ? (
              isDragReject ? (
                <>
                  <svg
                    className="w-12 h-12 mx-auto text-error mb-3"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.5}
                      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                    />
                  </svg>
                  <p className="text-error font-medium">Invalid file type</p>
                  <p className="text-text-muted text-sm mt-1">
                    Please use PNG, JPG, or WEBP
                  </p>
                </>
              ) : (
                <>
                  <svg
                    className="w-12 h-12 mx-auto text-primary mb-3 animate-bounce"
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
                  <p className="text-primary font-medium">Drop your image here</p>
                </>
              )
            ) : (
              <>
                <svg
                  className="w-12 h-12 mx-auto text-text-muted mb-3"
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
                <p className="text-text-secondary font-medium mb-1">
                  Drop an image here
                </p>
                <p className="text-text-muted text-sm">
                  or click to browse
                </p>
                <p className="text-text-muted text-xs mt-3">
                  PNG, JPG, WEBP up to 10MB
                </p>
                <p className="text-text-muted text-xs mt-1">
                  You can also paste from clipboard (Ctrl+V)
                </p>
              </>
            )}
          </div>
        )}
      </div>

      {error && (
        <p className="mt-2 text-sm text-error flex items-center gap-1">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          {error}
        </p>
      )}
    </div>
  );
}
