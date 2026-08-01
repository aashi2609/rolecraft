import React from 'react';
import { cn } from './FitmentRing';

export type StepStatus = 'Applied' | 'Reviewed' | 'Shortlisted' | 'Interview' | 'Decision';
const STATUS_ORDER: StepStatus[] = ['Applied', 'Reviewed', 'Shortlisted', 'Interview', 'Decision'];

type StatusStepperProps = {
  currentStatus: StepStatus;
  isRejected?: boolean;
  compact?: boolean;
  className?: string;
};

export function StatusStepper({ currentStatus, isRejected = false, compact = false, className }: StatusStepperProps) {
  const currentIndex = STATUS_ORDER.indexOf(currentStatus);

  return (
    <div className={cn('flex items-center w-full', className)}>
      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes pulse-ring {
          0% { box-shadow: 0 0 0 0 rgba(37, 99, 235, 0.4); }
          70% { box-shadow: 0 0 0 8px rgba(37, 99, 235, 0); }
          100% { box-shadow: 0 0 0 0 rgba(37, 99, 235, 0); }
        }
        .stepper-current {
          animation: pulse-ring 2s infinite;
        }
      `}} />
      
      {STATUS_ORDER.map((step, index) => {
        const isCompleted = index < currentIndex;
        const isCurrent = index === currentIndex;
        const isFuture = index > currentIndex;
        
        let circleClasses = 'w-4 h-4 rounded-full border-2 transition-colors';
        let textClasses = 'text-sm font-medium mt-2 transition-colors';
        
        if (isRejected && (isCurrent || isFuture)) {
          circleClasses = cn(circleClasses, 'border-red-400 bg-red-50', isCurrent && 'bg-red-500 border-red-500');
          textClasses = cn(textClasses, 'text-red-400', isCurrent && 'text-red-600 font-bold');
        } else if (isCompleted) {
          circleClasses = cn(circleClasses, 'border-blue-600 bg-blue-600');
          textClasses = cn(textClasses, 'text-blue-600');
        } else if (isCurrent) {
          circleClasses = cn(circleClasses, 'border-blue-600 bg-blue-600 stepper-current');
          textClasses = cn(textClasses, 'text-blue-700 font-bold');
        } else {
          circleClasses = cn(circleClasses, 'border-gray-300 bg-white');
          textClasses = cn(textClasses, 'text-gray-400');
        }

        return (
          <React.Fragment key={step}>
            <div className={cn('flex flex-col items-center relative', compact ? 'w-4' : 'flex-1')}>
              <div className={cn('flex items-center justify-center z-10 bg-white', compact ? '' : 'w-full')}>
                <div className={circleClasses} />
              </div>
              {!compact && (
                <span className={textClasses}>{step}</span>
              )}
            </div>
            
            {/* Connector Line */}
            {index < STATUS_ORDER.length - 1 && (
              <div 
                className={cn(
                  'h-[2px] flex-1 -ml-2 -mr-2 z-0 transition-colors',
                  isCompleted && !isRejected ? 'bg-blue-600' : 'bg-gray-200',
                  (isRejected && index >= currentIndex) ? 'bg-gray-200' : ''
                )}
                style={{ marginTop: compact ? 0 : '-28px' }}
              />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}
