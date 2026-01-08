/**
 * Toggle Component
 */

import { forwardRef, type InputHTMLAttributes } from 'react';
import { cn } from '../../lib/utils';

export interface ToggleProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: string;
  description?: string;
}

const Toggle = forwardRef<HTMLInputElement, ToggleProps>(
  ({ className, label, description, disabled, id, ...props }, ref) => {
    const inputId = id || label?.toLowerCase().replace(/\s+/g, '-');

    return (
      <label
        htmlFor={inputId}
        className={cn(
          'flex items-center justify-between gap-3 cursor-pointer group',
          disabled && 'cursor-not-allowed opacity-50'
        )}
      >
        {(label || description) && (
          <div className="flex flex-col">
            {label && (
              <span className="text-sm font-medium text-text-primary">
                {label}
              </span>
            )}
            {description && (
              <span className="text-xs text-text-muted">{description}</span>
            )}
          </div>
        )}
        <div className="relative">
          <input
            ref={ref}
            type="checkbox"
            id={inputId}
            disabled={disabled}
            className={cn('peer sr-only', className)}
            {...props}
          />
          <div
            className={cn(
              'w-11 h-6 rounded-full transition-colors',
              'bg-surface-lighter peer-checked:bg-primary',
              'peer-focus:ring-2 peer-focus:ring-primary/50 peer-focus:ring-offset-2 peer-focus:ring-offset-background'
            )}
          />
          <div
            className={cn(
              'absolute top-0.5 left-0.5 w-5 h-5 rounded-full',
              'bg-white shadow-sm transition-transform',
              'peer-checked:translate-x-5'
            )}
          />
        </div>
      </label>
    );
  }
);

Toggle.displayName = 'Toggle';

export { Toggle };
