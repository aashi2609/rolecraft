import React from 'react';
import { cn } from './FitmentRing';
import { AIBadge } from './AIBadge';

type MatchRationaleProps = {
  candidateSkills: string[];
  jobSkills: string[];
  rationaleText: string;
  className?: string;
};

export function MatchRationale({ candidateSkills, jobSkills, rationaleText, className }: MatchRationaleProps) {
  const overlap = candidateSkills.filter(skill => jobSkills.includes(skill));

  return (
    <div className={cn('flex flex-col gap-4 p-4 rounded-xl border border-gray-200 bg-white', className)}>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <h4 className="text-sm font-semibold text-gray-700 mb-2 font-display">Job Requires</h4>
          <div className="flex flex-wrap gap-2">
            {jobSkills.map(skill => {
              const isMatch = overlap.includes(skill);
              return (
                <span 
                  key={`job-${skill}`}
                  className={cn(
                    'px-2.5 py-1 text-xs rounded-md font-medium border transition-colors',
                    isMatch 
                      ? 'bg-blue-600 text-white border-blue-600' 
                      : 'bg-white text-blue-600 border-blue-200'
                  )}
                >
                  {skill}
                </span>
              );
            })}
          </div>
        </div>

        <div>
          <h4 className="text-sm font-semibold text-gray-700 mb-2 font-display">Your Skills</h4>
          <div className="flex flex-wrap gap-2">
            {candidateSkills.map(skill => {
              const isMatch = overlap.includes(skill);
              return (
                <span 
                  key={`cand-${skill}`}
                  className={cn(
                    'px-2.5 py-1 text-xs rounded-md font-medium border transition-colors',
                    isMatch 
                      ? 'bg-blue-600 text-white border-blue-600' 
                      : 'bg-white text-gray-600 border-gray-200'
                  )}
                >
                  {skill}
                </span>
              );
            })}
          </div>
        </div>
      </div>

      <div className="mt-2 p-3 bg-blue-50/50 rounded-lg flex items-start text-sm text-gray-700">
        <span className="flex-1">{rationaleText}</span>
        <AIBadge tooltipText="AI-generated match explanation" className="ml-3 shrink-0 mt-0.5" />
      </div>
    </div>
  );
}
