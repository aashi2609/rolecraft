"use client";

import React, { Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { useUser } from '@/context/UserContext';
import { Button } from '@/components/ui/Button';
import { FormField, Input } from '@/components/ui/FormField';
import Link from 'next/link';
import { BackgroundVideo } from '@/components/BackgroundVideo';

function SignupForm() {
  const searchParams = useSearchParams();
  const role = searchParams.get('role') as 'candidate' | 'company' || 'candidate';
  const router = useRouter();
  const { login } = useUser();

  const handleSignup = (e: React.FormEvent) => {
    e.preventDefault();
    login(role);
    if (role === 'candidate') {
      router.push('/onboarding/profile');
    } else {
      router.push('/company/dashboard');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4 relative">
      <BackgroundVideo />
      
      <div className="w-full max-w-md p-8 bg-white/90 backdrop-blur-md rounded-2xl shadow-xl border border-border relative z-10">
        <h1 className="text-3xl font-display text-foreground mb-2">Create an account</h1>
        <p className="text-muted-foreground mb-8 text-sm">
          Sign up as a <span className="font-semibold text-accent">{role}</span>
        </p>

        <form onSubmit={handleSignup} className="space-y-4">
          {role === 'company' ? (
            <FormField label="Company Name" required><Input required /></FormField>
          ) : (
            <FormField label="Full Name" required><Input required /></FormField>
          )}
          
          <FormField label="Email" required><Input type="email" required /></FormField>
          <FormField label="Password" required><Input type="password" required /></FormField>
          
          {role === 'company' && (
            <FormField label="Industry"><Input placeholder="e.g. Technology" /></FormField>
          )}

          <Button type="submit" className="w-full mt-4">Create Account</Button>
        </form>

        <div className="mt-6 text-center text-sm text-muted-foreground">
          Already have an account? <Link href="/signin" className="text-foreground hover:underline font-medium">Sign in</Link>
        </div>
      </div>
    </div>
  );
}

export default function SignupPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <SignupForm />
    </Suspense>
  );
}
