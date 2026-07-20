import React from 'react';
import { Check } from 'lucide-react';

interface StepProgressProps {
  steps: string[];
  currentStep: number;
}

export function StepProgress({ steps, currentStep }: StepProgressProps) {
  return (
    <div className="w-full">
      <div className="flex items-center justify-between">
        {steps.map((step, index) => {
          const isCompleted = index < currentStep;
          const isCurrent = index === currentStep;

          return (
            <div key={index} className="flex flex-col items-center relative z-10">
              <div
                className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold border-2 transition-colors ${
                  isCompleted
                    ? 'bg-primary border-primary text-white'
                    : isCurrent
                    ? 'bg-white border-primary text-primary'
                    : 'bg-white border-slate-200 text-slate-400'
                }`}
              >
                {isCompleted ? <Check className="w-5 h-5" /> : index + 1}
              </div>
              <span
                className={`mt-2 text-xs font-medium text-center max-w-[80px] ${
                  isCurrent || isCompleted ? 'text-slate-900' : 'text-slate-400'
                }`}
              >
                {step}
              </span>
            </div>
          );
        })}
      </div>
      {/* Background track line */}
      <div className="relative -mt-[52px] mb-[32px] w-[calc(100%-40px)] mx-auto">
        <div className="h-1 bg-slate-200 w-full absolute top-1/2 transform -translate-y-1/2 -z-10 rounded-full">
          <div
            className="h-1 bg-primary absolute left-0 top-0 rounded-full transition-all duration-300"
            style={{ width: `${(currentStep / (steps.length - 1)) * 100}%` }}
          />
        </div>
      </div>
    </div>
  );
}
