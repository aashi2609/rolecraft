"use client";

import React, { useEffect, useState } from 'react';
import { useUser } from '@/context/UserContext';
import { useParams, useRouter } from 'next/navigation';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Bookmark, BookmarkCheck, MapPin, Briefcase, IndianRupee, Clock, TrendingUp, X } from 'lucide-react';
import Link from 'next/link';
import { jobsApi } from '@/lib/api';

function mapJobFromApi(j: any) {
  return {
    id: j.id,
    companyId: j.company_id,
    companyName: j.company_name,
    title: j.title,
    vertical: j.department,
    department: j.department,
    location: j.location,
    employmentType: j.employment_type,
    jobType: j.job_type
      ? String(j.job_type).charAt(0).toUpperCase() + String(j.job_type).slice(1)
      : undefined,
    salaryMin: j.min_salary != null ? String(j.min_salary) : '',
    salaryMax: j.max_salary != null ? String(j.max_salary) : '',
    salaryUnit: j.salary_unit || 'Per annum',
    experience: j.experience_range,
    skills: j.required_skills || [],
    description: j.description,
    responsibilities: j.responsibilities,
    requirements: j.requirements,
    benefits: j.benefits,
    status: j.status ? String(j.status).charAt(0).toUpperCase() + String(j.status).slice(1) : 'Draft',
  };
}

export default function JobDetailPage() {
  const { jobId } = useParams();
  const { jobs, savedJobs, toggleSavedJob, applications, applyToJob, resumes } = useUser();
  const router = useRouter();
  const [job, setJob] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [isApplyModalOpen, setIsApplyModalOpen] = useState(false);

  useEffect(() => {
    const id = String(jobId);
    const cached = jobs.find((j) => String(j.id) === id);
    if (cached) {
      setJob(cached);
      setLoading(false);
      return;
    }
    jobsApi
      .get(id)
      .then((raw) => setJob(mapJobFromApi(raw)))
      .catch(() => setJob(null))
      .finally(() => setLoading(false));
  }, [jobId, jobs]);

  if (loading) {
    return <div className="min-h-[80vh] flex items-center justify-center text-ink-muted">Loading job…</div>;
  }

  if (!job) {
    return <div className="min-h-[80vh] flex items-center justify-center text-ink-muted">Job not found.</div>;
  }

  const isSaved = savedJobs.includes(String(job.id));
  const hasApplied = applications.some((a) => String(a.jobId) === String(job.id));
  const bestResume = resumes.find((r) => r.vertical === job.vertical) || resumes[0];

  const handleApplyClick = () => {
    if (resumes.length === 0) {
      router.push('/onboarding/generate?redirect=/jobs/' + job.id);
    } else {
      setIsApplyModalOpen(true);
    }
  };

  const confirmApply = async () => {
    try {
      await applyToJob({
        jobId: job.id,
        jobTitle: job.title,
        companyName: job.companyName,
        status: 'Applied',
        appliedAt: new Date().toISOString(),
        resumeId: bestResume?.id,
      });
    } catch {
      alert('You have already applied for this job.');
    }
    setIsApplyModalOpen(false);
  };

  return (
    <div className="min-h-screen bg-surface-soft py-10">
      <div className="max-w-4xl mx-auto px-4">
        <Link href="/jobs" className="text-sm text-ink-muted hover:text-primary mb-6 inline-block">
          ← Back to Jobs
        </Link>

        <Card className="p-8 mb-6">
          <div className="flex flex-col md:flex-row justify-between gap-4 mb-6">
            <div>
              <h1 className="text-3xl font-bold text-ink mb-2">{job.title}</h1>
              <p className="text-lg text-ink-muted font-medium">{job.companyName}</p>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => toggleSavedJob(job.id)} className="gap-2">
                {isSaved ? <BookmarkCheck className="w-4 h-4" /> : <Bookmark className="w-4 h-4" />}
                {isSaved ? 'Saved' : 'Save'}
              </Button>
              {!hasApplied ? (
                <Button onClick={handleApplyClick}>Apply Now</Button>
              ) : (
                <Button variant="outline" disabled>Applied</Button>
              )}
            </div>
          </div>

          <div className="flex flex-wrap gap-4 text-sm text-ink-muted mb-6">
            {job.location && (
              <span className="flex items-center gap-1"><MapPin className="w-4 h-4" /> {job.location}</span>
            )}
            {job.employmentType && (
              <span className="flex items-center gap-1"><Briefcase className="w-4 h-4" /> {job.employmentType}</span>
            )}
            {job.experience && (
              <span className="flex items-center gap-1"><Clock className="w-4 h-4" /> {job.experience}</span>
            )}
            {(job.salaryMin || job.salaryMax) && (
              <span className="flex items-center gap-1">
                <IndianRupee className="w-4 h-4" />
                {job.salaryMin && job.salaryMax
                  ? `${job.salaryMin} – ${job.salaryMax} ${job.salaryUnit || ''}`
                  : job.salaryMin || job.salaryMax}
              </span>
            )}
          </div>

          {job.description && (
            <div className="mb-6">
              <h2 className="font-bold text-ink mb-2">About the role</h2>
              <p className="text-ink-muted whitespace-pre-wrap">{job.description}</p>
            </div>
          )}

          {job.responsibilities && (
            <div className="mb-6">
              <h2 className="font-bold text-ink mb-2">Responsibilities</h2>
              <p className="text-ink-muted whitespace-pre-wrap">{job.responsibilities}</p>
            </div>
          )}

          {job.requirements && (
            <div className="mb-6">
              <h2 className="font-bold text-ink mb-2">Requirements</h2>
              <p className="text-ink-muted whitespace-pre-wrap">{job.requirements}</p>
            </div>
          )}

          {job.skills?.length > 0 && (
            <div>
              <h2 className="font-bold text-ink mb-2">Required skills</h2>
              <div className="flex flex-wrap gap-2">
                {job.skills.map((s: string) => (
                  <span key={s} className="px-2 py-1 bg-secondary rounded-md text-xs font-medium">{s}</span>
                ))}
              </div>
            </div>
          )}
        </Card>
      </div>

      {isApplyModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
          <Card className="max-w-md w-full p-6 relative">
            <button className="absolute top-4 right-4" onClick={() => setIsApplyModalOpen(false)}>
              <X className="w-5 h-5 text-ink-muted" />
            </button>
            <h3 className="text-xl font-bold text-ink mb-2">Confirm Application</h3>
            <p className="text-ink-muted text-sm mb-4">
              Apply to <strong>{job.title}</strong> at {job.companyName}?
            </p>
            {bestResume && (
              <p className="text-sm mb-4 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-primary" />
                Using resume: {bestResume.vertical} ({bestResume.score || '—'}/100)
              </p>
            )}
            <div className="flex gap-3">
              <Button variant="outline" onClick={() => setIsApplyModalOpen(false)}>Cancel</Button>
              <Button onClick={confirmApply}>Submit Application</Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
