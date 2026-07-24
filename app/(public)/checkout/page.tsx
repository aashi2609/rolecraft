"use client";

import React, { useState, useEffect, Suspense } from 'react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { FormField, Input } from '@/components/ui/FormField';
import { CreditCard, Wallet, Smartphone, Landmark, CheckCircle } from 'lucide-react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useUser } from '@/context/UserContext';
import { getPlanById, formatPlanPrice, type PlanId } from '@/lib/plans';
import { Logo } from '@/components/Logo';

function CheckoutForm() {
  const [activeTab, setActiveTab] = useState('card');
  const [isAnnual, setIsAnnual] = useState(true);

  const router = useRouter();
  const searchParams = useSearchParams();
  const { isAuthenticated, setPlan, role: ctxRole } = useUser();
  const planId = (searchParams.get('plan') || 'premium') as PlanId;
  const roleParam = searchParams.get('role');
  const next = searchParams.get('next');
  const role = roleParam === 'company' || roleParam === 'candidate' ? roleParam : ctxRole;
  const planDef = getPlanById(planId);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push(`/signin?redirect=/checkout?plan=${planId}&role=${role || 'candidate'}&next=${next || ''}`);
    }
  }, [isAuthenticated, router, planId, role, next]);

  const handlePay = () => {
    setPlan(planId);
    if (next === 'onboarding') {
      router.push(role === 'company' ? '/onboarding/company-profile' : '/onboarding/profile');
      return;
    }
    router.push(role === 'company' ? '/company/dashboard' : '/dashboard');
  };

  if (!isAuthenticated) return null;

  const priceLabel = planDef
    ? `${formatPlanPrice(planDef, isAnnual)}${planDef.isFree ? '' : isAnnual ? '/mo billed annually' : '/mo'}`
    : '—';

  return (
    <div className="min-h-screen bg-app-surface">
      <header className="flex items-center px-6 md:px-12 py-5 border-b border-border bg-white">
        <Logo />
      </header>

      <div className="max-w-5xl mx-auto px-4 py-10">
        <div className="mb-8">
          <Link
            href={`/subscribe?role=${role === 'company' ? 'company' : 'candidate'}`}
            className="text-primary hover:underline text-sm font-semibold"
          >
            &larr; Back to plans
          </Link>
          <h1 className="text-3xl font-bold text-foreground mt-4">Checkout</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Complete payment to activate your {planDef?.name || planId} plan.
          </p>
        </div>

        <div className="flex flex-col lg:flex-row gap-8">
          <div className="flex-1 space-y-6">
            <Card className="p-0 overflow-hidden">
              <div className="bg-primary p-6 text-primary-foreground flex justify-between items-center">
                <div>
                  <h2 className="text-xl font-bold capitalize">{planDef?.name || planId} Plan</h2>
                  <p className="text-primary-foreground/80 text-sm mt-1">
                    {planDef?.description || 'Unlock full access'}
                  </p>
                </div>
                <div className="text-right">
                  <div className="text-2xl font-bold">{priceLabel}</div>
                </div>
              </div>
              {!planDef?.isFree && (
                <div className="p-6 bg-white border-b border-border flex flex-wrap gap-6">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="billing"
                      checked={!isAnnual}
                      onChange={() => setIsAnnual(false)}
                      className="w-4 h-4 accent-primary"
                    />
                    <span className="text-foreground font-medium text-sm">
                      Monthly ({planDef ? formatPlanPrice(planDef, false) : ''}/mo)
                    </span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="billing"
                      checked={isAnnual}
                      onChange={() => setIsAnnual(true)}
                      className="w-4 h-4 accent-primary"
                    />
                    <span className="text-foreground font-medium text-sm">
                      Annually ({planDef ? formatPlanPrice(planDef, true) : ''}/mo){' '}
                      <span className="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded ml-1">
                        Save ~20%
                      </span>
                    </span>
                  </label>
                </div>
              )}
            </Card>

            <Card>
              <h3 className="text-lg font-bold text-foreground mb-6">Payment Method</h3>

              <div className="flex border-b border-border mb-6 overflow-x-auto">
                {[
                  { id: 'card', label: 'Credit/Debit Card', icon: CreditCard },
                  { id: 'upi', label: 'UPI', icon: Smartphone },
                  { id: 'netbanking', label: 'Net Banking', icon: Landmark },
                  { id: 'wallet', label: 'Wallet', icon: Wallet },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    type="button"
                    onClick={() => setActiveTab(tab.id)}
                    className={`flex items-center gap-2 px-4 py-3 font-semibold text-sm whitespace-nowrap border-b-2 transition-colors ${
                      activeTab === tab.id
                        ? 'border-primary text-primary'
                        : 'border-transparent text-muted-foreground hover:text-foreground'
                    }`}
                  >
                    <tab.icon className="w-4 h-4" /> {tab.label}
                  </button>
                ))}
              </div>

              {activeTab === 'card' && (
                <div className="space-y-4">
                  <FormField label="Card Number">
                    <Input placeholder="0000 0000 0000 0000" />
                  </FormField>
                  <div className="grid grid-cols-2 gap-4">
                    <FormField label="Expiry Date">
                      <Input placeholder="MM/YY" />
                    </FormField>
                    <FormField label="CVV">
                      <Input type="password" placeholder="123" />
                    </FormField>
                  </div>
                  <FormField label="Name on Card">
                    <Input placeholder="John Doe" />
                  </FormField>
                </div>
              )}
              {activeTab === 'upi' && (
                <div className="space-y-4 py-4 text-center">
                  <p className="text-muted-foreground mb-4">Enter your UPI ID to receive a payment request.</p>
                  <FormField label="UPI ID">
                    <Input placeholder="username@upi" />
                  </FormField>
                </div>
              )}
              {activeTab === 'netbanking' && (
                <div className="space-y-4 py-4">
                  <FormField label="Select Bank">
                    <select className="w-full px-3 py-2 bg-white border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary text-foreground">
                      <option>HDFC Bank</option>
                      <option>SBI</option>
                      <option>ICICI Bank</option>
                    </select>
                  </FormField>
                </div>
              )}
              {activeTab === 'wallet' && (
                <div className="space-y-4 py-4">
                  <FormField label="Wallet">
                    <select className="w-full px-3 py-2 bg-white border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary text-foreground">
                      <option>Amazon Pay</option>
                      <option>Paytm</option>
                      <option>PhonePe</option>
                    </select>
                  </FormField>
                </div>
              )}
            </Card>

            <Button variant="primary" size="lg" className="w-full text-lg" onClick={handlePay}>
              Pay Securely &amp; Continue
            </Button>
            <p className="text-center text-sm text-muted-foreground flex items-center justify-center gap-1">
              <CheckCircle className="w-4 h-4 text-green-500" /> Secure 256-bit SSL encryption
            </p>
          </div>

          <div className="w-full lg:w-80 space-y-6">
            <Card className="bg-primary/5 border-primary/15">
              <h3 className="font-bold text-foreground mb-4">Included</h3>
              <ul className="space-y-3 text-sm text-foreground/80">
                {(planDef?.features || ['Full plan access']).map((f) => (
                  <li key={f} className="flex items-start gap-2">
                    <CheckCircle className="w-4 h-4 text-primary mt-0.5 shrink-0" /> {f}
                  </li>
                ))}
              </ul>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function CheckoutPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center">Loading checkout...</div>}>
      <CheckoutForm />
    </Suspense>
  );
}
