"use client";

import React from 'react';
import Link from 'next/link';
import { Inbox } from 'lucide-react';
import { useUser } from '@/context/UserContext';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

/** Company-side applications inbox (mock) — distinct from candidate Applications. */
export default function CompanyApplicationsPage() {
  const { jobs } = useUser();
  const totalMatched = jobs.reduce((s, j) => s + (j.matched || 0), 0);
  const totalShortlisted = jobs.reduce((s, j) => s + (j.shortlisted || 0), 0);

  return (
    <div className="py-8 px-4 md:px-8 max-w-5xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl md:text-3xl font-bold text-foreground">Applications</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Incoming applications across your live jobs.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
        <Card className="p-5">
          <p className="text-sm text-muted-foreground">Total matched</p>
          <p className="text-3xl font-bold text-foreground mt-1">{totalMatched}</p>
        </Card>
        <Card className="p-5">
          <p className="text-sm text-muted-foreground">Shortlisted</p>
          <p className="text-3xl font-bold text-foreground mt-1">{totalShortlisted}</p>
        </Card>
      </div>

      {jobs.filter((j) => j.status === 'Live').length === 0 ? (
        <Card className="text-center py-16">
          <Inbox className="w-12 h-12 text-muted-foreground/30 mx-auto mb-4" />
          <h3 className="text-lg font-bold text-foreground mb-2">No live jobs yet</h3>
          <p className="text-muted-foreground text-sm mb-6">
            Post a job to start receiving applications.
          </p>
          <Link href="/company/jobs/new">
            <Button>Post a New Job</Button>
          </Link>
        </Card>
      ) : (
        <div className="space-y-3">
          {jobs
            .filter((j) => j.status === 'Live')
            .map((job) => (
              <Card key={job.id} className="p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <h3 className="font-bold text-foreground">{job.title}</h3>
                  <p className="text-sm text-muted-foreground mt-0.5">
                    {job.matched ?? 0} matched · {job.shortlisted ?? 0} shortlisted
                  </p>
                </div>
                <Link href="/company/candidates">
                  <Button variant="outline" size="sm">
                    Review candidates
                  </Button>
                </Link>
              </Card>
            ))}
        </div>
      )}
    </div>
  );
}
