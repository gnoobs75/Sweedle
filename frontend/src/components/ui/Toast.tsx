/**
 * Toast Component - Notification display
 */

import { useEffect, useCallback } from 'react';
import { useUIStore } from '../../stores/uiStore';
import { cn } from '../../lib/utils';

const TOAST_DURATION = 5000;

const TOAST_STYLES = {
  info: {
    bg: 'bg-primary/10 border-primary/30',
    icon: 'text-primary',
    iconPath: 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
  },
  success: {
    bg: 'bg-success/10 border-success/30',
    icon: 'text-success',
    iconPath: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z',
  },
  warning: {
    bg: 'bg-warning/10 border-warning/30',
    icon: 'text-warning',
    iconPath: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z',
  },
  error: {
    bg: 'bg-error/10 border-error/30',
    icon: 'text-error',
    iconPath: 'M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z',
  },
};

interface ToastItemProps {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message?: string;
  onDismiss: (id: string) => void;
}

function ToastItem({ id, type, title, message, onDismiss }: ToastItemProps) {
  const style = TOAST_STYLES[type];

  useEffect(() => {
    const timer = setTimeout(() => {
      onDismiss(id);
    }, TOAST_DURATION);

    return () => clearTimeout(timer);
  }, [id, onDismiss]);

  return (
    <div
      className={cn(
        'flex items-start gap-3 p-4 rounded-lg border shadow-lg backdrop-blur-sm',
        'animate-slideIn',
        style.bg
      )}
      role="alert"
    >
      <svg
        className={cn('w-5 h-5 flex-shrink-0 mt-0.5', style.icon)}
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d={style.iconPath}
        />
      </svg>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-text-primary">{title}</p>
        {message && (
          <p className="mt-1 text-sm text-text-secondary">{message}</p>
        )}
      </div>
      <button
        onClick={() => onDismiss(id)}
        className="flex-shrink-0 p-1 hover:bg-white/10 rounded transition-colors"
      >
        <svg
          className="w-4 h-4 text-text-muted"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M6 18L18 6M6 6l12 12"
          />
        </svg>
      </button>
    </div>
  );
}

export function ToastContainer() {
  const { notifications, removeNotification } = useUIStore();

  const handleDismiss = useCallback((id: string) => {
    removeNotification(id);
  }, [removeNotification]);

  if (notifications.length === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-2 max-w-md">
      {notifications.map((notification) => (
        <ToastItem
          key={notification.id}
          id={notification.id}
          type={notification.type}
          title={notification.title}
          message={notification.message}
          onDismiss={handleDismiss}
        />
      ))}
    </div>
  );
}
