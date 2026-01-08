/**
 * Spinner Component
 */

import type { HTMLAttributes } from 'react';
import { cn } from '../../lib/utils';

export interface SpinnerProps extends HTMLAttributes<HTMLDivElement> {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  variant?: 'default' | 'primary' | 'white';
}

export function Spinner({
  className,
  size = 'md',
  variant = 'default',
  ...props
}: SpinnerProps) {
  const sizeStyles = {
    sm: 'w-4 h-4 border-2',
    md: 'w-6 h-6 border-2',
    lg: 'w-8 h-8 border-3',
    xl: 'w-12 h-12 border-4',
  };

  const variantStyles = {
    default: 'border-surface-lighter border-t-text-primary',
    primary: 'border-primary/30 border-t-primary',
    white: 'border-white/30 border-t-white',
  };

  return (
    <div
      className={cn(
        'animate-spin rounded-full',
        sizeStyles[size],
        variantStyles[variant],
        className
      )}
      role="status"
      aria-label="Loading"
      {...props}
    />
  );
}

export interface LoadingOverlayProps extends HTMLAttributes<HTMLDivElement> {
  message?: string;
}

export function LoadingOverlay({
  className,
  message,
  ...props
}: LoadingOverlayProps) {
  return (
    <div
      className={cn(
        'absolute inset-0 flex flex-col items-center justify-center',
        'bg-background/80 backdrop-blur-sm z-50',
        className
      )}
      {...props}
    >
      <Spinner size="lg" variant="primary" />
      {message && (
        <p className="mt-4 text-sm text-text-secondary">{message}</p>
      )}
    </div>
  );
}
