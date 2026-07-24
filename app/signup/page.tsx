"use client";

import React, { Suspense } from 'react';
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
  const plan = (searchParams.get('plan') as PlanId) || (role === 'company' ? 'starter' : 'basic');
  const router = useRouter();
  const { login, setPendingPlan, setPlan } = useUser();
  const [industry, setIndustry] = React.useState('');

  const handleSignup = (e: React.FormEvent) => {
    e.preventDefault();
    login(role, plan);

    if (isFreePlan(plan)) {
      setPlan(plan);
      if (role === 'candidate') {
        router.push('/onboarding/profile');
      } else {
        router.push('/onboarding/company-profile');
      }
    } else {
      setPendingPlan(plan);
      router.push(`/checkout?plan=${plan}&role=${role}&next=onboarding`);
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
            {role === 'company' ? (
              <FormField label="Company Name" required>
                <Input required />
              </FormField>
            ) : (
              <FormField label="Full Name" required>
                <Input required />
              </FormField>
            )}

            <FormField label="Email" required>
              <Input type="email" required />
            </FormField>
            <FormField label="Password" required>
              <Input type="password" required />
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

            <Button type="submit" className="w-full mt-4">
              {isFreePlan(plan) ? 'Create Account' : 'Continue to Checkout'}
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
