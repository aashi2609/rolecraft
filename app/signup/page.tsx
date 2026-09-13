"use client";

import React, { Suspense, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { useUser } from '@/context/UserContext';
import { Button } from '@/components/ui/Button';
import { FormField, Input } from '@/components/ui/FormField';
import Link from 'next/link';
import { SearchableCombobox } from '@/components/ui/SearchableCombobox';
import { Logo } from '@/components/Logo';
import { isFreePlan, type PlanId } from '@/lib/plans';

function SignupForm() {
  const searchParams = useSearchParams();
  const role = (searchParams.get('role') as 'candidate' | 'company') || 'candidate';
  const plan = (searchParams.get('plan') as PlanId) || (role === 'company' ? 'corporate_annual' : 'complete');
  const router = useRouter();
  const { signUpWithApi, setPlan } = useUser();
  const [industry, setIndustry] = useState('');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await signUpWithApi({
        email,
        password,
        role,
        name: role === 'company' ? name : name,
        industry: role === 'company' ? industry : undefined,
        plan,
      });

      // Auto-activate plan for now until real payment gateway (Stripe/Razorpay) is connected
      await setPlan(plan);
      router.push(role === 'candidate' ? '/onboarding/profile' : '/onboarding/company-profile');
    } catch (err: any) {
      setError(err?.detail || err?.message || 'Signup failed');
    } finally {
      setLoading(false);
    }
  };

  const INDUSTRIES = [
    'Technology / IT Services',
    'EdTech',
    'FinTech',
    'E-commerce',
    'Healthcare',
    'Manufacturing',
    'BFSI (Banking, Financial Services & Insurance)',
    'Consulting',
    'Retail',
    'Media & Entertainment',
    'Logistics & Supply Chain',
    'Real Estate',
    'Telecommunications',
    'Automotive',
    'Other',
  ];

  return (
    <div className="min-h-screen flex flex-col bg-app-surface">
      <header className="flex items-center justify-between px-6 md:px-12 py-5 border-b border-border bg-white">
        <Logo />
        <Link href={`/subscribe?role=${role}`} className="text-sm text-muted-foreground hover:text-primary">
          Change plan
        </Link>
      </header>

      <div className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-lg p-8 md:p-10 bg-white rounded-2xl shadow-card border border-border">
          <p className="text-xs font-semibold uppercase tracking-wide text-primary mb-2">
            Plan: {plan}
          </p>
          <h1 className="text-2xl font-bold text-foreground mb-2">Create an account</h1>
          <p className="text-muted-foreground mb-8 text-sm">
            Sign up as a <span className="font-semibold text-primary">{role}</span>
          </p>

          <form onSubmit={handleSignup} className="space-y-4">
            <FormField label={role === 'company' ? 'Company Name' : 'Full Name'} required>
              <Input required value={name} onChange={(e) => setName(e.target.value)} />
            </FormField>

            <FormField label="Email" required>
              <Input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
            </FormField>
            <FormField label="Password" required>
              <Input
                type="password"
                required
                minLength={6}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </FormField>

            {role === 'company' && (
              <FormField label="Industry" required>
                <SearchableCombobox
                  options={INDUSTRIES}
                  value={industry}
                  onChange={setIndustry}
                  placeholder="Select or type your industry"
                />
              </FormField>
            )}

            {error && <p className="text-sm text-red-600">{error}</p>}

            <Button type="submit" className="w-full mt-4" disabled={loading}>
              {loading ? 'Creating Account…' : 'Create Account'}
            </Button>
          </form>

          <div className="mt-6 text-center text-sm text-muted-foreground">
            Already have an account?{' '}
            <Link href="/signin" className="text-primary hover:underline font-medium">
              Sign in
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function SignupPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center">Loading...</div>}>
      <SignupForm />
    </Suspense>
  );
}
