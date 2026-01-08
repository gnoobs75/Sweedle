/**
 * ExportPanel Component - Asset export to game engines
 */

import { useState, useCallback } from 'react';
import { useLibraryStore } from '../../stores/libraryStore';
import { useUIStore } from '../../stores/uiStore';
import {
  exportToEngine,
  generateLods,
  validateAsset,
  compressAsset,
} from '../../services/api/export';
import { EnginePresets, ExportOptions } from './EnginePresets';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';
import { Badge } from '../ui/Badge';
import { ProgressBar } from '../ui/ProgressBar';
import { cn } from '../../lib/utils';
import type { Asset, EngineType } from '../../types';

interface ExportPanelProps {
  assetId?: string;
  assetIds?: string[];
  onClose?: () => void;
  className?: string;
}

type ExportStep = 'config' | 'validating' | 'exporting' | 'complete' | 'error';

interface ValidationIssue {
  severity: string;
  message: string;
  fix_suggestion?: string;
}

export function ExportPanel({
  assetId,
  assetIds = [],
  onClose,
  className,
}: ExportPanelProps) {
  const { assets } = useLibraryStore();
  const { addNotification } = useUIStore();

  // Get assets to export
  const exportAssetIds = assetId ? [assetId] : assetIds;
  const exportAssets = assets.filter((a) => exportAssetIds.includes(a.id));

  // State
  const [step, setStep] = useState<ExportStep>('config');
  const [selectedEngine, setSelectedEngine] = useState<EngineType | null>(null);
  const [projectPath, setProjectPath] = useState('');

  // Export options
  const [includeLods, setIncludeLods] = useState(true);
  const [compress, setCompress] = useState(true);
  const [generateMaterials, setGenerateMaterials] = useState(true);

  // Progress state
  const [progress, setProgress] = useState(0);
  const [currentAsset, setCurrentAsset] = useState<string | null>(null);
  const [validationIssues, setValidationIssues] = useState<ValidationIssue[]>([]);
  const [exportedFiles, setExportedFiles] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  const handleValidate = useCallback(async () => {
    if (!selectedEngine || !projectPath) return;

    setStep('validating');
    setProgress(0);
    setValidationIssues([]);

    try {
      const allIssues: ValidationIssue[] = [];

      for (let i = 0; i < exportAssets.length; i++) {
        const asset = exportAssets[i];
        setCurrentAsset(asset.name);
        setProgress(((i + 1) / exportAssets.length) * 100);

        const result = await validateAsset({
          assetId: asset.id,
          targetEngine: selectedEngine,
        });

        if (result.issues.length > 0) {
          allIssues.push(
            ...result.issues.map((issue: any) => ({
              severity: issue.severity,
              message: `${asset.name}: ${issue.message}`,
              fix_suggestion: issue.fix_suggestion,
            }))
          );
        }
      }

      setValidationIssues(allIssues);
      setCurrentAsset(null);

      // Check for blocking errors
      const hasErrors = allIssues.some((i) => i.severity === 'error' || i.severity === 'critical');

      if (hasErrors) {
        addNotification({
          type: 'warning',
          title: 'Validation Issues',
          message: 'Some assets have issues that should be fixed before export',
        });
      }

      // Proceed to export if no critical errors
      if (!allIssues.some((i) => i.severity === 'critical')) {
        await handleExport();
      } else {
        setStep('config');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Validation failed');
      setStep('error');
    }
  }, [selectedEngine, projectPath, exportAssets, addNotification]);

  const handleExport = useCallback(async () => {
    if (!selectedEngine || !projectPath) return;

    setStep('exporting');
    setProgress(0);
    setExportedFiles([]);

    try {
      const allExported: string[] = [];

      for (let i = 0; i < exportAssets.length; i++) {
        const asset = exportAssets[i];
        setCurrentAsset(asset.name);

        // Generate LODs if requested
        if (includeLods) {
          setProgress((i / exportAssets.length) * 100 + 10);
          await generateLods({ assetId: asset.id });
        }

        // Compress if requested
        if (compress) {
          setProgress((i / exportAssets.length) * 100 + 30);
          await compressAsset({ assetId: asset.id, quality: 'balanced' });
        }

        // Export to engine
        setProgress((i / exportAssets.length) * 100 + 50);
        const result = await exportToEngine({
          assetId: asset.id,
          engine: selectedEngine,
          projectPath,
          generateLods: includeLods,
          compressMesh: compress,
        });

        if (result.success) {
          allExported.push(...result.filesExported);
        } else {
          throw new Error('Export failed');
        }

        setProgress(((i + 1) / exportAssets.length) * 100);
      }

      setExportedFiles(allExported);
      setCurrentAsset(null);
      setStep('complete');

      addNotification({
        type: 'success',
        title: 'Export Complete',
        message: `Exported ${exportAssets.length} asset${exportAssets.length > 1 ? 's' : ''} to ${selectedEngine}`,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Export failed');
      setStep('error');

      addNotification({
        type: 'error',
        title: 'Export Failed',
        message: err instanceof Error ? err.message : 'An error occurred',
      });
    }
  }, [selectedEngine, projectPath, exportAssets, includeLods, compress, addNotification]);

  const canExport = selectedEngine && projectPath && exportAssets.length > 0;

  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* Header */}
      <div className="p-4 border-b border-border flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-text-primary">Export to Engine</h2>
          <p className="text-sm text-text-muted">
            {exportAssets.length} asset{exportAssets.length !== 1 ? 's' : ''} selected
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
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {step === 'config' && (
          <>
            {/* Asset Preview */}
            <Card variant="outlined" padding="sm">
              <h4 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">
                Assets to Export
              </h4>
              <div className="flex flex-wrap gap-2">
                {exportAssets.map((asset) => (
                  <div
                    key={asset.id}
                    className="flex items-center gap-2 p-2 bg-surface-light rounded-lg"
                  >
                    {asset.thumbnailPath ? (
                      <img
                        src={asset.thumbnailPath}
                        alt={asset.name}
                        className="w-8 h-8 rounded object-cover"
                      />
                    ) : (
                      <div className="w-8 h-8 rounded bg-surface flex items-center justify-center">
                        <svg className="w-4 h-4 text-text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                        </svg>
                      </div>
                    )}
                    <span className="text-sm text-text-primary">{asset.name}</span>
                  </div>
                ))}
              </div>
            </Card>

            {/* Engine Selection */}
            <EnginePresets
              selectedEngine={selectedEngine}
              onSelectEngine={setSelectedEngine}
              projectPath={projectPath}
              onProjectPathChange={setProjectPath}
            />

            {/* Export Options */}
            {selectedEngine && (
              <ExportOptions
                includeLods={includeLods}
                onIncludeLodsChange={setIncludeLods}
                compress={compress}
                onCompressChange={setCompress}
                generateMaterials={generateMaterials}
                onGenerateMaterialsChange={setGenerateMaterials}
              />
            )}

            {/* Validation Warnings */}
            {validationIssues.length > 0 && (
              <Card variant="outlined" padding="sm" className="border-warning/50">
                <h4 className="text-xs font-semibold text-warning uppercase tracking-wider mb-2">
                  Validation Issues
                </h4>
                <div className="space-y-2 max-h-40 overflow-y-auto">
                  {validationIssues.map((issue, i) => (
                    <div key={i} className="text-sm">
                      <Badge
                        variant={issue.severity === 'error' ? 'error' : 'warning'}
                        size="sm"
                        className="mr-2"
                      >
                        {issue.severity}
                      </Badge>
                      <span className="text-text-secondary">{issue.message}</span>
                      {issue.fix_suggestion && (
                        <p className="text-xs text-text-muted mt-1 ml-4">
                          Fix: {issue.fix_suggestion}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </Card>
            )}
          </>
        )}

        {(step === 'validating' || step === 'exporting') && (
          <div className="flex flex-col items-center justify-center h-64 text-center">
            <div className="w-16 h-16 mb-4">
              <svg className="animate-spin text-primary" viewBox="0 0 24 24" fill="none">
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-text-primary mb-2">
              {step === 'validating' ? 'Validating Assets...' : 'Exporting...'}
            </h3>
            {currentAsset && (
              <p className="text-sm text-text-muted mb-4">
                Processing: {currentAsset}
              </p>
            )}
            <div className="w-full max-w-xs">
              <ProgressBar value={progress} max={100} variant="primary" animated />
              <p className="text-xs text-text-muted mt-2">{Math.round(progress)}% complete</p>
            </div>
          </div>
        )}

        {step === 'complete' && (
          <div className="flex flex-col items-center justify-center h-64 text-center">
            <div className="w-16 h-16 mb-4 text-success">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <path d="M9 12l2 2 4-4" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-text-primary mb-2">
              Export Complete!
            </h3>
            <p className="text-sm text-text-muted mb-4">
              {exportedFiles.length} file{exportedFiles.length !== 1 ? 's' : ''} exported to {selectedEngine}
            </p>
            <Card variant="outlined" padding="sm" className="w-full max-w-md text-left">
              <h4 className="text-xs font-semibold text-text-muted uppercase mb-2">
                Exported Files
              </h4>
              <div className="space-y-1 max-h-32 overflow-y-auto">
                {exportedFiles.slice(0, 10).map((file, i) => (
                  <p key={i} className="text-xs text-text-secondary font-mono truncate">
                    {file}
                  </p>
                ))}
                {exportedFiles.length > 10 && (
                  <p className="text-xs text-text-muted">
                    ...and {exportedFiles.length - 10} more
                  </p>
                )}
              </div>
            </Card>
          </div>
        )}

        {step === 'error' && (
          <div className="flex flex-col items-center justify-center h-64 text-center">
            <div className="w-16 h-16 mb-4 text-error">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <path d="M15 9l-6 6M9 9l6 6" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-text-primary mb-2">
              Export Failed
            </h3>
            <p className="text-sm text-error mb-4">{error}</p>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-border">
        {step === 'config' && (
          <div className="flex gap-2">
            <Button
              variant="primary"
              className="flex-1"
              onClick={handleValidate}
              disabled={!canExport}
            >
              <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
              </svg>
              Export to {selectedEngine || 'Engine'}
            </Button>
            {onClose && (
              <Button variant="ghost" onClick={onClose}>
                Cancel
              </Button>
            )}
          </div>
        )}

        {step === 'complete' && (
          <div className="flex gap-2">
            <Button variant="primary" className="flex-1" onClick={onClose}>
              Done
            </Button>
            <Button
              variant="secondary"
              onClick={() => {
                setStep('config');
                setExportedFiles([]);
              }}
            >
              Export More
            </Button>
          </div>
        )}

        {step === 'error' && (
          <div className="flex gap-2">
            <Button
              variant="primary"
              className="flex-1"
              onClick={() => {
                setStep('config');
                setError(null);
              }}
            >
              Try Again
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
