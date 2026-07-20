import React from 'react';

interface FormFieldProps {
  label: string;
  required?: boolean;
  children: React.ReactNode;
  error?: string;
  className?: string;
}

export function FormField({ label, required, children, error, className = '' }: FormFieldProps) {
  return (
    <div className={`flex flex-col space-y-1.5 ${className}`}>
      <label className="text-sm font-semibold text-slate-800">
        {label}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>
      {children}
      {error && <span className="text-xs text-red-500 mt-1">{error}</span>}
    </div>
  );
}

// Reusable styled input components
export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input 
      className="px-3 py-2 bg-white border border-slate-200 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-shadow w-full text-slate-900 placeholder:text-slate-400"
      {...props} 
    />
  );
}

export function Textarea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea 
      className="px-3 py-2 bg-white border border-slate-200 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-shadow w-full text-slate-900 placeholder:text-slate-400 min-h-[100px] resize-y"
      {...props} 
    />
  );
}
