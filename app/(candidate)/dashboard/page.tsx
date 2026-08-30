"use client";

import React, { useEffect, useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { ArrowRight, Sparkles, FileText, CheckCircle2, Briefcase, Bookmark, MessageSquare } from 'lucide-react';
import Link from 'next/link';
import { useUser } from '@/context/UserContext';
import { isFreePlan } from '@/lib/plans';
import { UpsellPrompt } from '@/components/UpsellPrompt';
import { computeProfileCompleteness, getDisplayName } from '@/lib/profile';

export default function CandidateDashboardPage() {
  const [verticals, setVerticals] = useState<string[]>([]);
  const { applications, savedJobs, messages, jobs, resumes, plan, candidateProfile } = useUser();
  const displayName = getDisplayName(candidateProfile);
  const completeness = computeProfileCompleteness(candidateProfile);

  useEffect(() => {
    const multi = localStorage.getItem('rolecraft_target_verticals');
    if (multi) {
      try {
        setVerticals(JSON.parse(multi));
        return;
      } catch {
        /* ignore */
      }
    }
    const stored = localStorage.getItem('rolecraft_target_vertical');
    if (stored) setVerticals([stored]);
    else if (resumes.length) setVerticals(resumes.map((r) => r.vertical).filter(Boolean));
  }, [resumes]);

  return (
    <div className="py-8 px-4 md:px-8 max-w-6xl mx-auto space-y-8">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-foreground">
            {displayName ? `Welcome back, ${displayName.split(' ')[0]}` : 'Welcome back'}
          </h1>
          <p className="text-muted-foreground mt-1 text-sm">
            Here&apos;s what&apos;s happening with your job search today.
          </p>
        </div>
        <Link href="/profile/personal-details">
          <Button variant="outline">Edit Profile</Button>
        </Link>
      </div>

      {isFreePlan(plan) && (
        <UpsellPrompt
          compact
          title="Unlock multi-vertical resumes"
          description="Premium lets you generate tailored resumes for multiple target roles at once, with full job search filters."
        />
      )}

      <Card className="bg-white p-0 overflow-hidden">
        {verticals.length > 0 || resumes.length > 0 ? (
          <div className="p-8">
            <h2 className="text-xl font-bold text-foreground mb-2">Your Resumes</h2>
            <p className="text-muted-foreground mb-6 text-sm">
              Targeting:{' '}
              <span className="font-semibold text-primary">
                {(verticals.length ? verticals : resumes.map((r) => r.vertical)).join(' · ')}
              </span>
            </p>

            <div className="flex flex-wrap gap-4">
              {(resumes.length ? resumes : verticals.map((v) => ({ vertical: v, score: null, id: v }))).map(
                (r: any) => (
                  <div
                    key={r.id || r.vertical}
                    className="flex items-center gap-4 p-4 border border-border rounded-lg bg-secondary/40"
                  >
                    <div className="p-3 bg-white rounded-md shadow-sm border border-border">
                      <FileText className="w-7 h-7 text-primary" />
                    </div>
                    <div>
                      <div className="font-semibold text-foreground text-sm">
                        {r.vertical} Resume
                      </div>
                      {r.score != null && (
                        <div className="flex items-center gap-1.5 text-sm text-green-700 font-medium mt-1">
                          <CheckCircle2 className="w-4 h-4" />
                          {r.score}/100 — ATS Ready
                        </div>
                      )}
                    </div>
                  </div>
                )
              )}
            </div>

            <div className="mt-8 flex flex-wrap gap-3">
              <Link href="/jobs">
                <Button variant="primary">Apply to Jobs</Button>
              </Link>
              <Link href="/resumes">
                <Button variant="outline">Manage Resumes</Button>
              </Link>
            </div>
          </div>
        ) : (
          <div className="flex flex-col md:flex-row">
            <div className="p-8 md:p-12 flex-1 flex flex-col justify-center">
              <div className="inline-flex items-center gap-2 px-3 py-1 bg-primary/10 text-primary text-sm font-bold rounded-full w-fit mb-4">
                <Sparkles className="w-4 h-4" /> Profile Completeness: {completeness}%
              </div>
              <h2 className="text-2xl font-bold text-foreground mb-4">
                Stand out to top employers
              </h2>
              <p className="text-muted-foreground mb-8 max-w-md text-sm">
                Complete your profile and generate tailored resumes for the verticals you&apos;re targeting.
              </p>
              <Link href="/onboarding/generate">
                <Button variant="primary" className="w-fit">
                  Generate Resumes <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              </Link>
            </div>
            <div className="bg-primary/5 hidden md:flex items-center justify-center p-12 w-1/3">
              <div className="w-40 h-40 rounded-full bg-primary/10 border-8 border-white shadow-sm" />
            </div>
          </div>
        )}
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <Card className="p-6">
          <h3 className="font-bold text-foreground mb-4 flex items-center justify-between">
            Recent Applications
            <Link href="/jobs" className="text-xs text-primary hover:underline font-normal">
              Browse Jobs
            </Link>
          </h3>
          {applications.length === 0 ? (
            <div className="text-center py-8">
              <Briefcase className="w-10 h-10 text-muted-foreground/30 mx-auto mb-3" />
              <p className="text-sm text-muted-foreground font-medium">No applications yet</p>
            </div>
          ) : (
            <div className="space-y-4">
              {applications.slice(0, 3).map((app) => (
                <div key={app.id} className="border-b border-border pb-3 last:border-0">
                  <h4 className="font-bold text-foreground text-sm">{app.jobTitle}</h4>
                  <div className="flex justify-between items-center mt-1">
                    <span className="text-xs text-muted-foreground">{app.companyName}</span>
                    <span className="text-xs font-medium bg-primary/10 text-primary px-2 py-0.5 rounded-full">
                      {app.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card className="p-6">
          <h3 className="font-bold text-foreground mb-4 flex items-center justify-between">
            Saved Jobs
            <Link href="/saved-jobs" className="text-xs text-primary hover:underline font-normal">
              View All
            </Link>
          </h3>
          {savedJobs.length === 0 ? (
            <div className="text-center py-8">
              <Bookmark className="w-10 h-10 text-muted-foreground/30 mx-auto mb-3" />
              <p className="text-sm text-muted-foreground font-medium">No saved jobs</p>
            </div>
          ) : (
            <div className="space-y-4">
              {savedJobs.slice(0, 3).map((jobId) => {
                const job = jobs.find((j) => String(j.id) === String(jobId));
                if (!job) return null;
                return (
                  <div key={job.id} className="border-b border-border pb-3 last:border-0">
                    <h4 className="font-bold text-foreground text-sm line-clamp-1">{job.title}</h4>
                    <div className="flex justify-between items-center mt-1">
                      <span className="text-xs text-muted-foreground">{job.companyName}</span>
                      <Link href={`/jobs/${job.id}`} className="text-xs text-primary hover:underline">
                        Apply
                      </Link>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </Card>

        <Card className="p-6">
          <h3 className="font-bold text-foreground mb-4 flex items-center justify-between">
            Recent Messages
            <Link href="/messages" className="text-xs text-primary hover:underline font-normal">
              Open Inbox
            </Link>
          </h3>
          {messages.length === 0 ? (
            <div className="text-center py-8">
              <MessageSquare className="w-10 h-10 text-muted-foreground/30 mx-auto mb-3" />
              <p className="text-sm text-muted-foreground font-medium">No new messages</p>
            </div>
          ) : (
            <div className="space-y-4">
              {messages.slice(0, 3).map((msg: any) => (
                <div key={msg.id} className="border-b border-border pb-3 last:border-0">
                  <h4 className="font-bold text-foreground text-sm">{msg.companyName}</h4>
                  <p className="text-xs text-muted-foreground line-clamp-2 mt-1">{msg.lastMessage}</p>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
