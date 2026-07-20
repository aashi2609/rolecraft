"use client";

import React, { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Check } from 'lucide-react';

export default function CompanyPricingPage() {
  const [isAnnual, setIsAnnual] = useState(false);

  const plans = [
    {
      name: 'Starter',
      description: 'Perfect for small teams hiring occasionally.',
      price: isAnnual ? '₹0' : '₹0',
      period: 'forever',
      features: ['Up to 2 active job postings', 'Basic candidate ranking', 'Email support'],
      cta: 'Get Started',
      popular: false,
    },
    {
      name: 'Growth',
      description: 'For growing companies with consistent hiring needs.',
      price: isAnnual ? '₹3,999' : '₹4,999',
      period: 'per month',
      features: ['Unlimited job postings', 'Priority ranking refresh', 'See full candidate profiles', 'Direct candidate messaging'],
      cta: 'Upgrade to Growth',
      popular: true,
    },
    {
      name: 'Scale',
      description: 'Advanced tools for high-volume recruitment.',
      price: isAnnual ? '₹9,999' : '₹12,999',
      period: 'per month',
      features: ['Everything in Growth', 'Dedicated account support', 'Bulk hiring tools', 'Advanced analytics dashboard', 'Custom integrations'],
      cta: 'Contact Sales',
      popular: false,
    }
  ];

  return (
    <div className="min-h-[90vh] bg-slate-50 py-16">
      <div className="max-w-7xl mx-auto px-4 text-center">
        
        <h1 className="text-4xl font-bold text-slate-900 mb-4">Plans that scale with your hiring</h1>
        <p className="text-xl text-slate-500 mb-10 max-w-2xl mx-auto">
          Find the perfect candidates faster. Choose a plan tailored to your team's needs.
        </p>

        {/* Toggle */}
        <div className="flex items-center justify-center gap-3 mb-16">
          <span className={`text-sm font-medium ${!isAnnual ? 'text-slate-900' : 'text-slate-500'}`}>Monthly</span>
          <button 
            className="w-14 h-7 rounded-full bg-slate-200 relative focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 transition-colors"
            onClick={() => setIsAnnual(!isAnnual)}
            style={{ backgroundColor: isAnnual ? '#2563EB' : '#e2e8f0' }}
          >
            <div className={`w-5 h-5 bg-white rounded-full absolute top-1 transition-all ${isAnnual ? 'left-8' : 'left-1'} shadow-sm`} />
          </button>
          <span className={`text-sm font-medium ${isAnnual ? 'text-slate-900' : 'text-slate-500'}`}>Annually <span className="text-primary text-xs ml-1 bg-blue-50 px-2 py-0.5 rounded-full">Save ~20%</span></span>
        </div>

        {/* Pricing Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto text-left">
          {plans.map((plan) => (
            <Card key={plan.name} className={`relative flex flex-col ${plan.popular ? 'border-primary shadow-lg scale-105 z-10' : ''}`}>
              {plan.popular && (
                <div className="absolute top-0 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-primary text-white px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wide">
                  Most Popular
                </div>
              )}
              
              <div className="mb-6">
                <h3 className="text-2xl font-bold text-slate-900">{plan.name}</h3>
                <p className="text-slate-500 mt-2 text-sm">{plan.description}</p>
              </div>
              
              <div className="mb-6 flex items-baseline gap-1">
                <span className="text-4xl font-bold text-slate-900">{plan.price}</span>
                <span className="text-slate-500 text-sm">/{plan.period}</span>
              </div>
              
              <ul className="space-y-4 mb-8 flex-1">
                {plan.features.map((feature, i) => (
                  <li key={i} className="flex items-start gap-3">
                    <Check className="w-5 h-5 text-primary shrink-0" />
                    <span className="text-slate-700">{feature}</span>
                  </li>
                ))}
              </ul>
              
              <Button variant={plan.popular ? 'primary' : 'outline'} className="w-full mt-auto">
                {plan.cta}
              </Button>
            </Card>
          ))}
        </div>

      </div>
    </div>
  );
}
