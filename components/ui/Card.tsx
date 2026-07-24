import React from 'react';
import { cn } from '@/lib/utils';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {}

export function Card({ className = '', children, ...props }: CardProps) {
  return (
    <div
      className={cn(
        'bg-surface-white rounded-xl shadow-card border border-border-soft p-6',
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
