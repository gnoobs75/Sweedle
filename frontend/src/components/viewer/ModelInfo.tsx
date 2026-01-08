/**
 * ModelInfo Component - Display mesh statistics and info
 */

import { useViewerStore } from '../../stores/viewerStore';
import { Badge } from '../ui/Badge';
import { cn, formatNumber, formatFileSize } from '../../lib/utils';

interface ModelInfoProps {
  className?: string;
  variant?: 'bar' | 'panel';
}

export function ModelInfo({ className, variant = 'bar' }: ModelInfoProps) {
  const {
    currentModelUrl,
    modelInfo,
    currentLodLevel,
    availableLodLevels,
  } = useViewerStore();

  if (!currentModelUrl) {
    return null;
  }

  if (variant === 'bar') {
    return (
      <div
        className={cn(
          'h-8 flex items-center justify-between px-4 text-xs',
          'border-t border-border bg-surface text-text-muted',
          className
        )}
      >
        <div className="flex items-center gap-4">
          <span>
            <span className="text-text-secondary">Vertices:</span>{' '}
            {modelInfo.vertexCount ? formatNumber(modelInfo.vertexCount) : '--'}
          </span>
          <span>
            <span className="text-text-secondary">Faces:</span>{' '}
            {modelInfo.faceCount ? formatNumber(modelInfo.faceCount) : '--'}
          </span>
          <span>
            <span className="text-text-secondary">Materials:</span>{' '}
            {modelInfo.materials?.length || '--'}
          </span>
          {modelInfo.hasTextures && (
            <Badge variant="success" size="sm">
              Textured
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-2">
          {availableLodLevels.length > 1 && (
            <span>
              <span className="text-text-secondary">LOD:</span> {currentLodLevel}
            </span>
          )}
        </div>
      </div>
    );
  }

  // Panel variant - more detailed info
  return (
    <div className={cn('p-4 bg-surface border border-border rounded-xl', className)}>
      <h3 className="text-sm font-semibold text-text-primary mb-3">
        Model Information
      </h3>

      <div className="space-y-2 text-sm">
        <div className="flex justify-between">
          <span className="text-text-muted">Vertices</span>
          <span className="text-text-primary font-mono">
            {modelInfo.vertexCount ? formatNumber(modelInfo.vertexCount) : '--'}
          </span>
        </div>

        <div className="flex justify-between">
          <span className="text-text-muted">Faces</span>
          <span className="text-text-primary font-mono">
            {modelInfo.faceCount ? formatNumber(modelInfo.faceCount) : '--'}
          </span>
        </div>

        <div className="flex justify-between">
          <span className="text-text-muted">Materials</span>
          <span className="text-text-primary font-mono">
            {modelInfo.materials?.length || '--'}
          </span>
        </div>

        <div className="flex justify-between">
          <span className="text-text-muted">Textures</span>
          <span className="text-text-primary">
            {modelInfo.hasTextures ? (
              <Badge variant="success" size="sm">Yes</Badge>
            ) : (
              <Badge variant="default" size="sm">No</Badge>
            )}
          </span>
        </div>

        {availableLodLevels.length > 1 && (
          <div className="flex justify-between">
            <span className="text-text-muted">LOD Level</span>
            <span className="text-text-primary font-mono">{currentLodLevel}</span>
          </div>
        )}
      </div>

      {/* Material List */}
      {modelInfo.materials && modelInfo.materials.length > 0 && (
        <div className="mt-4 pt-4 border-t border-border">
          <h4 className="text-xs font-medium text-text-secondary mb-2">
            Materials ({modelInfo.materials.length})
          </h4>
          <div className="flex flex-wrap gap-1">
            {modelInfo.materials.map((mat, i) => (
              <Badge key={i} variant="default" size="sm">
                {mat}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* Mesh Quality Indicator */}
      <div className="mt-4 pt-4 border-t border-border">
        <h4 className="text-xs font-medium text-text-secondary mb-2">
          Mesh Quality
        </h4>
        <MeshQualityIndicator
          faceCount={modelInfo.faceCount || 0}
          hasTextures={modelInfo.hasTextures || false}
        />
      </div>
    </div>
  );
}

/**
 * Mesh quality indicator based on face count
 */
function MeshQualityIndicator({
  faceCount,
  hasTextures,
}: {
  faceCount: number;
  hasTextures: boolean;
}) {
  const getQualityLevel = () => {
    if (faceCount === 0) return { level: 'unknown', label: 'Unknown', color: 'default' };
    if (faceCount < 5000) return { level: 'low', label: 'Low Poly', color: 'info' };
    if (faceCount < 20000) return { level: 'medium', label: 'Medium Poly', color: 'success' };
    if (faceCount < 100000) return { level: 'high', label: 'High Poly', color: 'warning' };
    return { level: 'ultra', label: 'Ultra High', color: 'error' };
  };

  const quality = getQualityLevel();

  const getGameReadiness = () => {
    const issues: string[] = [];
    const good: string[] = [];

    if (faceCount > 50000) {
      issues.push('High poly count may impact performance');
    } else if (faceCount > 0) {
      good.push('Poly count suitable for games');
    }

    if (!hasTextures) {
      issues.push('No textures detected');
    } else {
      good.push('Has PBR textures');
    }

    return { issues, good };
  };

  const readiness = getGameReadiness();

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <Badge variant={quality.color as any} size="sm">
          {quality.label}
        </Badge>
        {faceCount > 0 && (
          <span className="text-xs text-text-muted">
            ({formatNumber(faceCount)} faces)
          </span>
        )}
      </div>

      {readiness.good.length > 0 && (
        <div className="space-y-1">
          {readiness.good.map((item, i) => (
            <div key={i} className="flex items-center gap-1 text-xs text-success">
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              {item}
            </div>
          ))}
        </div>
      )}

      {readiness.issues.length > 0 && (
        <div className="space-y-1">
          {readiness.issues.map((item, i) => (
            <div key={i} className="flex items-center gap-1 text-xs text-warning">
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              {item}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * Compact model info for thumbnails/cards
 */
export function CompactModelInfo({
  vertexCount,
  faceCount,
  className,
}: {
  vertexCount?: number;
  faceCount?: number;
  className?: string;
}) {
  return (
    <div className={cn('flex items-center gap-2 text-xs text-text-muted', className)}>
      {faceCount !== undefined && (
        <span>{formatNumber(faceCount)} faces</span>
      )}
      {vertexCount !== undefined && faceCount !== undefined && (
        <span className="text-border">|</span>
      )}
      {vertexCount !== undefined && (
        <span>{formatNumber(vertexCount)} verts</span>
      )}
    </div>
  );
}
