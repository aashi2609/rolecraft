"use client";

import React from 'react';
import Link from 'next/link';
import { Briefcase } from 'lucide-react';
import { useUser } from '@/context/UserContext';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

export default function ApplicationsPage() {
  const { applications } = useUser();

  return (
    <div className="py-8 px-4 md:px-8 max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl md:text-3xl font-bold text-foreground">Applications</h1>
        <p className="text-muted-foreground text-sm mt-1">Track roles you&apos;ve applied to.</p>
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
          {applications.map((app) => (
            <Card key={app.id} className="p-5 flex items-center justify-between gap-4">
              <div>
                <h3 className="font-bold text-foreground">{app.jobTitle}</h3>
                <p className="text-sm text-muted-foreground mt-0.5">{app.companyName}</p>
                <p className="text-xs text-muted-foreground mt-1">Applied {app.date}</p>
              </div>
              <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-primary/10 text-primary">
                {app.status}
              </span>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
