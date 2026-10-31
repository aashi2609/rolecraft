'use client';

import React from 'react';
import { AlertCircle, X, RotateCw } from 'lucide-react';

interface ErrorBannerProps {
  message: string;
  onRetry?: () => void;
  onDismiss?: () => void;
  showRetry?: boolean;
  showDismiss?: boolean;
}

/**
 * Error banner with message, retry button, and dismiss option.
 *
 * Usage:
 * ```tsx
 * if (error) return <ErrorBanner message={error} onRetry={retry} />;
 * ```
 */
export function ErrorBanner({
  message,
  onRetry,
  onDismiss,
  showRetry = true,
  showDismiss = true,
}: ErrorBannerProps) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 p-4 flex items-start gap-4">
      <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
      <div className="flex-1 min-w-0">
        <p className="text-sm text-red-800">{message}</p>
      </div>
      <div className="flex items-center gap-2 flex-shrink-0">
        {showRetry && onRetry && (
          <button
            onClick={onRetry}
            className="inline-flex items-center gap-1 text-sm font-medium text-red-600 hover:text-red-700 transition"
          >
            <RotateCw className="w-4 h-4" />
            Retry
          </button>
        )}
        {showDismiss && onDismiss && (
          <button
            onClick={onDismiss}
            className="text-red-600 hover:text-red-700 transition"
          >
            <X className="w-5 h-5" />
          </button>
        )}
      </div>
    </div>
  );
}
