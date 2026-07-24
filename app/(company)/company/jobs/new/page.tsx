"use client";

import React, { Suspense, useEffect, useMemo, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { FormField, Input, Textarea } from '@/components/ui/FormField';
import { SearchableCombobox } from '@/components/ui/SearchableCombobox';
import { UpsellPrompt } from '@/components/UpsellPrompt';
import { useUser } from '@/context/UserContext';
import {
  CITIES,
  DEPARTMENTS,
  EMPLOYMENT_TYPES,
  JOB_TYPES,
  SKILLS,
} from '@/lib/constants';
import { isFreePlan, maxJobPostings } from '@/lib/plans';
import { jobsApi } from '@/lib/api';

type JobDraft = {
  id: number | null;
  title: string;
  department: string;
  employmentType: string;
  experience: string;
  salaryMin: string;
  salaryMax: string;
  salaryUnit: 'Per month' | 'Per annum';
  location: string;
  jobType: string;
  skills: string[];
  openings: string;
  deadline: string;
  description: string;
  responsibilities: string;
  requirements: string;
  benefits: string;
};

const emptyDraft = (): JobDraft => ({
  id: null,
  title: '',
  department: '',
  employmentType: '',
  experience: '',
  salaryMin: '',
  salaryMax: '',
  salaryUnit: 'Per annum',
  location: '',
  jobType: 'On-site',
  skills: [],
  openings: '1',
  deadline: '',
  description: '',
  responsibilities: '',
  requirements: '',
  benefits: '',
});

function PostJobContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const editId = searchParams.get('edit');
  const { jobs, addJob, updateJob, plan } = useUser();
  const [step, setStep] = useState<1 | 2>(1);
  const [draft, setDraft] = useState<JobDraft>(emptyDraft());
  const [saving, setSaving] = useState(false);

  const activeCount = jobs.filter((j) => j.status === 'Live' || j.status === 'Draft').length;
  const atCap = !editId && isFreePlan(plan) && activeCount >= maxJobPostings(plan);

  useEffect(() => {
    if (!editId) return;
    const existing = jobs.find((j) => String(j.id) === editId);
    if (!existing) return;
    setDraft({
      id: existing.id,
      title: existing.title || '',
      department: existing.department || existing.vertical || '',
      employmentType: existing.employmentType || '',
      experience: existing.experience || '',
      salaryMin: existing.salaryMin || '',
      salaryMax: existing.salaryMax || '',
      salaryUnit: existing.salaryUnit || 'Per annum',
      location: existing.location || '',
      jobType: existing.jobType || 'On-site',
      skills: existing.skills || [],
      openings: String(existing.openings ?? 1),
      deadline: existing.deadline || '',
      description: existing.description || '',
      responsibilities: existing.responsibilities || '',
      requirements: existing.requirements || '',
      benefits: existing.benefits || '',
    });
  }, [editId, jobs]);

  const step1Valid = useMemo(() => {
    return Boolean(
      draft.title &&
        draft.department &&
        draft.employmentType &&
        draft.experience &&
        draft.location &&
        draft.jobType &&
        draft.skills.length > 0 &&
        draft.openings
    );
  }, [draft]);

  const setField = <K extends keyof JobDraft>(key: K, value: JobDraft[K]) => {
    setDraft((prev) => ({ ...prev, [key]: value }));
  };

  const persist = async (status: 'Live' | 'Draft') => {
    if (atCap && status === 'Live') return;
    setSaving(true);
    const apiBody = {
      title: draft.title,
      department: draft.department,
      employment_type: draft.employmentType,
      experience_range: draft.experience,
      min_salary: draft.salaryMin ? Number(draft.salaryMin) : undefined,
      max_salary: draft.salaryMax ? Number(draft.salaryMax) : undefined,
      salary_unit: draft.salaryUnit,
      location: draft.location,
      job_type: draft.jobType?.toLowerCase(),
      required_skills: draft.skills,
      num_openings: Number(draft.openings) || 1,
      application_deadline: draft.deadline || undefined,
      description: draft.description,
      responsibilities: draft.responsibilities,
      requirements: draft.requirements,
      benefits: draft.benefits,
      status: status.toLowerCase(),
    };

    try {
      if (draft.id) {
        const updated = await jobsApi.update(String(draft.id), apiBody);
        if (status !== (jobs.find((j) => String(j.id) === String(draft.id))?.status || '')) {
          await jobsApi.setStatus(String(draft.id), status.toLowerCase());
        }
        updateJob({
          id: updated.id,
          title: updated.title,
          department: updated.department,
          status: status,
        });
      } else {
        const created = await jobsApi.create(apiBody);
        addJob({
          id: created.id,
          title: created.title,
          department: created.department,
          location: created.location,
          employmentType: created.employment_type,
          status: status,
          matched: 0,
          shortlisted: 0,
          date: created.created_at?.slice?.(0, 10),
          skills: created.required_skills || [],
        });
      }
      router.push('/company/jobs');
    } catch {
      // Fallback local persist if API offline
      const payload = {
        id: draft.id ?? Date.now(),
        title: draft.title,
        department: draft.department,
        location: draft.location,
        employmentType: draft.employmentType,
        status,
        matched: 0,
        shortlisted: 0,
        date: new Date().toISOString().split('T')[0],
        skills: draft.skills,
      };
      if (draft.id) updateJob(payload);
      else addJob(payload);
      router.push('/company/jobs');
    } finally {
      setSaving(false);
    }
  };

  if (atCap) {
    return (
      <div className="py-8 px-4 md:px-8 max-w-3xl mx-auto">
        <UpsellPrompt
          title="You've reached your free posting limit"
          description="Upgrade your plan to post unlimited jobs and unlock full candidate search filters."
        />
        <Link href="/company/jobs" className="inline-block mt-6">
          <Button variant="outline">Back to My Jobs</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="py-8 px-4 md:px-8 max-w-3xl mx-auto">
      <Link
        href="/company/jobs"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-primary mb-6"
      >
        <ArrowLeft className="w-4 h-4" /> Back to My Jobs
      </Link>

      <div className="mb-8">
        <h1 className="text-2xl md:text-3xl font-bold text-foreground">
          {editId ? 'Edit Job' : 'Post a New Job'}
        </h1>
        <p className="text-muted-foreground text-sm mt-1">
          Step {step} of 2 — {step === 1 ? 'Job Details' : 'Job Description'}
        </p>
        <div className="mt-4 flex gap-2">
          <div className={`h-1.5 flex-1 rounded-full ${step >= 1 ? 'bg-primary' : 'bg-secondary'}`} />
          <div className={`h-1.5 flex-1 rounded-full ${step >= 2 ? 'bg-primary' : 'bg-secondary'}`} />
        </div>
      </div>

      {step === 1 && (
        <Card className="space-y-5">
          <h2 className="text-lg font-bold text-foreground">Job Details</h2>

          <FormField label="Job Title" required>
            <Input
              placeholder="e.g. Senior UI/UX Designer"
              value={draft.title}
              onChange={(e) => setField('title', e.target.value)}
            />
          </FormField>

          <FormField label="Department" required>
            <SearchableCombobox
              options={[...DEPARTMENTS]}
              value={draft.department}
              onChange={(v) => setField('department', v)}
              placeholder="Select department"
            />
          </FormField>

          <FormField label="Employment Type" required>
            <select
              className="w-full px-3 py-2 bg-white border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary text-foreground"
              value={draft.employmentType}
              onChange={(e) => setField('employmentType', e.target.value)}
            >
              <option value="">Select type</option>
              {EMPLOYMENT_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </FormField>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <FormField label="Experience Required" required>
              <Input
                placeholder="e.g. 3-5 Years"
                value={draft.experience}
                onChange={(e) => setField('experience', e.target.value)}
              />
            </FormField>
            <FormField label="Min Salary">
              <div className="relative">
                <span className="absolute left-3 top-2.5 text-muted-foreground text-sm">₹</span>
                <Input
                  className="pl-7"
                  type="number"
                  placeholder="Min"
                  value={draft.salaryMin}
                  onChange={(e) => setField('salaryMin', e.target.value)}
                />
              </div>
            </FormField>
            <FormField label="Max Salary">
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <span className="absolute left-3 top-2.5 text-muted-foreground text-sm">₹</span>
                  <Input
                    className="pl-7"
                    type="number"
                    placeholder="Max"
                    value={draft.salaryMax}
                    onChange={(e) => setField('salaryMax', e.target.value)}
                  />
                </div>
                <select
                  className="w-[110px] px-2 py-2 bg-white border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                  value={draft.salaryUnit}
                  onChange={(e) => setField('salaryUnit', e.target.value as JobDraft['salaryUnit'])}
                >
                  <option value="Per month">Per month</option>
                  <option value="Per annum">Per annum</option>
                </select>
              </div>
            </FormField>
          </div>

          <FormField label="Location" required>
            <SearchableCombobox
              options={[...CITIES]}
              value={draft.location}
              onChange={(v) => setField('location', v)}
              placeholder="e.g. Bangalore, Karnataka"
            />
          </FormField>

          <FormField label="Job Type" required>
            <div className="flex flex-wrap gap-3">
              {JOB_TYPES.map((t) => (
                <label
                  key={t}
                  className={`inline-flex items-center gap-2 px-4 py-2.5 rounded-lg border cursor-pointer transition-colors ${
                    draft.jobType === t
                      ? 'border-primary bg-primary/5 text-primary'
                      : 'border-border hover:border-primary/40'
                  }`}
                >
                  <input
                    type="radio"
                    name="jobType"
                    className="accent-primary"
                    checked={draft.jobType === t}
                    onChange={() => setField('jobType', t)}
                  />
                  <span className="text-sm font-medium">{t}</span>
                </label>
              ))}
            </div>
          </FormField>

          <FormField label="Required Skills" required>
            <SearchableCombobox
              multiSelect
              options={[...SKILLS]}
              value={draft.skills}
              onChange={(v) => setField('skills', v)}
              placeholder="e.g. Figma, UI Design, Prototyping"
            />
          </FormField>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FormField label="Number of Openings" required>
              <Input
                type="number"
                min={1}
                value={draft.openings}
                onChange={(e) => setField('openings', e.target.value)}
              />
            </FormField>
            <FormField label="Application Deadline">
              <Input
                type="date"
                value={draft.deadline}
                onChange={(e) => setField('deadline', e.target.value)}
              />
            </FormField>
          </div>

          <div className="flex flex-col-reverse sm:flex-row justify-between gap-3 pt-4 border-t border-border">
            <Button
              variant="outline"
              disabled={saving || !draft.title}
              onClick={() => persist('Draft')}
            >
              Save Draft
            </Button>
            <Button disabled={!step1Valid} onClick={() => setStep(2)} className="gap-2">
              Next: Job Description <ArrowRight className="w-4 h-4" />
            </Button>
          </div>
        </Card>
      )}

      {step === 2 && (
        <Card className="space-y-5">
          <h2 className="text-lg font-bold text-foreground">Job Description</h2>

          <FormField label="Full Description" required>
            <Textarea
              rows={5}
              placeholder="Summarize the role, team, and impact..."
              value={draft.description}
              onChange={(e) => setField('description', e.target.value)}
            />
          </FormField>

          <FormField label="Responsibilities">
            <Textarea
              rows={4}
              placeholder="One responsibility per line"
              value={draft.responsibilities}
              onChange={(e) => setField('responsibilities', e.target.value)}
            />
          </FormField>

          <FormField label="Requirements">
            <Textarea
              rows={4}
              placeholder="Must-haves and nice-to-haves"
              value={draft.requirements}
              onChange={(e) => setField('requirements', e.target.value)}
            />
          </FormField>

          <FormField label="Benefits">
            <Textarea
              rows={3}
              placeholder="Perks, benefits, and culture highlights"
              value={draft.benefits}
              onChange={(e) => setField('benefits', e.target.value)}
            />
          </FormField>

          <div className="flex flex-col-reverse sm:flex-row justify-between gap-3 pt-4 border-t border-border">
            <Button variant="outline" onClick={() => setStep(1)}>
              Back
            </Button>
            <div className="flex gap-2">
              <Button variant="outline" disabled={saving} onClick={() => persist('Draft')}>
                Save Draft
              </Button>
              <Button
                disabled={saving || !draft.description}
                onClick={() => persist('Live')}
              >
                {saving ? 'Posting...' : 'Post Job'}
              </Button>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}

export default function PostJobPage() {
  return (
    <Suspense fallback={<div className="p-8">Loading...</div>}>
      <PostJobContent />
    </Suspense>
  );
}
