"use client";

import React, { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { applicationsApi, jobsApi } from '@/lib/api';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { ArrowLeft, Inbox, Clock, CheckCircle2, XCircle, Users } from 'lucide-react';
import Link from 'next/link';

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
  const s = status ? status.charAt(0).toUpperCase() + status.slice(1) : 'Applied';
  const config = STATUS_CONFIG[s] ?? {
    label: s,
    className: 'bg-primary/10 text-primary',
    icon: <Clock className="w-3 h-3" />,
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full ${config.className}`}
    >
      {config.icon}
      {config.label}
    </span>
  );
}

export default function JobApplicationsPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params.id as string;

  const [job, setJob] = useState<any>(null);
  const [applications, setApplications] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [jobData, appsData] = await Promise.all([
          jobsApi.get(jobId),
          applicationsApi.forJob(jobId),
        ]);
        setJob(jobData);
        setApplications(appsData);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [jobId]);

  const updateStatus = async (appId: string, status: string) => {
    try {
      await applicationsApi.setStatus(appId, status);
      setApplications(applications.map(a => 
        a.id === appId ? { ...a, status } : a
      ));
    } catch (err) {
      console.error(err);
    }
  };

  if (loading) {
    return <div className="py-8 px-4 text-center">Loading applications...</div>;
  }

  return (
    <div className="py-8 px-4 md:px-8 max-w-5xl mx-auto">
      <div className="mb-6 flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => router.back()}>
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold text-foreground">
            Applications for {job?.title || 'Job'}
          </h1>
          <p className="text-muted-foreground text-sm">
            Review and update the status of candidates who applied.
          </p>
        </div>
      </div>

      {applications.length === 0 ? (
        <Card className="text-center py-16">
          <Inbox className="w-12 h-12 text-muted-foreground/30 mx-auto mb-4" />
          <h3 className="text-lg font-bold text-foreground mb-2">No applications yet</h3>
          <p className="text-muted-foreground text-sm">
            Candidates haven't applied to this job yet.
          </p>
        </Card>
      ) : (
        <div className="space-y-4">
          {applications.map((app) => (
            <Card key={app.id} className="p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-3">
                  <h3 className="font-bold text-foreground text-lg">{app.candidate_name || 'Candidate'}</h3>
                  <StatusBadge status={app.status} />
                </div>
                <p className="text-sm text-muted-foreground mt-1">
                  Applied on {new Date(app.applied_at).toLocaleDateString()}
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Button size="sm" variant="outline" onClick={() => updateStatus(app.id, 'shortlisted')}>
                  Shortlist
                </Button>
                <Button size="sm" variant="outline" onClick={() => updateStatus(app.id, 'interview')}>
                  Interview
                </Button>
                <Button size="sm" variant="outline" onClick={() => updateStatus(app.id, 'rejected')} className="text-red-600 hover:text-red-700">
                  Reject
                </Button>
                <Link href={`/company/candidates`}>
                  <Button size="sm">View Profile</Button>
                </Link>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
