/**
 * Slider Component
 */

import { forwardRef, type InputHTMLAttributes, useCallback } from 'react';
import { cn } from '../../lib/utils';

export interface SliderProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type' | 'onChange'> {
  label?: string;
  hint?: string;
  showValue?: boolean;
  valueFormatter?: (value: number) => string;
  onChange?: (value: number) => void;
}

const Slider = forwardRef<HTMLInputElement, SliderProps>(
  (
    {
      className,
      label,
      hint,
      showValue = true,
      valueFormatter,
      min = 0,
      max = 100,
      step = 1,
      value,
      onChange,
      disabled,
      id,
      ...props
    },
    ref
  ) => {
    const inputId = id || label?.toLowerCase().replace(/\s+/g, '-');
    const numValue = typeof value === 'number' ? value : Number(value) || 0;
    const numMin = Number(min);
    const numMax = Number(max);
    const percentage = ((numValue - numMin) / (numMax - numMin)) * 100;

    const formattedValue = valueFormatter
      ? valueFormatter(numValue)
      : String(numValue);

    const handleChange = useCallback(
      (e: React.ChangeEvent<HTMLInputElement>) => {
        onChange?.(Number(e.target.value));
      },
      [onChange]
    );

    return (
      <div className="w-full">
        {(label || showValue) && (
          <div className="flex items-center justify-between mb-2">
            {label && (
              <label
                htmlFor={inputId}
                className="text-sm font-medium text-text-secondary"
              >
                {label}
              </label>
            )}
            {showValue && (
              <span className="text-sm font-mono text-text-primary">
                {formattedValue}
              </span>
            )}
          </div>
        )}
        <div className="relative">
          <div className="absolute inset-0 h-2 top-1/2 -translate-y-1/2 bg-surface-lighter rounded-full overflow-hidden">
            <div
              className="h-full bg-primary transition-all"
              style={{ width: `${percentage}%` }}
            />
          </div>
          <input
            ref={ref}
            type="range"
            id={inputId}
            min={min}
            max={max}
            step={step}
            value={value}
            onChange={handleChange}
            disabled={disabled}
            className={cn(
              'w-full h-2 appearance-none bg-transparent cursor-pointer relative z-10',
              'disabled:opacity-50 disabled:cursor-not-allowed',
              '[&::-webkit-slider-thumb]:appearance-none',
              '[&::-webkit-slider-thumb]:w-4',
              '[&::-webkit-slider-thumb]:h-4',
              '[&::-webkit-slider-thumb]:rounded-full',
              '[&::-webkit-slider-thumb]:bg-white',
              '[&::-webkit-slider-thumb]:shadow-md',
              '[&::-webkit-slider-thumb]:cursor-pointer',
              '[&::-webkit-slider-thumb]:transition-transform',
              '[&::-webkit-slider-thumb]:hover:scale-110',
              '[&::-moz-range-thumb]:w-4',
              '[&::-moz-range-thumb]:h-4',
              '[&::-moz-range-thumb]:rounded-full',
              '[&::-moz-range-thumb]:bg-white',
              '[&::-moz-range-thumb]:border-0',
              '[&::-moz-range-thumb]:shadow-md',
              '[&::-moz-range-thumb]:cursor-pointer',
              className
            )}
            {...props}
          />
        </div>
        {hint && <p className="mt-2 text-xs text-text-muted">{hint}</p>}
      </div>
    );
  }
);

Slider.displayName = 'Slider';

export { Slider };
