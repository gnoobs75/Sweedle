/**
 * ResizablePanel Component
 */

import {
  useRef,
  useCallback,
  useState,
  type HTMLAttributes,
  type ReactNode,
} from 'react';
import { cn } from '../../lib/utils';

export interface ResizablePanelProps extends HTMLAttributes<HTMLDivElement> {
  direction: 'horizontal' | 'vertical';
  minSize?: number;
  maxSize?: number;
  defaultSize?: number;
  onResize?: (size: number) => void;
  resizeFrom?: 'start' | 'end';
  children: ReactNode;
}

export function ResizablePanel({
  className,
  direction,
  minSize = 200,
  maxSize = 600,
  defaultSize = 320,
  onResize,
  resizeFrom = 'end',
  children,
  ...props
}: ResizablePanelProps) {
  const [size, setSize] = useState(defaultSize);
  const [isResizing, setIsResizing] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      setIsResizing(true);

      const startPos = direction === 'horizontal' ? e.clientX : e.clientY;
      const startSize = size;

      const handleMouseMove = (moveEvent: MouseEvent) => {
        const currentPos =
          direction === 'horizontal' ? moveEvent.clientX : moveEvent.clientY;
        const delta = resizeFrom === 'end' ? currentPos - startPos : startPos - currentPos;
        const newSize = Math.max(minSize, Math.min(maxSize, startSize + delta));
        setSize(newSize);
        onResize?.(newSize);
      };

      const handleMouseUp = () => {
        setIsResizing(false);
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };

      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    },
    [direction, size, minSize, maxSize, resizeFrom, onResize]
  );

  const sizeStyle =
    direction === 'horizontal' ? { width: size } : { height: size };

  return (
    <div
      ref={panelRef}
      className={cn(
        'relative flex-shrink-0',
        isResizing && 'select-none',
        className
      )}
      style={sizeStyle}
      {...props}
    >
      {children}
      <div
        className={cn(
          'absolute z-10 group',
          direction === 'horizontal'
            ? resizeFrom === 'end'
              ? 'right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-primary/50'
              : 'left-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-primary/50'
            : resizeFrom === 'end'
            ? 'bottom-0 left-0 right-0 h-1 cursor-row-resize hover:bg-primary/50'
            : 'top-0 left-0 right-0 h-1 cursor-row-resize hover:bg-primary/50',
          isResizing && 'bg-primary'
        )}
        onMouseDown={handleMouseDown}
      >
        <div
          className={cn(
            'absolute transition-opacity opacity-0 group-hover:opacity-100',
            direction === 'horizontal'
              ? 'top-1/2 -translate-y-1/2 -translate-x-1/2 w-1 h-8 rounded-full bg-primary'
              : 'left-1/2 -translate-x-1/2 -translate-y-1/2 h-1 w-8 rounded-full bg-primary',
            isResizing && 'opacity-100'
          )}
        />
      </div>
    </div>
  );
}
