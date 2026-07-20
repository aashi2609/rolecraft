"use client";

import React, { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { FormField, Input } from '@/components/ui/FormField';
import { CreditCard, Wallet, Smartphone, Landmark, CheckCircle } from 'lucide-react';
import Link from 'next/link';

export default function CheckoutPage() {
  const [activeTab, setActiveTab] = useState('card');
  const [isAnnual, setIsAnnual] = useState(true);

  const handlePay = () => {
    alert("Payment successful! Console updated.");
    console.log("Payment processed for tab:", activeTab, isAnnual ? 'Annual' : 'Monthly');
  };

  return (
    <div className="min-h-screen bg-slate-50 py-10">
      <div className="max-w-5xl mx-auto px-4">
        
        <div className="mb-8">
          <Link href="/pricing" className="text-primary hover:underline text-sm font-semibold">&larr; Back to Pricing</Link>
          <h1 className="text-3xl font-bold text-slate-900 mt-4">Checkout</h1>
        </div>

        <div className="flex flex-col lg:flex-row gap-8">
          
          {/* Left Column: Form */}
          <div className="flex-1 space-y-6">
            <Card className="p-0 overflow-hidden">
              <div className="bg-slate-900 p-6 text-white flex justify-between items-center">
                <div>
                  <h2 className="text-xl font-bold">Premium Plan</h2>
                  <p className="text-slate-400 text-sm mt-1">Unlock your full career potential</p>
                </div>
                <div className="text-right">
                  <div className="text-2xl font-bold">{isAnnual ? '$108' : '$12'}</div>
                  <div className="text-slate-400 text-sm">{isAnnual ? 'per year' : 'per month'}</div>
                </div>
              </div>
              <div className="p-6 bg-white border-b border-slate-100 flex gap-6">
                <label className="flex items-center gap-2 cursor-pointer">
                   <input type="radio" name="billing" checked={!isAnnual} onChange={() => setIsAnnual(false)} className="w-4 h-4 text-primary" />
                   <span className="text-slate-700 font-medium">Billed Monthly ($12/mo)</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                   <input type="radio" name="billing" checked={isAnnual} onChange={() => setIsAnnual(true)} className="w-4 h-4 text-primary" />
                   <span className="text-slate-700 font-medium">Billed Annually ($9/mo) <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded ml-1">Save 25%</span></span>
                </label>
              </div>
            </Card>

            <Card>
              <h3 className="text-lg font-bold text-slate-900 mb-6">Payment Method</h3>
              
              <div className="flex border-b border-slate-200 mb-6 overflow-x-auto">
                <button onClick={() => setActiveTab('card')} className={`flex items-center gap-2 px-4 py-3 font-semibold text-sm whitespace-nowrap border-b-2 transition-colors ${activeTab === 'card' ? 'border-primary text-primary' : 'border-transparent text-slate-500 hover:text-slate-700'}`}>
                  <CreditCard className="w-4 h-4" /> Credit/Debit Card
                </button>
                <button onClick={() => setActiveTab('upi')} className={`flex items-center gap-2 px-4 py-3 font-semibold text-sm whitespace-nowrap border-b-2 transition-colors ${activeTab === 'upi' ? 'border-primary text-primary' : 'border-transparent text-slate-500 hover:text-slate-700'}`}>
                  <Smartphone className="w-4 h-4" /> UPI
                </button>
                <button onClick={() => setActiveTab('netbanking')} className={`flex items-center gap-2 px-4 py-3 font-semibold text-sm whitespace-nowrap border-b-2 transition-colors ${activeTab === 'netbanking' ? 'border-primary text-primary' : 'border-transparent text-slate-500 hover:text-slate-700'}`}>
                  <Landmark className="w-4 h-4" /> Net Banking
                </button>
                <button onClick={() => setActiveTab('wallet')} className={`flex items-center gap-2 px-4 py-3 font-semibold text-sm whitespace-nowrap border-b-2 transition-colors ${activeTab === 'wallet' ? 'border-primary text-primary' : 'border-transparent text-slate-500 hover:text-slate-700'}`}>
                  <Wallet className="w-4 h-4" /> Wallet
                </button>
              </div>

              {activeTab === 'card' && (
                <div className="space-y-4">
                  <FormField label="Card Number"><Input placeholder="0000 0000 0000 0000" /></FormField>
                  <div className="grid grid-cols-2 gap-4">
                    <FormField label="Expiry Date"><Input placeholder="MM/YY" /></FormField>
                    <FormField label="CVV"><Input type="password" placeholder="123" /></FormField>
                  </div>
                  <FormField label="Name on Card"><Input placeholder="John Doe" /></FormField>
                </div>
              )}
              {activeTab === 'upi' && (
                <div className="space-y-4 py-4 text-center">
                  <p className="text-slate-600 mb-4">Enter your UPI ID to receive a payment request.</p>
                  <FormField label="UPI ID"><Input placeholder="username@upi" /></FormField>
                </div>
              )}
              {activeTab === 'netbanking' && (
                <div className="space-y-4 py-4">
                  <FormField label="Select Bank">
                    <select className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary text-slate-900">
                      <option>HDFC Bank</option>
                      <option>SBI</option>
                      <option>ICICI Bank</option>
                    </select>
                  </FormField>
                </div>
              )}
              {activeTab === 'wallet' && (
                <div className="space-y-4 py-4">
                   <p className="text-slate-600 mb-4">Select your preferred wallet.</p>
                   <FormField label="Wallet">
                    <select className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary text-slate-900">
                      <option>Amazon Pay</option>
                      <option>Paytm</option>
                      <option>PhonePe</option>
                    </select>
                  </FormField>
                </div>
              )}
            </Card>

            <Button variant="primary" size="lg" className="w-full text-lg" onClick={handlePay}>
              Pay Securely {isAnnual ? '$108.00' : '$12.00'}
            </Button>
            <p className="text-center text-sm text-slate-500 flex items-center justify-center gap-1">
              <CheckCircle className="w-4 h-4 text-green-500" /> Secure 256-bit SSL encryption
            </p>
          </div>

          {/* Right Column: Benefits sidebar */}
          <div className="w-full lg:w-80 space-y-6">
            <Card className="bg-blue-50 border-blue-100">
              <h3 className="font-bold text-slate-900 mb-4">Premium Benefits</h3>
              <ul className="space-y-3 text-sm text-slate-700">
                <li className="flex items-start gap-2"><CheckCircle className="w-4 h-4 text-primary mt-0.5 shrink-0" /> Priority placement in search results</li>
                <li className="flex items-start gap-2"><CheckCircle className="w-4 h-4 text-primary mt-0.5 shrink-0" /> Unlimited resume downloads</li>
                <li className="flex items-start gap-2"><CheckCircle className="w-4 h-4 text-primary mt-0.5 shrink-0" /> See exactly who viewed your profile</li>
                <li className="flex items-start gap-2"><CheckCircle className="w-4 h-4 text-primary mt-0.5 shrink-0" /> Cover letter generator</li>
              </ul>
            </Card>

            <div className="p-6 bg-white rounded-xl shadow-sm border border-slate-100">
              <div className="flex gap-1 text-yellow-400 mb-3">
                {[1,2,3,4,5].map(i => <svg key={i} className="w-4 h-4 fill-current" viewBox="0 0 20 20"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" /></svg>)}
              </div>
              <p className="text-slate-600 text-sm italic">
                "Upgrading to Premium was the best decision I made. I landed interviews at top companies within 2 weeks of using the priority placement."
              </p>
              <div className="mt-4 flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-slate-200"></div>
                <div>
                  <div className="font-bold text-sm text-slate-900">Sarah Jenkins</div>
                  <div className="text-xs text-slate-500">Frontend Developer</div>
                </div>
              </div>
            </div>
          </div>

        </div>

      </div>
    </div>
  );
}
