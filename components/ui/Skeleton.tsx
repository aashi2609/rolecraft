import React from 'react';
import { cn } from './FitmentRing';

type SkeletonProps = {
  className?: string;
};

export function Skeleton({ className }: SkeletonProps) {
  return (
    <div 
      className={cn(
        "animate-pulse bg-slate-200 rounded-md relative overflow-hidden",
        className
      )}
    >
      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes shimmer {
          100% {
            transform: translateX(100%);
          }
        }
        .shimmer-effect::after {
          position: absolute;
          top: 0;
          right: 0;
          bottom: 0;
          left: 0;
          transform: translateX(-100%);
          background-image: linear-gradient(90deg, rgba(255, 255, 255, 0) 0, rgba(255, 255, 255, 0.4) 20%, rgba(255, 255, 255, 0.7) 60%, rgba(255, 255, 255, 0));
          animation: shimmer 1.5s infinite;
          content: '';
        }
      `}} />
      <div className="shimmer-effect absolute inset-0 z-10" />
    </div>
  );
}

export function SkeletonCircle({ className }: SkeletonProps) {
  return <Skeleton className={cn("rounded-full", className)} />;
}

export function SkeletonText({ lines = 1, className }: { lines?: number; className?: string }) {
  return (
    <div className={cn("space-y-2", className)}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton 
          key={i} 
          className={cn(
            "h-4", 
            i === lines - 1 && lines > 1 ? "w-[80%]" : "w-full"
          )} 
        />
      ))}
    </div>
  );
}
