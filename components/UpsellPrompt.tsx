"use client";

import Link from 'next/link';
import { AlertCircle, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { useUser } from '@/context/UserContext';

interface UpsellPromptProps {
  title: string;
  description: string;
  className?: string;
  compact?: boolean;
}

export function UpsellPrompt({ title, description, className = '', compact = false }: UpsellPromptProps) {
  const { role } = useUser();
  const href = `/subscribe?role=${role === 'company' ? 'company' : 'candidate'}`;

  if (compact) {
    return (
      <div className={`rounded-xl border border-primary/20 bg-primary/5 p-4 flex flex-col sm:flex-row sm:items-center gap-3 ${className}`}>
        <div className="flex items-start gap-3 flex-1">
          <Sparkles className="h-5 w-5 text-primary shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-foreground">{title}</p>
            <p className="text-xs text-muted-foreground mt-0.5">{description}</p>
          </div>
        </div>
        <Link href={href}>
          <Button size="sm" className="whitespace-nowrap">Upgrade plan</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className={`rounded-xl border border-amber-200 bg-amber-50 p-4 flex items-start gap-3 ${className}`}>
      <AlertCircle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
      <div className="flex-1">
        <h4 className="font-semibold text-amber-900">{title}</h4>
        <p className="text-sm text-amber-800 mt-1">{description}</p>
        <Link href={href} className="inline-block mt-3">
          <Button size="sm">View plans</Button>
        </Link>
      </div>
    </div>
  );
}
