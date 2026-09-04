"use client";

import React, { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { FormField, Input } from '@/components/ui/FormField';
import Link from 'next/link';
import { Mail, ArrowLeft, CheckCircle2 } from 'lucide-react';
import { authApi } from '@/lib/api';

export default function ForgotPasswordPage() {
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [email, setEmail] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;
    try {
      await authApi.forgotPassword(email);
    } catch {
      /* always show success */
    }
    setIsSubmitted(true);
  };

  return (
    <div className="min-h-screen bg-surface-soft flex items-center justify-center p-4">
      <Card className="w-full max-w-md p-8 relative overflow-hidden">
        
        {/* Decorative element */}
        <div className="absolute top-0 right-0 w-32 h-32 bg-primary/5 rounded-bl-full -z-10"></div>
        <div className="absolute bottom-0 left-0 w-24 h-24 bg-blue-100/50 rounded-tr-full -z-10"></div>

        <Link href="/signin" className="inline-flex items-center text-sm text-ink-muted hover:text-primary mb-6 transition-colors">
          <ArrowLeft className="w-4 h-4 mr-1" /> Back to Sign In
        </Link>

        {!isSubmitted ? (
          <>
            <div className="w-12 h-12 bg-brand-blue/10 text-primary rounded-xl flex items-center justify-center mb-6">
              <Mail className="w-6 h-6" />
            </div>
            
            <h1 className="text-2xl font-bold text-ink mb-2">Forgot Password?</h1>
            <p className="text-ink-muted mb-8 text-sm">
              No worries, we&apos;ll send you reset instructions. Enter the email associated with your account.
            </p>

            <form onSubmit={handleSubmit} className="space-y-6">
              <FormField label="Email Address" required>
                <Input 
                  type="email" 
                  placeholder="Enter your email" 
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </FormField>

              <Button type="submit" size="lg" className="w-full">
                Reset Password
              </Button>
            </form>
          </>
        ) : (
          <div className="text-center py-6">
            <div className="w-16 h-16 bg-green-50 text-green-500 rounded-full flex items-center justify-center mx-auto mb-6">
              <CheckCircle2 className="w-8 h-8" />
            </div>
            <h2 className="text-2xl font-bold text-ink mb-2">Check your email</h2>
            <p className="text-ink-muted mb-8 text-sm">
              We&apos;ve sent a password reset link to <span className="font-medium text-ink">{email}</span>.
            </p>
            <Link href="/signin">
              <Button variant="outline" className="w-full">Return to Sign In</Button>
            </Link>
          </div>
        )}

      </Card>
    </div>
  );
}
