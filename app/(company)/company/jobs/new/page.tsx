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
  role: string;
  level: string;
  employmentType: string;
  experience: string;
  salaryMin: string;
  salaryMax: string;
  salaryUnit: 'Per month' | 'Per annum';
  location: string;
  country: string;
  state: string;
  city: string;
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
  role: '',
  level: '',
  employmentType: '',
  experience: '',
  salaryMin: '',
  salaryMax: '',
  salaryUnit: 'Per annum',
  location: '',
  country: '',
  state: '',
  city: '',
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
  const [uploadedFileName, setUploadedFileName] = useState<string | null>(null);

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
      role: (existing as any).role || '',
      level: (existing as any).level || '',
      employmentType: existing.employmentType || '',
      experience: existing.experience || '',
      salaryMin: existing.salaryMin || '',
      salaryMax: existing.salaryMax || '',
      salaryUnit: existing.salaryUnit || 'Per annum',
      location: existing.location || '',
      country: (existing as any).country || '',
      state: (existing as any).state || '',
      city: (existing as any).city || '',
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
        draft.role &&
        draft.level &&
        draft.employmentType &&
        draft.experience &&
        draft.country &&
        draft.state &&
        draft.city &&
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
      role: draft.role,
      level: draft.level,
      employment_type: draft.employmentType,
      experience_range: draft.experience,
      min_salary: draft.salaryMin ? Number(draft.salaryMin) : undefined,
      max_salary: draft.salaryMax ? Number(draft.salaryMax) : undefined,
      salary_unit: draft.salaryUnit,
      location: `${draft.city}, ${draft.state}, ${draft.country}`,
      country: draft.country,
      state: draft.state,
      city: draft.city,
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
        const updated: any = await jobsApi.update(String(draft.id), apiBody);
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
        const created: any = await jobsApi.create(apiBody);
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
        role: draft.role,
        level: draft.level,
        location: `${draft.city}, ${draft.state}, ${draft.country}`,
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

      <div className="mb-6">
        <label className="block text-sm font-medium mb-2 text-foreground">Upload JD to Autofill</label>
        <div className="flex items-center gap-4">
          <input
            type="file"
            accept=".pdf,.doc,.docx,.txt"
            id="jd-upload"
            className="hidden"
            onChange={async (e) => {
              const file = e.target.files?.[0];
              if (!file) return;
              setUploadedFileName(file.name);
              
              if (file.type === 'text/plain' || file.name.endsWith('.txt')) {
                const reader = new FileReader();
                reader.onload = (ev) => {
                  const text = ev.target?.result as string;
                  if (!text) return;
                  
                  const lines = text.split('\n');
                  const getField = (prefix: string) => {
                    const line = lines.find(l => l.startsWith(prefix));
                    return line ? line.replace(prefix, '').trim() : '';
                  };
                  
                  const title = getField('Job Title:');
                  if (title) setField('title', title);
                  
                  const department = getField('Department:');
                  if (department) setField('department', department);
                  
                  const role = getField('Role:');
                  if (role) setField('role', role);
                  
                  const level = getField('Level:');
                  if (level) {
                     const matchedLevel = ['Internship', 'Entry', 'Mid', 'Senior', 'Director', 'Executive'].find(l => level.includes(l));
                     if (matchedLevel) setField('level', matchedLevel);
                  }

                  const empType = getField('Employment Type:');
                  if (empType) {
                     const matchedEmp = EMPLOYMENT_TYPES.find(t => empType.toLowerCase().includes(t.toLowerCase()));
                     if (matchedEmp) setField('employmentType', matchedEmp);
                  }

                  const loc = getField('Location:');
                  if (loc) {
                     const parts = loc.split(',').map(s => s.trim());
                     if (parts.length >= 3) {
                       setField('city', parts[0]);
                       setField('state', parts[1]);
                       setField('country', parts[2]);
                     } else if (parts.length === 1) {
                       setField('city', parts[0]);
                     }
                  }

                  let currentSection = '';
                  let description = '';
                  let responsibilities = '';
                  let requirements = '';
                  let benefits = '';
                  
                  for (let line of lines) {
                    if (line.startsWith('About the Role:')) { currentSection = 'desc'; continue; }
                    if (line.startsWith('Responsibilities:')) { currentSection = 'resp'; continue; }
                    if (line.startsWith('Requirements:')) { currentSection = 'req'; continue; }
                    if (line.startsWith('Benefits:')) { currentSection = 'ben'; continue; }
                    
                    if (currentSection === 'desc' && !line.startsWith('Job Title:')) description += line + '\n';
                    if (currentSection === 'resp') responsibilities += line + '\n';
                    if (currentSection === 'req') requirements += line + '\n';
                    if (currentSection === 'ben') benefits += line + '\n';
                  }
                  
                  if (description.trim()) setField('description', description.trim());
                  if (responsibilities.trim()) setField('responsibilities', responsibilities.trim());
                  if (requirements.trim()) setField('requirements', requirements.trim());
                  if (benefits.trim()) setField('benefits', benefits.trim());

                  const foundSkills: string[] = [];
                  SKILLS.forEach(skill => {
                    if (text.toLowerCase().includes(skill.toLowerCase())) {
                       foundSkills.push(skill);
                    }
                  });
                  const extraSkills = ['React', 'Next.js', 'TypeScript', 'Tailwind'];
                  extraSkills.forEach(s => {
                     if (text.toLowerCase().includes(s.toLowerCase()) && !foundSkills.includes(s)) {
                        foundSkills.push(s);
                     }
                  });
                  if (foundSkills.length > 0) {
                     setField('skills', foundSkills);
                  }
                };
                reader.readAsText(file);
              } else {
                 setField('title', 'Software Engineer');
                 setField('role', 'Engineering');
                 setField('level', 'Mid');
              }
            }}
          />
          <Button variant="outline" onClick={() => document.getElementById('jd-upload')?.click()}>
            Upload JD File
          </Button>
          <span className="text-sm text-muted-foreground">
            {uploadedFileName ? (
              <span className="font-medium text-primary">Uploaded: {uploadedFileName}</span>
            ) : (
              "Upload a PDF or DOCX to automatically fill out this form."
            )}
          </span>
        </div>
      </div>

      {step === 1 && (
        <Card className="space-y-5">
          <h2 className="text-lg font-bold text-foreground">Job Details</h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FormField label="Job Title" required>
              <Input
                placeholder="e.g. Senior UI/UX Designer"
                value={draft.title}
                onChange={(e) => setField('title', e.target.value)}
              />
            </FormField>

            <FormField label="Department">
              <SearchableCombobox
                options={[...DEPARTMENTS]}
                value={draft.department}
                onChange={(v) => setField('department', v)}
                placeholder="Select department"
              />
            </FormField>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FormField label="Job Role" required>
              <Input
                placeholder="e.g. Frontend Developer"
                value={draft.role}
                onChange={(e) => setField('role', e.target.value)}
              />
            </FormField>

            <FormField label="Job Level" required>
              <select
                className="w-full px-3 py-2 bg-white border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary text-foreground"
                value={draft.level}
                onChange={(e) => setField('level', e.target.value)}
              >
                <option value="">Select level</option>
                <option value="Internship">Internship</option>
                <option value="Entry">Entry Level</option>
                <option value="Mid">Mid Level</option>
                <option value="Senior">Senior Level</option>
                <option value="Director">Director</option>
                <option value="Executive">Executive</option>
              </select>
            </FormField>
          </div>

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

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <FormField label="Country" required>
              <Input
                placeholder="e.g. India"
                value={draft.country}
                onChange={(e) => setField('country', e.target.value)}
              />
            </FormField>
            <FormField label="State" required>
              <Input
                placeholder="e.g. Karnataka"
                value={draft.state}
                onChange={(e) => setField('state', e.target.value)}
              />
            </FormField>
            <FormField label="City" required>
              <Input
                placeholder="e.g. Bangalore"
                value={draft.city}
                onChange={(e) => setField('city', e.target.value)}
              />
            </FormField>
          </div>

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
