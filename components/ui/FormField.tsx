import React from 'react';
import { cn } from '@/lib/utils';

interface FormFieldProps {
  label: string;
  required?: boolean;
  children: React.ReactNode;
  error?: string;
  className?: string;
}

export function FormField({ label, required, children, error, className = '' }: FormFieldProps) {
  return (
    <div className={cn('flex flex-col space-y-1.5', className)}>
      <label className="text-caption text-ink font-semibold">
        {label}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>
      {children}
      {error && <span className="text-xs text-red-500 mt-1">{error}</span>}
    </div>
  );
}

export function Input({ className, ...props }: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        'px-3 py-2 bg-surface-white border border-border-soft rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-brand-blue focus:border-transparent transition-shadow w-full text-ink text-[15px] placeholder:text-ink-muted',
        className
      )}
      {...props}
    />
  );
}

export function Textarea({ className, ...props }: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cn(
        'px-3 py-2 bg-surface-white border border-border-soft rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-brand-blue focus:border-transparent transition-shadow w-full text-ink text-[15px] placeholder:text-ink-muted min-h-[100px] resize-y',
        className
      )}
      {...props}
    />
  );
}
