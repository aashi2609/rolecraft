import React from 'react';
import { Sparkles } from 'lucide-react';
import { cn } from './FitmentRing';

type AIBadgeProps = {
  tooltipText: string;
  className?: string;
};

export function AIBadge({ tooltipText, className }: AIBadgeProps) {
  return (
    <div className={cn("inline-flex items-center justify-center group relative cursor-help ml-2", className)}>
      <Sparkles className="w-3.5 h-3.5 text-blue-600" />
      
      {/* Tooltip */}
      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-max px-2 py-1 bg-slate-800 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
        {tooltipText}
        <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-1 border-4 border-transparent border-t-slate-800"></div>
      </div>
    </div>
  );
}
