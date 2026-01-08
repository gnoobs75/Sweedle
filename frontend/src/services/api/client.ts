/**
 * API Client - HTTP service layer
 */

import { logger } from '../../lib/logger';

// Detect if running in Tauri (check at runtime, not module load)
function isTauri(): boolean {
  return typeof window !== 'undefined' && '__TAURI__' in window;
}

// Get API base URL - checked at runtime for each request
function getApiBase(): string {
  if (isTauri()) {
    return 'http://localhost:8000/api';
  }
  return import.meta.env.VITE_API_BASE_URL
    ? `${import.meta.env.VITE_API_BASE_URL}/api`
    : '/api';
}

interface RequestOptions extends RequestInit {
  timeout?: number;
}

interface ApiError extends Error {
  status: number;
  statusText: string;
  data?: unknown;
}

function createApiError(
  message: string,
  status: number,
  statusText: string,
  data?: unknown
): ApiError {
  const error = new Error(message) as ApiError;
  error.status = status;
  error.statusText = statusText;
  error.data = data;
  return error;
}

async function request<T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const { timeout = 30000, ...fetchOptions } = options;
  const method = fetchOptions.method || 'GET';
  const startTime = performance.now();

  logger.debug('API', `${method} ${endpoint}`, {
    method,
    endpoint,
    hasBody: !!fetchOptions.body
  });

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(`${getApiBase()}${endpoint}`, {
      ...fetchOptions,
      signal: controller.signal,
      headers: {
        ...fetchOptions.headers,
      },
    });

    clearTimeout(timeoutId);
    const duration = Math.round(performance.now() - startTime);

    if (!response.ok) {
      let errorData;
      const text = await response.text();
      try {
        errorData = JSON.parse(text);
      } catch {
        errorData = text;
      }

      logger.error('API', `${method} ${endpoint} failed`, {
        status: response.status,
        statusText: response.statusText,
        duration: `${duration}ms`,
        error: errorData
      });

      throw createApiError(
        errorData?.detail || errorData?.message || response.statusText,
        response.status,
        response.statusText,
        errorData
      );
    }

    // Handle empty responses
    const contentType = response.headers.get('content-type');
    if (!contentType || !contentType.includes('application/json')) {
      logger.debug('API', `${method} ${endpoint} completed (non-JSON)`, {
        status: response.status,
        duration: `${duration}ms`
      });
      return {} as T;
    }

    const data = await response.json();
    logger.info('API', `${method} ${endpoint} completed`, {
      status: response.status,
      duration: `${duration}ms`
    });

    return data;
  } catch (error) {
    clearTimeout(timeoutId);
    const duration = Math.round(performance.now() - startTime);

    if (error instanceof Error && error.name === 'AbortError') {
      logger.error('API', `${method} ${endpoint} timeout`, {
        duration: `${duration}ms`,
        timeout: `${timeout}ms`
      });
      throw createApiError('Request timeout', 408, 'Request Timeout');
    }

    // Only log if not already logged as API error
    if (!(error as ApiError).status) {
      logger.error('API', `${method} ${endpoint} network error`, {
        error: error instanceof Error ? error.message : String(error),
        duration: `${duration}ms`
      });
    }

    throw error;
  }
}

function get<T>(endpoint: string, options?: RequestOptions): Promise<T> {
  return request<T>(endpoint, { ...options, method: 'GET' });
}

function post<T>(
  endpoint: string,
  data?: unknown,
  options?: RequestOptions
): Promise<T> {
  const isFormData = data instanceof FormData;
  return request<T>(endpoint, {
    ...options,
    method: 'POST',
    headers: isFormData
      ? options?.headers
      : {
          'Content-Type': 'application/json',
          ...options?.headers,
        },
    body: isFormData ? data : data ? JSON.stringify(data) : undefined,
  });
}

function patch<T>(
  endpoint: string,
  data: unknown,
  options?: RequestOptions
): Promise<T> {
  return request<T>(endpoint, {
    ...options,
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    body: JSON.stringify(data),
  });
}

function del<T>(endpoint: string, options?: RequestOptions): Promise<T> {
  return request<T>(endpoint, { ...options, method: 'DELETE' });
}

export const apiClient = {
  get,
  post,
  patch,
  delete: del,
  request,
};

export type { ApiError };
