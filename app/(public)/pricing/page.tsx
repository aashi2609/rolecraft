"use client";

import React, { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Check } from 'lucide-react';
import Link from 'next/link';
import { Logo } from '@/components/Logo';
import { CANDIDATE_PLANS, COMPANY_PLANS, formatPlanPrice, Role } from '@/lib/plans';
import { SwapCTAGroup } from '@/components/ui/SwapCTAGroup';

export default function PricingPage() {
  const [role, setRole] = useState<Role>('candidate');
  const [isAnnual, setIsAnnual] = useState(false);

  const plans = role === 'candidate' ? CANDIDATE_PLANS : COMPANY_PLANS;

  const getBillingPeriodLabel = (planId: string) => {
    if (planId === 'corporate_lifetime') return 'one-time';
    if (planId === 'corporate_annual') return '/year';
    return isAnnual ? '/mo (billed annually)' : '/mo';
  };

  return (
    <div className="min-h-screen bg-app-surface">
      <header className="flex items-center justify-between px-6 md:px-12 py-5 border-b border-border bg-white">
        <Logo />
        <Link href={`/subscribe?role=${role}`}>
          <Button size="sm">Get Started</Button>
        </Link>
      </header>

      <div className="max-w-5xl mx-auto px-4 py-16 text-center">
        <h1 className="text-3xl md:text-4xl font-bold text-foreground mb-3">
          Simple, transparent pricing
        </h1>
        <p className="text-muted-foreground mb-10 max-w-xl mx-auto">
          Choose the plan that fits your goals. Start your subscription today.
        </p>

        <div className="mb-8">
          <SwapCTAGroup
            action1={{
              label: 'For Job Seekers',
              onClick: () => setRole('candidate'),
              isActive: role === 'candidate'
            }}
            action2={{
              label: 'For Companies',
              onClick: () => setRole('company'),
              isActive: role === 'company'
            }}
          />
        </div>

        {role === 'candidate' && (
          <div className="flex items-center justify-center gap-3 mb-12">
            <span className={`text-sm font-medium ${!isAnnual ? 'text-foreground' : 'text-muted-foreground'}`}>
              Monthly
            </span>
            <button
              type="button"
              className="w-14 h-7 rounded-full relative focus:outline-none focus:ring-2 focus:ring-primary"
              onClick={() => setIsAnnual(!isAnnual)}
              style={{ backgroundColor: isAnnual ? '#2563EB' : '#e2e8f0' }}
            >
              <div
                className={`w-5 h-5 bg-white rounded-full absolute top-1 transition-all shadow-sm ${
                  isAnnual ? 'left-8' : 'left-1'
                }`}
              />
            </button>
            <span className={`text-sm font-medium ${isAnnual ? 'text-foreground' : 'text-muted-foreground'}`}>
              Annually <span className="text-xs text-primary bg-primary/10 px-2 py-0.5 rounded-full ml-1 font-semibold">Save 20%</span>
            </span>
          </div>
        )}

        <div className={`grid grid-cols-1 ${plans.length === 2 ? 'md:grid-cols-2 max-w-3xl' : 'md:grid-cols-3'} gap-6 mx-auto text-left`}>
          {plans.map((plan) => (
            <Card
              key={plan.id}
              className={`pricing-card relative flex flex-col p-6 ${plan.popular ? 'border-primary shadow-md is-popular' : ''}`}
            >
              {plan.popular && (
                <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-primary text-primary-foreground px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wide">
                  Most Popular
                </div>
              )}
              <h3 className="text-xl font-bold">{plan.name}</h3>
              <p className="text-muted-foreground text-sm mt-1 mb-4">{plan.description}</p>
              <div className="mb-6 flex items-baseline gap-1">
                <span className="text-4xl font-bold">{formatPlanPrice(plan, isAnnual)}</span>
                <span className="text-muted-foreground text-xs font-medium">
                  {getBillingPeriodLabel(plan.id)}
                </span>
              </div>
              <ul className="space-y-3 mb-8 flex-1">
                {plan.features.map((f) => (
                  <li key={f} className="flex gap-2 text-sm">
                    <Check className="w-4 h-4 text-primary shrink-0 mt-0.5" />
                    <span className="text-foreground/90">{f}</span>
                  </li>
                ))}
              </ul>
              <Link href={`/signup?role=${role}&plan=${plan.id}`} className="mt-auto block">
                <Button variant={plan.popular ? 'primary' : 'outline'} className="btn-inside w-full">
                  Choose {plan.name}
                </Button>
              </Link>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}

