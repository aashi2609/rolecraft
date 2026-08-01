"use client";

import React, { Suspense, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { Check } from 'lucide-react';
import Link from 'next/link';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Logo } from '@/components/Logo';
import { useUser } from '@/context/UserContext';
import {
  getPlansForRole,
  formatPlanPrice,
  isFreePlan,
  type PlanId,
  type Role,
} from '@/lib/plans';

function SubscribeContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { isAuthenticated, setPlan, setPendingPlan, plan: currentPlan, profileComplete, companyProfileComplete } = useUser();
  const roleParam = searchParams.get('role');
  const role: Role = roleParam === 'company' ? 'company' : 'candidate';
  const [isAnnual, setIsAnnual] = useState(false);

  const plans = getPlansForRole(role);

  const selectPlan = (planId: PlanId) => {
    // Logged-in upgrade / plan change
    if (isAuthenticated) {
      if (isFreePlan(planId)) {
        setPlan(planId);
        // Route to onboarding if profile is not complete, otherwise to dashboard
        if (role === 'company') {
          router.push(companyProfileComplete ? '/company/dashboard' : '/onboarding/company-profile');
        } else {
          router.push(profileComplete ? '/dashboard' : '/onboarding/profile');
        }
        return;
      }
      setPendingPlan(planId);
      router.push(`/checkout?plan=${planId}&role=${role}`);
      return;
    }

    // New user entry flow: plan → signup
    router.push(`/signup?role=${role}&plan=${planId}`);
  };

  return (
    <div className="min-h-screen bg-app-surface">
      <header className="flex items-center justify-between px-6 md:px-12 py-5 border-b border-border bg-white">
        <Logo href={isAuthenticated ? (role === 'company' ? '/company/dashboard' : '/dashboard') : '/'} />
        {!isAuthenticated && (
          <Link href="/signin" className="text-sm font-medium text-primary hover:underline">
            Sign In
          </Link>
        )}
      </header>

      <div className="max-w-5xl mx-auto px-4 py-14 text-center">
        <p className="text-sm font-semibold text-primary mb-2 uppercase tracking-wide">
          {isAuthenticated ? 'Manage your plan' : 'Step 1 of 2 · Choose your plan'}
        </p>
        <h1 className="text-3xl md:text-4xl font-bold text-foreground mb-3">
          {role === 'company' ? 'Plans that scale with your hiring' : 'Simple, transparent pricing'}
        </h1>
        <p className="text-muted-foreground mb-10 max-w-xl mx-auto">
          {isAuthenticated
            ? `You're currently on ${currentPlan}. Select a plan to upgrade or switch.`
            : role === 'company'
              ? 'Select a plan before creating your employer account. You can change it later.'
              : 'Pick a plan before signup. Free to start — upgrade anytime for multi-role resumes.'}
        </p>

        <div className="flex items-center justify-center gap-3 mb-12">
          <span className={`text-sm font-medium ${!isAnnual ? 'text-foreground' : 'text-muted-foreground'}`}>
            Monthly
          </span>
          <button
            type="button"
            className="w-14 h-7 rounded-full relative focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 transition-colors"
            onClick={() => setIsAnnual(!isAnnual)}
            style={{ backgroundColor: isAnnual ? '#2563EB' : '#e2e8f0' }}
            aria-label="Toggle annual billing"
          >
            <div
              className={`w-5 h-5 bg-white rounded-full absolute top-1 transition-all shadow-sm ${
                isAnnual ? 'left-8' : 'left-1'
              }`}
            />
          </button>
          <span className={`text-sm font-medium ${isAnnual ? 'text-foreground' : 'text-muted-foreground'}`}>
            Annually{' '}
            <span className="text-primary text-xs ml-1 bg-primary/10 px-2 py-0.5 rounded-full">
              Save ~20%
            </span>
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-left">
          {plans.map((plan) => {
            const isCurrent = isAuthenticated && currentPlan === plan.id;
            return (
              <Card
                key={plan.id}
                className={`relative flex flex-col p-6 ${
                  plan.popular || isCurrent ? 'border-primary shadow-md ring-1 ring-primary/20' : ''
                }`}
              >
                {plan.popular && !isCurrent && (
                  <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-primary text-primary-foreground px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wide">
                    Most Popular
                  </div>
                )}
                {isCurrent && (
                  <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-primary text-primary-foreground px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wide">
                    Current
                  </div>
                )}
                <div className="mb-5">
                  <h3 className="text-xl font-bold text-foreground">{plan.name}</h3>
                  <p className="text-muted-foreground mt-1 text-sm">{plan.description}</p>
                </div>
                <div className="mb-5 flex items-baseline gap-1">
                  <span className="text-4xl font-bold text-foreground">
                    {formatPlanPrice(plan, isAnnual)}
                  </span>
                  <span className="text-muted-foreground text-sm">
                    /{plan.isFree ? 'forever' : 'mo'}
                  </span>
                </div>
                <ul className="space-y-3 mb-8 flex-1">
                  {plan.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-2.5">
                      <Check className="w-4 h-4 text-primary shrink-0 mt-0.5" />
                      <span className="text-sm text-foreground/80">{feature}</span>
                    </li>
                  ))}
                </ul>
                <Button
                  variant={plan.popular || isCurrent ? 'primary' : 'outline'}
                  className="w-full"
                  disabled={isCurrent}
                  onClick={() => selectPlan(plan.id)}
                >
                  {isCurrent
                    ? 'Current plan'
                    : plan.isFree
                      ? isAuthenticated
                        ? 'Switch to free'
                        : 'Continue free'
                      : isAuthenticated
                        ? `Upgrade to ${plan.name}`
                        : `Select ${plan.name}`}
                </Button>
              </Card>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export default function SubscribePage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center">Loading plans...</div>}>
      <SubscribeContent />
    </Suspense>
  );
}
