import React from 'react';
import { CheckCircle2, Clock, Briefcase } from 'lucide-react';
import { cn } from './FitmentRing';

type TrustBadgeType = 'verified' | 'response_time' | 'open_roles';

type TrustBadgeProps = {
  type: TrustBadgeType;
  value?: string | number;
  className?: string;
};

export function TrustBadge({ type, value, className }: TrustBadgeProps) {
  const badgeConfig = {
    verified: {
      icon: CheckCircle2,
      label: 'Verified Company',
      iconClass: 'text-green-600',
    },
    response_time: {
      icon: Clock,
      label: `Usually responds in ${value || '~2 days'}`,
      iconClass: 'text-blue-600',
    },
    open_roles: {
      icon: Briefcase,
      label: `${value || 0} Open Roles`,
      iconClass: 'text-blue-600',
    }
  };

  const config = badgeConfig[type];
  const Icon = config.icon;

  return (
    <div className={cn('inline-flex items-center px-2.5 py-1 rounded-full bg-slate-100 text-slate-700 text-xs font-medium', className)}>
      <Icon className={cn("w-3.5 h-3.5 mr-1.5", config.iconClass)} />
      {config.label}
    </div>
  );
}

export function TrustBadgeGroup({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={cn('flex flex-wrap items-center gap-2', className)}>
      {children}
    </div>
  );
}
