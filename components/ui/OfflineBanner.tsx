'use client';

import { useOffline } from '@/hooks/useOffline';
import { cn } from './FitmentRing';

export function OfflineBanner() {
  const isOffline = useOffline();

  if (!isOffline) return null;

  return (
    <div className={cn(
      "fixed top-0 left-0 right-0 bg-amber-500 text-white px-4 py-2 text-center z-50",
      "flex items-center justify-center gap-2"
    )}>
      <span className="font-medium">⚠️ You are offline</span>
      <span className="text-sm opacity-90">Some features may not be available</span>
    </div>
  );
}
