"use client";

import React, { useState } from 'react';
import { useUser } from '@/context/UserContext';
import { useParams, useRouter } from 'next/navigation';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Bookmark, BookmarkCheck, MapPin, Briefcase, IndianRupee, Clock, TrendingUp, X } from 'lucide-react';
import Link from 'next/link';

export default function JobDetailPage() {
  const { jobId } = useParams();
  const { jobs, savedJobs, toggleSavedJob, applications, applyToJob, resumes } = useUser();
  const router = useRouter();
  
  const [isApplyModalOpen, setIsApplyModalOpen] = useState(false);

  const job = jobs.find(j => j.id === Number(jobId));
  if (!job) {
    return <div className="min-h-[80vh] flex items-center justify-center text-ink-muted">Job not found.</div>;
  }

  const isSaved = savedJobs.includes(job.id);
  const hasApplied = applications.some(a => a.jobId === job.id);
  const bestResume = resumes.find(r => r.vertical === job.vertical) || resumes[0]; // mock best resume match

  // Mock fitment score for demonstration
  const mockFitment = '92%';

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
        appliedAt: new Date().toISOString()
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

        {/* Header Card */}
        <Card className="p-8 mb-8 relative overflow-hidden">
          <div className="flex flex-col md:flex-row gap-6 items-start justify-between">
            <div className="flex gap-6">
              <div className="w-20 h-20 bg-surface-soft rounded-xl flex items-center justify-center text-3xl font-bold text-ink-muted shrink-0">
                {job.companyName.charAt(0)}
              </div>
              <div>
                <h1 className="text-3xl font-bold text-ink mb-2">{job.title}</h1>
                <Link href={`/companies/${job.companyId}`} className="text-lg text-primary hover:underline font-medium block mb-4">
                  {job.companyName}
                </Link>
                
                <div className="flex flex-wrap gap-4 text-sm text-ink-muted mb-6">
                  <div className="flex items-center gap-1"><MapPin className="w-4 h-4" /> {job.location}</div>
                  <div className="flex items-center gap-1"><Briefcase className="w-4 h-4" /> {job.employmentType}</div>
                  <div className="flex items-center gap-1"><Clock className="w-4 h-4" /> {job.experience}</div>
                  {!job.salaryUndisclosed && job.salaryMin && (
                    <div className="flex items-center gap-1"><IndianRupee className="w-4 h-4" /> {job.salaryMin} - {job.salaryMax}</div>
                  )}
                </div>
              </div>
            </div>
            
            <div className="flex flex-col items-end gap-3 shrink-0">
              <span className="inline-flex items-center justify-center px-3 py-1.5 text-sm font-bold rounded-full bg-green-100 text-green-700">
                <TrendingUp className="w-4 h-4 mr-1" /> AI Match: {mockFitment}
              </span>
              <div className="flex gap-3 mt-4">
                <button 
                  className="p-3 text-ink-muted hover:text-primary border border-border-soft rounded-lg hover:border-primary transition-colors bg-white"
                  onClick={() => toggleSavedJob(job.id)}
                >
                  {isSaved ? <BookmarkCheck className="w-5 h-5 text-primary" /> : <Bookmark className="w-5 h-5" />}
                </button>
                <Button size="lg" onClick={handleApplyClick} disabled={hasApplied} className="min-w-[150px]">
                  {hasApplied ? 'Applied ✓' : 'Apply Now'}
                </Button>
              </div>
            </div>
          </div>
        </Card>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Left Column (Job Details) */}
          <div className="md:col-span-2 space-y-8">
            <Card className="p-8">
              <h2 className="text-xl font-bold text-ink mb-4">About the Role</h2>
              <div className="prose text-ink-muted max-w-none">
                <p className="whitespace-pre-line">{job.description}</p>
              </div>
            </Card>

            <Card className="p-8">
              <h2 className="text-xl font-bold text-ink mb-4">About {job.companyName}</h2>
              <div className="text-ink-muted mb-4">
                A leading company in the industry, focused on building innovative solutions and fostering a culture of continuous learning.
              </div>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div><span className="font-medium text-ink">Industry:</span> Technology / IT Services</div>
                <div><span className="font-medium text-ink">Company Size:</span> 51-200</div>
              </div>
              <div className="mt-6">
                <Link href={`/companies/${job.companyId}`}>
                  <Button variant="outline">View Full Profile</Button>
                </Link>
              </div>
            </Card>
          </div>

          {/* Right Column (Skills & Meta) */}
          <div className="space-y-8">
            <Card className="p-6">
              <h3 className="font-bold text-ink mb-4">Required Skills</h3>
              <div className="flex flex-wrap gap-2">
                {job.skills.map((skill: string) => (
                  <span key={skill} className="bg-surface-soft text-ink px-3 py-1.5 rounded-md text-sm font-medium">
                    {skill}
                  </span>
                ))}
              </div>
            </Card>

            <Card className="p-6">
              <h3 className="font-bold text-ink mb-4">Job Info</h3>
              <ul className="space-y-4 text-sm">
                <li>
                  <div className="text-ink-muted mb-1">Posted Date</div>
                  <div className="font-medium text-ink">{job.date}</div>
                </li>
                <li>
                  <div className="text-ink-muted mb-1">Vertical</div>
                  <div className="font-medium text-ink">{job.vertical}</div>
                </li>
              </ul>
            </Card>
          </div>
        </div>

      </div>

      {/* Apply Modal */}
      {isApplyModalOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-ink/50 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-md overflow-hidden flex flex-col p-6">
            <div className="flex justify-between items-center mb-6">
              <h3 className="font-bold text-ink text-xl">Review Application</h3>
              <button onClick={() => setIsApplyModalOpen(false)} className="text-ink-muted hover:text-ink-muted">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <p className="text-ink-muted mb-6">
              You are about to apply for <span className="font-bold text-ink">{job.title}</span> at <span className="font-bold text-ink">{job.companyName}</span>.
            </p>

            <div className="bg-surface-soft p-4 rounded-lg border border-border-soft mb-6">
              <div className="text-xs text-ink-muted mb-2 uppercase font-bold tracking-wide">Resume Attached</div>
              <div className="flex justify-between items-center">
                <div className="font-medium text-ink">{bestResume ? `${bestResume.vertical} Profile` : 'Default Profile'}</div>
                <Link href="/resumes" className="text-sm text-primary hover:underline">Change</Link>
              </div>
            </div>

            <Button size="lg" className="w-full" onClick={confirmApply}>
              Confirm & Apply
            </Button>
          </div>
        </div>
      )}

    </div>
  );
}
