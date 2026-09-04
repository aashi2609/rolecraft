"use client";

import React from 'react';
import Link from 'next/link';
import { Logo } from '@/components/Logo';
import { useUser } from '@/context/UserContext';

import { Globe, Mail, MessageSquare } from 'lucide-react';

export function Footer() {
  const { isAuthenticated } = useUser();
  if (isAuthenticated) return null;

  return (
    <footer className="bg-[#f0f4fc] border-t border-border-soft mt-auto py-12 px-4 md:px-8">
      <div className="max-w-6xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-12">
          <div className="md:col-span-1">
            <Link href="/" className="font-display text-xl font-bold tracking-tight text-ink mb-2 block">
              RoleCraft
            </Link>
            <p className="text-sm text-ink-muted leading-relaxed">
              The future of smarter, AI-tailored career fitment.
            </p>
          </div>
          
          <div>
            <h4 className="font-semibold text-ink mb-4 text-sm uppercase tracking-wider">Product</h4>
            <div className="flex flex-col gap-3">
              <Link href="/#features" className="text-sm text-ink-muted hover:text-brand-blue transition-colors">Features</Link>
              <Link href="/pricing" className="text-sm text-ink-muted hover:text-brand-blue transition-colors">Pricing</Link>
              <Link href="/#companies" className="text-sm text-ink-muted hover:text-brand-blue transition-colors">For Companies</Link>
            </div>
          </div>
          
          <div>
            <h4 className="font-semibold text-ink mb-4 text-sm uppercase tracking-wider">Company</h4>
            <div className="flex flex-col gap-3">
              <Link href="#" className="text-sm text-ink-muted hover:text-brand-blue transition-colors">About</Link>
              <Link href="#" className="text-sm text-ink-muted hover:text-brand-blue transition-colors">Contact</Link>
            </div>
          </div>
          
          <div>
            <h4 className="font-semibold text-ink mb-4 text-sm uppercase tracking-wider">Legal</h4>
            <div className="flex flex-col gap-3">
              <Link href="/terms" className="text-sm text-ink-muted hover:text-brand-blue transition-colors">Terms of Service</Link>
              <Link href="/privacy" className="text-sm text-ink-muted hover:text-brand-blue transition-colors">Privacy Policy</Link>
            </div>
          </div>
        </div>
        
        <div className="pt-8 border-t border-border-soft flex flex-col md:flex-row justify-between items-center gap-4">
          <span className="text-sm text-ink-muted">© 2026 RoleCraft Inc. All rights reserved.</span>
          <div className="flex items-center gap-5">
            <a href="#" className="text-ink-muted hover:text-brand-blue transition-colors"><MessageSquare className="w-5 h-5" /></a>
            <a href="#" className="text-ink-muted hover:text-brand-blue transition-colors"><Mail className="w-5 h-5" /></a>
            <a href="#" className="text-ink-muted hover:text-brand-blue transition-colors"><Globe className="w-5 h-5" /></a>
          </div>
        </div>
      </div>
    </footer>
  );
}
