"use client";

import React from 'react';
import Link from 'next/link';
import { Briefcase, Clock, CheckCircle2, XCircle, Users } from 'lucide-react';
import { useUser } from '@/context/UserContext';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

/** Map application status strings to styled badge configurations. */
const STATUS_CONFIG: Record<string, { label: string; className: string; icon: React.ReactNode }> = {
  Applied: {
    label: 'Applied',
    className: 'bg-blue-500/10 text-blue-600',
    icon: <Clock className="w-3 h-3" />,
  },
  Shortlisted: {
    label: 'Shortlisted',
    className: 'bg-emerald-500/10 text-emerald-600',
    icon: <CheckCircle2 className="w-3 h-3" />,
  },
  Interview: {
    label: 'Interview',
    className: 'bg-amber-500/10 text-amber-600',
    icon: <Users className="w-3 h-3" />,
  },
  Rejected: {
    label: 'Rejected',
    className: 'bg-red-500/10 text-red-600',
    icon: <XCircle className="w-3 h-3" />,
  },
};

function StatusBadge({ status }: { status: string }) {
  const config = STATUS_CONFIG[status] ?? {
    label: status,
    className: 'bg-primary/10 text-primary',
    icon: <Clock className="w-3 h-3" />,
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full transition-all duration-300 ${config.className}`}
    >
      {config.icon}
      {config.label}
    </span>
  );
}

export default function ApplicationsPage() {
  const { applications } = useUser();

  return (
    <div className="py-8 px-4 md:px-8 max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl md:text-3xl font-bold text-foreground">Applications</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Track roles you&apos;ve applied to. Statuses update in real-time.
        </p>
      </div>

      {applications.length === 0 ? (
        <Card className="text-center py-16">
          <Briefcase className="w-12 h-12 text-muted-foreground/30 mx-auto mb-4" />
          <h3 className="text-lg font-bold text-foreground mb-2">No applications yet</h3>
          <p className="text-muted-foreground text-sm mb-6">Browse jobs and apply to get started.</p>
          <Link href="/jobs">
            <Button>Search Jobs</Button>
          </Link>
        </Card>
      ) : (
        <div className="space-y-3">
          {applications.map((app: Record<string, any>) => (
            <Card key={app.id} className="p-5 flex items-center justify-between gap-4">
              <div>
                <h3 className="font-bold text-foreground">{app.jobTitle}</h3>
                <p className="text-sm text-muted-foreground mt-0.5">{app.companyName}</p>
                <p className="text-xs text-muted-foreground mt-1">Applied {app.date}</p>
              </div>
              <StatusBadge status={app.status} />
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
