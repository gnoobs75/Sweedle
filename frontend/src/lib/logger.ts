/**
 * Logger - Application-wide logging with persistence
 */

type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface LogEntry {
  id: string;
  timestamp: string;
  level: LogLevel;
  category: string;
  message: string;
  data?: unknown;
  stack?: string;
}

const MAX_LOGS = 500;
const STORAGE_KEY = 'sweedle_logs';

class Logger {
  private logs: LogEntry[] = [];
  private subscribers: Set<(logs: LogEntry[]) => void> = new Set();

  constructor() {
    this.loadFromStorage();
  }

  private loadFromStorage(): void {
    try {
      const stored = sessionStorage.getItem(STORAGE_KEY);
      if (stored) {
        this.logs = JSON.parse(stored);
      }
    } catch {
      this.logs = [];
    }
  }

  private saveToStorage(): void {
    try {
      // Keep only recent logs
      if (this.logs.length > MAX_LOGS) {
        this.logs = this.logs.slice(-MAX_LOGS);
      }
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(this.logs));
    } catch {
      // Storage full, clear old logs
      this.logs = this.logs.slice(-100);
    }
  }

  private notifySubscribers(): void {
    this.subscribers.forEach(fn => fn(this.logs));
  }

  private log(level: LogLevel, category: string, message: string, data?: unknown): void {
    const entry: LogEntry = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
      timestamp: new Date().toISOString(),
      level,
      category,
      message,
      data: data !== undefined ? this.sanitizeData(data) : undefined,
    };

    // Capture stack for errors
    if (level === 'error' && data instanceof Error) {
      entry.stack = data.stack;
    }

    this.logs.push(entry);
    this.saveToStorage();
    this.notifySubscribers();

    // Also log to browser console with styling
    const styles = {
      debug: 'color: #888',
      info: 'color: #6366f1',
      warn: 'color: #f59e0b',
      error: 'color: #ef4444; font-weight: bold',
    };

    const prefix = `[${category}]`;
    if (data !== undefined) {
      console[level === 'debug' ? 'log' : level](
        `%c${prefix} ${message}`,
        styles[level],
        data
      );
    } else {
      console[level === 'debug' ? 'log' : level](
        `%c${prefix} ${message}`,
        styles[level]
      );
    }
  }

  private sanitizeData(data: unknown): unknown {
    try {
      // Handle File objects
      if (data instanceof File) {
        return { name: data.name, size: data.size, type: data.type };
      }
      // Handle arrays
      if (Array.isArray(data)) {
        return data.map(item => this.sanitizeData(item));
      }
      // Handle objects
      if (data && typeof data === 'object') {
        const sanitized: Record<string, unknown> = {};
        for (const [key, value] of Object.entries(data)) {
          sanitized[key] = this.sanitizeData(value);
        }
        return sanitized;
      }
      return data;
    } catch {
      return String(data);
    }
  }

  debug(category: string, message: string, data?: unknown): void {
    this.log('debug', category, message, data);
  }

  info(category: string, message: string, data?: unknown): void {
    this.log('info', category, message, data);
  }

  warn(category: string, message: string, data?: unknown): void {
    this.log('warn', category, message, data);
  }

  error(category: string, message: string, data?: unknown): void {
    this.log('error', category, message, data);
  }

  getLogs(): LogEntry[] {
    return [...this.logs];
  }

  getLogsByLevel(level: LogLevel): LogEntry[] {
    return this.logs.filter(log => log.level === level);
  }

  getLogsByCategory(category: string): LogEntry[] {
    return this.logs.filter(log => log.category === category);
  }

  getRecentLogs(count: number): LogEntry[] {
    return this.logs.slice(-count);
  }

  clear(): void {
    this.logs = [];
    sessionStorage.removeItem(STORAGE_KEY);
    this.notifySubscribers();
  }

  subscribe(callback: (logs: LogEntry[]) => void): () => void {
    this.subscribers.add(callback);
    return () => this.subscribers.delete(callback);
  }

  exportLogs(): string {
    return JSON.stringify(this.logs, null, 2);
  }
}

// Singleton instance
export const logger = new Logger();

// Convenience exports
export type { LogEntry, LogLevel };
