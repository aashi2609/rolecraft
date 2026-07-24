"use client";

import React from 'react';
import Link from 'next/link';
import { Logo } from '@/components/Logo';
import { useUser } from '@/context/UserContext';

export function Footer() {
  const { isAuthenticated } = useUser();
  if (isAuthenticated) return null;

  return (
    <footer className="bg-white border-t border-border mt-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex flex-col md:flex-row justify-between items-center gap-4">
          <div className="flex items-center gap-4">
            <Logo showWordmark markClassName="h-7 w-7" wordmarkClassName="text-base" />
            <span className="text-sm text-muted-foreground">© 2026 RoleCraft Inc.</span>
          </div>
          <div className="flex gap-6">
            <Link href="/terms" className="text-sm text-muted-foreground hover:text-primary">
              Terms of Service
            </Link>
            <Link href="/privacy" className="text-sm text-muted-foreground hover:text-primary">
              Privacy Policy
            </Link>
            <Link href="/pricing" className="text-sm text-muted-foreground hover:text-primary">
              Pricing
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
