import { ApiError } from '@/lib/api';
import { useCallback } from 'react';

export interface ToastConfig {
  showToast: (type: 'success' | 'error', message: string) => void;
}

/**
 * Hook to handle API errors with user-friendly messages.
 * Integrates with toast notifications to show errors to users.
 */
export function useApiError() {
  const handleError = useCallback(
    (
      error: unknown,
      showToast: (type: 'error', message: string) => void,
      defaultMessage = 'An error occurred. Please try again.'
    ): void => {
      let message = defaultMessage;

      if (error instanceof ApiError) {
        message = error.getUserMessage();
        console.error(`[${error.errorCode || 'unknown'}] ${error.detail}`, { status: error.status, type: error.type });
      } else if (error instanceof Error) {
        message = error.message || defaultMessage;
        console.error('Error:', error.message);
      } else {
        console.error('Unknown error:', error);
      }

      showToast('error', message);
    },
    []
  );

  return { handleError };
}
