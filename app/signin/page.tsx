"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useUser } from '@/context/UserContext';
import { Button } from '@/components/ui/Button';
import { FormField, Input } from '@/components/ui/FormField';
import Link from 'next/link';
import { BackgroundVideo } from '@/components/BackgroundVideo';

export default function SigninPage() {
  const router = useRouter();
  const { login } = useUser();
  const [email, setEmail] = useState('');

  const handleSignin = (e: React.FormEvent) => {
    e.preventDefault();
    // Stub: simulate role based on email or default to candidate
    const isCompany = email.includes('@company.com');
    const role = isCompany ? 'company' : 'candidate';
    
    login(role);
    if (role === 'candidate') {
      router.push('/dashboard');
    } else {
      router.push('/company/dashboard');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4 relative">
      <BackgroundVideo />

      <div className="w-full max-w-md p-8 bg-white/90 backdrop-blur-md rounded-2xl shadow-xl border border-border relative z-10">
        <h1 className="text-3xl font-display text-foreground mb-2">Welcome back</h1>
        <p className="text-muted-foreground mb-8 text-sm">Enter your credentials to access your account</p>

        <form onSubmit={handleSignin} className="space-y-4">
          <FormField label="Email" required>
            <Input 
              type="email" 
              required 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="user@example.com (use @company.com for employer)" 
            />
          </FormField>
          <FormField label="Password" required>
            <Input type="password" required />
          </FormField>
          
          <Button type="submit" className="w-full mt-4">Sign In</Button>
        </form>

        <div className="mt-6 text-center text-sm text-muted-foreground">
          Don't have an account? <span className="text-foreground hover:underline font-medium cursor-pointer" onClick={() => router.push('/')}>Sign up</span>
        </div>
      </div>
    </div>
  );
}
