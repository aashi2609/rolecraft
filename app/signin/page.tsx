"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useUser } from '@/context/UserContext';
import { Button } from '@/components/ui/Button';
import { FormField, Input } from '@/components/ui/FormField';
import Link from 'next/link';
import { Logo } from '@/components/Logo';

export default function SigninPage() {
  const router = useRouter();
  const { signInWithApi } = useUser();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSignin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await signInWithApi(email, password);
      // Route to onboarding if profile is incomplete, otherwise to dashboard
      if (res.role === 'admin') {
        router.push('/admin/dashboard');
      } else if (res.role === 'company') {
        router.push(res.companyProfileComplete ? '/company/dashboard' : '/onboarding/company-profile');
      } else {
        router.push(res.profileComplete ? '/dashboard' : '/onboarding/profile');
      }
    } catch (err: any) {
      setError(err?.detail || err?.message || 'Sign in failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-app-surface">
      <header className="flex items-center px-6 md:px-12 py-5 border-b border-border bg-white">
        <Logo />
      </header>

      <div className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-lg p-8 md:p-10 bg-white rounded-2xl shadow-card border border-border">
          <h1 className="text-2xl font-bold text-foreground mb-2">Welcome back</h1>
          <p className="text-muted-foreground mb-8 text-sm">
            Enter your credentials to access your account
          </p>

          <form onSubmit={handleSignin} className="space-y-4">
            <FormField label="Email" required>
              <Input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
              />
            </FormField>
            <FormField label="Password" required>
              <Input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </FormField>

            {error && <p className="text-sm text-red-600">{error}</p>}

            <Button type="submit" className="w-full mt-4" disabled={loading}>
              {loading ? 'Signing in…' : 'Sign In'}
            </Button>
          </form>

          <div className="mt-6 text-center text-sm text-muted-foreground">
            Don&apos;t have an account?{' '}
            <Link href="/" className="text-primary hover:underline font-medium">
              Get started
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
