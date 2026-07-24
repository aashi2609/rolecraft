"use client";

import React from 'react';
import Link from 'next/link';
import { Briefcase, Users, PlusCircle, TrendingUp, ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { useUser } from '@/context/UserContext';
import { planDisplayName, isFreePlan, maxJobPostings } from '@/lib/plans';

export default function CompanyDashboardPage() {
  const { jobs, plan } = useUser();
  const live = jobs.filter((j) => j.status === 'Live');
  const drafts = jobs.filter((j) => j.status === 'Draft');
  const matched = jobs.reduce((sum, j) => sum + (j.matched || 0), 0);
  const shortlisted = jobs.reduce((sum, j) => sum + (j.shortlisted || 0), 0);
  const activeCount = live.length + drafts.length;
  const remaining = isFreePlan(plan)
    ? Math.max(0, maxJobPostings(plan) - activeCount)
    : null;

  return (
    <div className="py-8 px-4 md:px-8 max-w-6xl mx-auto space-y-8">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-foreground">Employer Dashboard</h1>
          <p className="text-muted-foreground text-sm mt-1">
            You&apos;re on the <span className="font-semibold text-primary">{planDisplayName(plan)}</span> plan.
            {remaining !== null && ` ${remaining} posting${remaining === 1 ? '' : 's'} remaining.`}
          </p>
        </div>
        <Link href="/company/jobs/new">
          <Button className="gap-2">
            <PlusCircle className="w-4 h-4" /> Post a New Job
          </Button>
        </Link>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Live Jobs', value: live.length, icon: Briefcase },
          { label: 'Drafts', value: drafts.length, icon: Briefcase },
          { label: 'Matched Candidates', value: matched, icon: Users },
          { label: 'Shortlisted', value: shortlisted, icon: TrendingUp },
        ].map((stat) => (
          <Card key={stat.label} className="p-5">
            <div className="flex items-center justify-between mb-3">
              <p className="text-sm text-muted-foreground">{stat.label}</p>
              <stat.icon className="w-4 h-4 text-primary" />
            </div>
            <p className="text-3xl font-bold text-foreground">{stat.value}</p>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="p-6 flex flex-col">
          <h3 className="font-bold text-foreground mb-2">My Jobs</h3>
          <p className="text-sm text-muted-foreground flex-1 mb-4">
            View status, matches, and shortlists for every posting.
          </p>
          <Link href="/company/jobs">
            <Button variant="outline" className="w-full gap-2">
              Open My Jobs <ArrowRight className="w-4 h-4" />
            </Button>
          </Link>
        </Card>
        <Card className="p-6 flex flex-col">
          <h3 className="font-bold text-foreground mb-2">Post a Job</h3>
          <p className="text-sm text-muted-foreground flex-1 mb-4">
            Multi-step flow for details, skills, salary, and description.
          </p>
          <Link href="/company/jobs/new">
            <Button className="w-full gap-2">
              Start posting <ArrowRight className="w-4 h-4" />
            </Button>
          </Link>
        </Card>
        <Card className="p-6 flex flex-col">
          <h3 className="font-bold text-foreground mb-2">Search Candidates</h3>
          <p className="text-sm text-muted-foreground flex-1 mb-4">
            Filter the full talent pool by skills, location, salary, and more.
          </p>
          <Link href="/company/candidates">
            <Button variant="outline" className="w-full gap-2">
              Browse talent <ArrowRight className="w-4 h-4" />
            </Button>
          </Link>
        </Card>
      </div>

      <Card className="p-0 overflow-hidden">
        <div className="px-6 py-4 border-b border-border flex items-center justify-between">
          <h3 className="font-bold text-foreground">Recent postings</h3>
          <Link href="/company/jobs" className="text-sm text-primary font-medium hover:underline">
            View all
          </Link>
        </div>
        {jobs.length === 0 ? (
          <div className="p-10 text-center text-muted-foreground text-sm">No jobs yet.</div>
        ) : (
          <ul className="divide-y divide-border">
            {jobs.slice(0, 5).map((job) => (
              <li key={job.id} className="px-6 py-4 flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <p className="font-semibold text-foreground truncate">{job.title}</p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {job.status} · {job.matched ?? 0} matched · {job.shortlisted ?? 0} shortlisted
                  </p>
                </div>
                <Link href={`/company/jobs/new?edit=${job.id}`}>
                  <Button variant="ghost" size="sm">
                    Edit
                  </Button>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
