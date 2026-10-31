"use client";

import React, { useState, useEffect, Suspense } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { FormField, Input } from '@/components/ui/FormField';
import Link from 'next/link';
import { AlertCircle, CheckCircle2 } from 'lucide-react';
import { useSearchParams, useRouter } from 'next/navigation';
import { authApi } from '@/lib/api';

function ResetPasswordContent() {
  const [token, setToken] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [status, setStatus] = useState<'loading' | 'form' | 'success' | 'error'>('loading');
  const [errorMsg, setErrorMsg] = useState('');
  const searchParams = useSearchParams();
  const router = useRouter();

  useEffect(() => {
    const t = searchParams.get('token');
    if (t) {
      setToken(t);
      setStatus('form');
      // Remove token from URL for security
      window.history.replaceState({}, '', '/reset-password');
    } else {
      setStatus('error');
      setErrorMsg('No reset token provided');
    }
  }, [searchParams]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirmPassword) {
      setErrorMsg('Passwords do not match');
      return;
    }
    if (password.length < 8) {
      setErrorMsg('Password must be at least 8 characters');
      return;
    }

    try {
      await authApi.resetPassword(token, password);
      setStatus('success');
    } catch {
      setStatus('error');
      setErrorMsg('Invalid or expired reset link');
    }
  };

  return (
    <div className="min-h-screen bg-surface-soft flex items-center justify-center p-4">
      <Card className="w-full max-w-md p-8">
        {status === 'loading' && (
          <div className="text-center">
            <div className="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full mx-auto mb-4"></div>
            <p className="text-ink-muted">Loading...</p>
          </div>
        )}

        {status === 'form' && (
          <>
            <h1 className="text-2xl font-bold text-ink mb-2">Reset Password</h1>
            <p className="text-ink-muted mb-6 text-sm">Enter your new password below.</p>
            
            <form onSubmit={handleSubmit} className="space-y-4">
              <FormField label="New Password" required>
                <Input
                  type="password"
                  placeholder="Min 8 chars, letter + number"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </FormField>

              <FormField label="Confirm Password" required>
                <Input
                  type="password"
                  placeholder="Confirm new password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                />
              </FormField>

              {errorMsg && (
                <div className="flex gap-2 text-sm text-red-600">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  {errorMsg}
                </div>
              )}

              <Button type="submit" size="lg" className="w-full">
                Reset Password
              </Button>
            </form>
          </>
        )}

        {status === 'success' && (
          <div className="text-center">
            <div className="w-16 h-16 bg-green-50 text-green-500 rounded-full flex items-center justify-center mx-auto mb-4">
              <CheckCircle2 className="w-8 h-8" />
            </div>
            <h2 className="text-2xl font-bold text-ink mb-2">Password Reset</h2>
            <p className="text-ink-muted mb-6 text-sm">Your password has been reset successfully.</p>
            <Link href="/signin">
              <Button className="w-full">Return to Sign In</Button>
            </Link>
          </div>
        )}

        {status === 'error' && (
          <div className="text-center">
            <div className="w-16 h-16 bg-red-50 text-red-500 rounded-full flex items-center justify-center mx-auto mb-4">
              <AlertCircle className="w-8 h-8" />
            </div>
            <h2 className="text-2xl font-bold text-ink mb-2">Invalid Link</h2>
            <p className="text-ink-muted mb-6 text-sm">{errorMsg || 'This reset link has expired or is invalid.'}</p>
            <Link href="/forgot-password">
              <Button variant="outline" className="w-full">Request New Link</Button>
            </Link>
          </div>
        )}
      </Card>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-surface-soft flex items-center justify-center p-4"><div className="text-center"><div className="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full mx-auto mb-4"></div><p className="text-ink-muted">Loading...</p></div></div>}>
      <ResetPasswordContent />
    </Suspense>
  );
}
