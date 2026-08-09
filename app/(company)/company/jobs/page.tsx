"use client";

import React, { useState } from 'react';
import Link from 'next/link';
import { useUser } from '@/context/UserContext';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Briefcase, Plus, MoreVertical, Users, Bookmark } from 'lucide-react';

export default function MyJobsPage() {
  const { jobs, updateJob } = useUser();
  const [menuOpen, setMenuOpen] = useState<number | null>(null);

  // Show company-owned + seeded jobs for demo
  const myJobs = jobs;

  const closeJob = async (id: number | string) => {
    const job = jobs.find((j) => String(j.id) === String(id));
    if (job) {
      try {
        const { jobsApi } = await import('@/lib/api');
        await jobsApi.setStatus(String(id), 'closed');
      } catch {
        /* offline */
      }
      updateJob({ ...job, status: 'Closed' });
    }
    setMenuOpen(null);
  };

  return (
    <div className="py-8 px-4 md:px-8 max-w-6xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-foreground">My Jobs</h1>
          <p className="text-muted-foreground mt-1 text-sm">
            Manage postings, matches, and shortlists.
          </p>
        </div>
        <Link href="/company/jobs/new">
          <Button className="gap-2">
            <Plus className="h-4 w-4" /> Post a New Job
          </Button>
        </Link>
      </div>

      {myJobs.length === 0 ? (
        <Card className="text-center py-16">
          <Briefcase className="w-12 h-12 text-muted-foreground/40 mx-auto mb-4" />
          <h3 className="text-lg font-bold mb-2">No jobs yet</h3>
          <p className="text-muted-foreground text-sm mb-6">Post your first role to start matching candidates.</p>
          <Link href="/company/jobs/new">
            <Button>Post a New Job</Button>
          </Link>
        </Card>
      ) : (
        <div className="space-y-4">
          {myJobs.map((job) => (
            <Card key={job.id} className="p-5 flex flex-col md:flex-row md:items-center gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <h3 className="font-bold text-foreground text-lg">{job.title}</h3>
                  <span
                    className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                      job.status === 'Live'
                        ? 'bg-green-100 text-green-700'
                        : job.status === 'Draft'
                          ? 'bg-amber-100 text-amber-700'
                          : 'bg-secondary text-muted-foreground'
                    }`}
                  >
                    {job.status}
                  </span>
                </div>
                <p className="text-sm text-muted-foreground mt-1">
                  {job.department || job.vertical} · {job.location} · Posted {job.date}
                </p>
              </div>

              <div className="flex items-center gap-6 text-sm">
                <div className="flex items-center gap-1.5 text-muted-foreground">
                  <Users className="h-4 w-4" />
                  <span className="font-semibold text-foreground">{job.matched ?? 0}</span> matched
                </div>
                <div className="flex items-center gap-1.5 text-muted-foreground">
                  <Bookmark className="h-4 w-4" />
                  <span className="font-semibold text-foreground">{job.shortlisted ?? 0}</span> shortlisted
                </div>
              </div>

              <div className="relative flex items-center gap-2">
                <Link href={`/company/jobs/${job.id}/applications`}>
                  <Button variant="outline" size="sm">
                    View Candidates
                  </Button>
                </Link>
                <button
                  type="button"
                  className="h-9 w-9 inline-flex items-center justify-center rounded-lg border border-border hover:bg-secondary"
                  onClick={() => setMenuOpen(menuOpen === job.id ? null : job.id)}
                >
                  <MoreVertical className="h-4 w-4" />
                </button>
                {menuOpen === job.id && (
                  <>
                    <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(null)} />
                    <div className="absolute right-0 top-10 z-20 w-40 rounded-lg border border-border bg-white shadow-md py-1">
                      <Link
                        href="/company/jobs/new"
                        className="block px-3 py-2 text-sm hover:bg-secondary"
                        onClick={() => setMenuOpen(null)}
                      >
                        Edit
                      </Link>
                      <button
                        type="button"
                        className="w-full text-left px-3 py-2 text-sm text-red-600 hover:bg-red-50"
                        onClick={() => closeJob(job.id)}
                      >
                        Close Job
                      </button>
                    </div>
                  </>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
