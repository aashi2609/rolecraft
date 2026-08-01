import React from 'react';
import { cn } from './FitmentRing';

type Tier = 'Getting Started' | 'Good' | 'Strong' | 'All-Star';

type StrengthMeterProps = {
  completionPercentage: number;
  nextStepTip: string;
  className?: string;
};

export function StrengthMeter({ completionPercentage, nextStepTip, className }: StrengthMeterProps) {
  let tier: Tier = 'Getting Started';
  if (completionPercentage >= 76) tier = 'All-Star';
  else if (completionPercentage >= 51) tier = 'Strong';
  else if (completionPercentage >= 26) tier = 'Good';

  return (
    <div className={cn("w-full max-w-md", className)}>
      <div className="flex justify-between items-end mb-2">
        <span className="text-sm font-semibold text-gray-700">Profile Strength: {tier}</span>
        <span className="text-xs font-medium text-gray-500">{completionPercentage}%</span>
      </div>
      
      {/* Progress Bar */}
      <div className="h-2 w-full bg-blue-100 rounded-full overflow-hidden">
        <div 
          className="h-full bg-blue-600 transition-all duration-700 ease-out"
          style={{ width: `${completionPercentage}%` }}
        />
      </div>

      {/* Dynamic Tip */}
      {completionPercentage < 100 && (
        <div className="mt-3 text-sm text-gray-600 bg-slate-50 p-2.5 rounded border border-slate-100 flex items-start">
          <span className="text-blue-600 mr-2 mt-0.5">💡</span>
          <span>{nextStepTip}</span>
        </div>
      )}
    </div>
  );
}
