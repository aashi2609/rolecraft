/**
 * Custom hook for data fetching with loading/error/empty/data states.
 *
 * Replaces try-catch + useState([loading, error, data]) pattern.
 * Provides consistent error handling, retry logic, and distinct states.
 *
 * Usage:
 * ```tsx
 * const { data, loading, error, empty, retry } = useApi(
 *   () => candidatesApi.search({ skills: ['React'] }),
 *   { dependencies: [skills] }
 * );
 *
 * if (loading) return <Spinner />;
 * if (error) return <ErrorBanner message={error} onRetry={retry} />;
 * if (empty) return <EmptyState />;
 * return <DataList items={data} />;
 * ```
 */

import { useEffect, useRef, useState } from 'react';
import { ApiError } from '@/lib/api';

interface UseApiOptions {
  dependencies?: any[];
  onError?: (err: ApiError | Error) => void;
  onSuccess?: (data: any) => void;
  autoRetry?: boolean; // Auto-retry on network errors
  retryDelay?: number; // ms
}

interface UseApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  empty: boolean;
  retry: () => void;
}

export function useApi<T = unknown>(
  asyncFn: () => Promise<T>,
  options: UseApiOptions = {}
): UseApiState<T> {
  const {
    dependencies = [],
    onError,
    onSuccess,
    autoRetry = false,
    retryDelay = 3000,
  } = options;

  const [state, setState] = useState<Omit<UseApiState<T>, 'retry'>>({
    data: null,
    loading: true,
    error: null,
    empty: false,
  });

  // Track retries to avoid infinite loops
  const retryCountRef = useRef(0);
  const maxRetriesRef = useRef(autoRetry ? 2 : 0);

  const fetchData = async () => {
    setState({ data: null, loading: true, error: null, empty: false });

    try {
      const result = await asyncFn();

      // Check if result is empty (array/object with no items)
      const isEmpty = Array.isArray(result) ? result.length === 0 : false;

      setState({
        data: result,
        loading: false,
        error: null,
        empty: isEmpty,
      });

      onSuccess?.(result);
      retryCountRef.current = 0; // Reset retry count on success
    } catch (err) {
      let errorMessage = 'An error occurred. Please try again.';

      if (err instanceof ApiError) {
        // HTTP error responses
        if (err.status === 401) {
          errorMessage = 'Session expired. Please sign in again.';
          // 401 handling (sign out) is done at API layer in lib/api.ts
        } else if (err.status === 403) {
          errorMessage =
            err.detail ||
            'You do not have permission to access this. Consider upgrading your plan.';
        } else if (err.status === 404) {
          errorMessage = err.detail || 'Resource not found.';
        } else if (err.status === 429) {
          errorMessage = 'Too many requests. Please try again in a moment.';
        } else if (err.status >= 500) {
          errorMessage = 'Server error. Please try again later.';
        } else {
          // 4xx validation errors
          errorMessage = err.detail || 'Request failed. Please check your input.';
        }
      } else if (err instanceof Error) {
        // Network errors, parsing errors, etc.
        if (err.message.toLowerCase().includes('network')) {
          errorMessage = 'Connection failed. Please check your internet and try again.';
        } else if (
          err.message.toLowerCase().includes('abort') ||
          err.message.toLowerCase().includes('cancelled')
        ) {
          errorMessage = 'Request was cancelled.';
        } else {
          errorMessage = err.message || 'An unexpected error occurred.';
        }
      }

      setState({
        data: null,
        loading: false,
        error: errorMessage,
        empty: false,
      });

      onError?.(err as ApiError | Error);

      // Auto-retry on network errors if enabled
      if (autoRetry && retryCountRef.current < maxRetriesRef.current) {
        retryCountRef.current++;
        setTimeout(() => fetchData(), retryDelay);
      }
    }
  };

  // Fetch on mount and when dependencies change
  useEffect(() => {
    retryCountRef.current = 0;
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, dependencies);

  return {
    ...state,
    retry: () => {
      retryCountRef.current = 0; // Reset on manual retry
      fetchData();
    },
  };
}
