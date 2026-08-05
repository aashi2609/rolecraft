"use client";

import React, { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Check } from 'lucide-react';
import Link from 'next/link';
import { COMPANY_PLANS, formatPlanPrice } from '@/lib/plans';

export default function CompanyPricingPage() {
  const [isAnnual, setIsAnnual] = useState(false);

  return (
    <div className="py-12 px-4 max-w-5xl mx-auto text-center">
      <h1 className="text-3xl font-bold text-foreground mb-3">Plans that scale with your hiring</h1>
      <p className="text-muted-foreground mb-10 max-w-xl mx-auto">
        Find the perfect candidates faster. Choose a plan tailored to your team.
      </p>

      <div className="flex items-center justify-center gap-3 mb-12">
        <span className={`text-sm font-medium ${!isAnnual ? 'text-foreground' : 'text-muted-foreground'}`}>
          Monthly
        </span>
        <button
          type="button"
          className="w-14 h-7 rounded-full relative"
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
          Annually
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-left">
        {COMPANY_PLANS.map((plan) => (
          <Card
            key={plan.id}
            className={`relative flex flex-col p-6 ${plan.popular ? 'border-primary shadow-md' : ''}`}
          >
            {plan.popular && (
              <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-primary text-primary-foreground px-3 py-1 rounded-full text-xs font-bold uppercase">
                Most Popular
              </div>
            )}
            <h3 className="text-xl font-bold">{plan.name}</h3>
            <p className="text-muted-foreground text-sm mt-1 mb-4">{plan.description}</p>
            <div className="mb-6">
              <span className="text-4xl font-bold">{formatPlanPrice(plan, isAnnual)}</span>
              <span className="text-muted-foreground text-sm">
                /{plan.isFree ? 'forever' : 'mo'}
              </span>
            </div>
            <ul className="space-y-3 mb-8 flex-1">
              {plan.features.map((f) => (
                <li key={f} className="flex gap-2 text-sm">
                  <Check className="w-4 h-4 text-primary shrink-0 mt-0.5" />
                  {f}
                </li>
              ))}
            </ul>
            <Link href={plan.isFree ? `/signup?role=company&plan=${plan.id}` : `/checkout?plan=${plan.id}&role=company`} className="mt-auto block">
              <Button variant={plan.popular ? 'primary' : 'outline'} className="w-full">
                {plan.isFree ? 'Get Started' : `Choose ${plan.name}`}
              </Button>
            </Link>
          </Card>
        ))}
      </div>
    </div>
  );
}
