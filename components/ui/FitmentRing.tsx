import React from 'react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

type FitmentRingProps = {
  score: number; // 0 to 100
  size?: 'small' | 'medium' | 'large';
  label?: string;
  className?: string;
};

const sizeConfig = {
  small: {
    size: 32,
    strokeWidth: 3,
    fontSize: 'text-xs',
  },
  medium: {
    size: 56,
    strokeWidth: 4,
    fontSize: 'text-base',
  },
  large: {
    size: 120,
    strokeWidth: 6,
    fontSize: 'text-3xl',
  },
};

export function FitmentRing({ score, size = 'medium', label, className }: FitmentRingProps) {
  const config = sizeConfig[size];
  const radius = (config.size - config.strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  let colorClass = 'text-gray-500';
  if (score >= 80) colorClass = 'text-green-600';
  else if (score >= 60) colorClass = 'text-amber-500';

  return (
    <div className={cn('flex flex-col items-center justify-center font-sans', className)}>
      <div
        className="relative flex items-center justify-center"
        style={{ width: config.size, height: config.size }}
      >
        {/* Background track */}
        <svg className="absolute w-full h-full transform -rotate-90">
          <circle
            cx={config.size / 2}
            cy={config.size / 2}
            r={radius}
            stroke="currentColor"
            strokeWidth={config.strokeWidth}
            fill="transparent"
            className="text-blue-100"
          />
          {/* Progress ring */}
          <circle
            cx={config.size / 2}
            cy={config.size / 2}
            r={radius}
            stroke="currentColor"
            strokeWidth={config.strokeWidth}
            fill="transparent"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            className="text-blue-600 transition-all duration-1000 ease-out"
          />
        </svg>
        <span className={cn('font-bold font-display', config.fontSize)}>
          {score}%
        </span>
      </div>
      {label && size !== 'small' && (
        <span className={cn('mt-2 text-sm font-medium', colorClass)}>
          {label}
        </span>
      )}
    </div>
  );
}
