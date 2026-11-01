'use client';

import React, { ReactNode, ReactElement } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { AlertCircle } from 'lucide-react';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: (error: Error, retry: () => void) => ReactElement;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, State> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    console.error('Error caught by boundary:', error, errorInfo);
  }

  retry = (): void => {
    this.setState({ error: null });
  };

  render(): ReactNode {
    if (this.state.error) {
      if (this.props.fallback) {
        return this.props.fallback(this.state.error, this.retry);
      }

      return (
        <div className="min-h-screen flex items-center justify-center p-4 bg-background">
          <Card className="w-full max-w-md p-6 border-red-200 bg-red-50">
            <div className="flex gap-3">
              <AlertCircle className="w-6 h-6 text-red-600 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <h2 className="font-bold text-red-900 mb-2">Something went wrong</h2>
                <p className="text-sm text-red-800 mb-4">
                  {this.state.error.message || 'An unexpected error occurred.'}
                </p>
                <div className="flex gap-2">
                  <Button variant="outline" onClick={this.retry} className="text-red-600">
                    Try Again
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() => { if (typeof window !== 'undefined') window.location.href = '/'; }}
                    className="text-red-600"
                  >
                    Back to Home
                  </Button>
                </div>
              </div>
            </div>
          </Card>
        </div>
      );
    }

    return this.props.children;
  }
}
