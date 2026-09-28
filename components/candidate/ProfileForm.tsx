"use client";

import React, { useCallback, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/Button';
import { FormField, Input, Textarea } from '@/components/ui/FormField';
import { TagInput } from '@/components/ui/TagInput';
import { candidateApi } from '@/lib/api';
import { useUser } from '@/context/UserContext';
import { useToast } from '@/components/ui/Toast';
import {
  EducationSection,
  CertificationsSection,
  ExperienceSection,
  ProjectsSection,
  SkillsSection
} from './ProfileSections';

interface CandidateProfile {
  dob?: string;
  gender?: string;
  marital_status?: string;
  present_address?: string;
  permanent_address?: string;
  preferred_locations?: string[];
  preferred_sectors?: string[];
  strengths?: string[];
  weaknesses?: string[];
  annual_family_income?: string;
  weblinks?: Record<string, string>;
  skills?: string[];
  education?: any[];
  certifications?: any[];
  experience?: any[];
  projects?: any[];
}

export default function ProfileForm() {
  const router = useRouter();
  const { candidateProfile, refreshSession, resumes } = useUser();
  const { showToast } = useToast();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [formData, setFormData] = useState({
    full_name: '',
    dob: '',
    gender: '',
    marital_status: '',
    present_address: '',
    permanent_address: '',
    sameAddress: false,
    preferred_locations: [] as string[],
    preferred_sectors: [] as string[],
    strengths: [] as string[],
    weaknesses: [] as string[],
    annual_family_income: '',
    weblinks: {} as Record<string, string>,
    family: [] as Record<string, string>[],
    skills: [] as string[],
    education: [] as any[],
    certifications: [] as any[],
    experience: [] as any[],
    projects: [] as any[],
    hobbies: [] as string[],
    extra: ''
  });

  const updateFormData = useCallback(() => {
    const p = (candidateProfile as CandidateProfile) || {};
    const links = p.weblinks || {};
    setFormData((prev) => ({
      ...prev,
      full_name: links.display_name || links.full_name || '',
      dob: p.dob ? String(p.dob).slice(0, 10) : '',
      gender: p.gender || '',
      marital_status: p.marital_status || '',
      present_address: p.present_address || '',
      permanent_address: p.permanent_address || '',
      preferred_locations: p.preferred_locations || [],
      preferred_sectors: p.preferred_sectors || [],
      strengths: p.strengths || [],
      weaknesses: p.weaknesses || [],
      annual_family_income: p.annual_family_income || '',
      weblinks: links,
      skills: p.skills || [],
      education: p.education || [],
      certifications: p.certifications || [],
      experience: p.experience || [],
      projects: p.projects || [],
    }));
  }, [candidateProfile]);

  useEffect(() => {
    updateFormData();
  }, [updateFormData]);

  const updateForm = (key: string, value: unknown) => {
    setFormData((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = async () => {
    setSaving(true);
    setError('');
    try {
      // 1. Update Personal Details (Scalars)
      const payload: Record<string, unknown> = {
        full_name: formData.full_name || null,
        dob: formData.dob || null,
        gender: formData.gender || null,
        marital_status: formData.marital_status || null,
        present_address: formData.present_address || null,
        permanent_address: formData.sameAddress
          ? formData.present_address
          : formData.permanent_address || null,
        preferred_locations: formData.preferred_locations,
        preferred_sectors: formData.preferred_sectors,
        strengths: formData.strengths,
        weaknesses: formData.weaknesses,
        annual_family_income: formData.annual_family_income || null,
        weblinks: formData.weblinks,
      };
      await candidateApi.updateMe(payload);
      
      // 2. Update Skills
      if (formData.skills) {
        await candidateApi.putSkills(formData.skills);
      }

      const p = (candidateProfile as CandidateProfile) || {};

      // Helper function to sync arrays
      const syncArray = async (
        oldArr: any[] = [], 
        newArr: any[] = [], 
        addFn: (data: any) => Promise<any>, 
        updateFn: (id: string, data: any) => Promise<any>, 
        deleteFn: (id: string) => Promise<any>
      ) => {
        const oldIds = new Set(oldArr.map(i => i.id));
        const newIds = new Set(newArr.filter(i => i.id).map(i => i.id));

        // Delete missing ids
        for (const id of oldIds) {
          if (!newIds.has(id)) {
            await deleteFn(id);
          }
        }
        // Add or Update
        for (const item of newArr) {
          if (item.id) {
            await updateFn(item.id, item);
          } else {
            await addFn(item);
          }
        }
      };

      // 3. Sync Education
      await syncArray(
        p.education, formData.education,
        candidateApi.addEducation.bind(candidateApi),
        candidateApi.updateEducation.bind(candidateApi),
        candidateApi.deleteEducation.bind(candidateApi)
      );

      // 4. Sync Certifications
      await syncArray(
        p.certifications, formData.certifications,
        candidateApi.addCertification.bind(candidateApi),
        candidateApi.updateCertification.bind(candidateApi),
        candidateApi.deleteCertification.bind(candidateApi)
      );

      // 5. Sync Experience
      await syncArray(
        p.experience, formData.experience,
        candidateApi.addExperience.bind(candidateApi),
        candidateApi.updateExperience.bind(candidateApi),
        candidateApi.deleteExperience.bind(candidateApi)
      );

      // 6. Sync Projects
      await syncArray(
        p.projects, formData.projects,
        candidateApi.addProject.bind(candidateApi),
        candidateApi.updateProject.bind(candidateApi),
        candidateApi.deleteProject.bind(candidateApi)
      );

      await refreshSession();
      if (resumes && resumes.length > 0) {
        showToast('warning', 'Profile updated. Your generated resumes are now out of date. Please regenerate them to include these changes.', 8000);
      } else {
        showToast('success', 'Profile saved successfully.');
      }
      router.push('/dashboard');
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to save profile');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto py-10 px-4">
      <div className="bg-white rounded-xl shadow-sm border border-border-soft p-8 space-y-8">
        {error && (
          <div className="rounded-lg bg-red-50 text-red-700 px-4 py-3 text-sm">{error}</div>
        )}

        <section>
          <h2 className="text-xl font-bold text-ink border-b pb-2 mb-4">Basic Information</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FormField label="Full Name" required>
              <Input placeholder="Enter your full name" value={formData.full_name} onChange={(e) => updateForm('full_name', e.target.value)} />
            </FormField>
            <FormField label="Date of Birth" required>
              <Input type="date" value={formData.dob} onChange={(e) => updateForm('dob', e.target.value)} />
            </FormField>
            <FormField label="Gender" required>
              <select className="flex h-10 w-full rounded-md border border-border-soft bg-transparent px-3 py-2 text-sm text-ink placeholder:text-ink-muted focus:outline-none focus:ring-1 focus:ring-brand" value={formData.gender} onChange={(e) => updateForm('gender', e.target.value)}>
                <option value="">Select Gender</option>
                <option value="Male">Male</option>
                <option value="Female">Female</option>
                <option value="Other">Other</option>
                <option value="Prefer not to say">Prefer not to say</option>
              </select>
            </FormField>
            <FormField label="Marital Status">
              <select className="flex h-10 w-full rounded-md border border-border-soft bg-transparent px-3 py-2 text-sm text-ink placeholder:text-ink-muted focus:outline-none focus:ring-1 focus:ring-brand" value={formData.marital_status} onChange={(e) => updateForm('marital_status', e.target.value)}>
                <option value="">Select Status</option>
                <option value="Single">Single</option>
                <option value="Married">Married</option>
              </select>
            </FormField>
          </div>
        </section>

        <section>
          <h2 className="text-xl font-bold text-ink border-b pb-2 mb-4">Address Details</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FormField label="Present Address" required>
              <Textarea placeholder="Current residential address" value={formData.present_address} onChange={(e) => updateForm('present_address', e.target.value)} />
            </FormField>
            <FormField label="Permanent Address">
              <div className="flex flex-col gap-2">
                <Textarea placeholder="Permanent residential address" disabled={formData.sameAddress} value={formData.sameAddress ? formData.present_address : formData.permanent_address} onChange={(e) => updateForm('permanent_address', e.target.value)} />
                <label className="flex items-center gap-2 text-sm text-ink-muted">
                  <input type="checkbox" checked={formData.sameAddress} onChange={(e) => updateForm('sameAddress', e.target.checked)} />
                  Same as present address
                </label>
              </div>
            </FormField>
          </div>
        </section>

        <section>
          <h2 className="text-xl font-bold text-ink border-b pb-2 mb-4">Preferences & Profile</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FormField label="Preferred Locations">
              <TagInput tags={formData.preferred_locations} onChange={(tags) => updateForm('preferred_locations', tags)} placeholder="Press enter to add location" />
            </FormField>
            <FormField label="Preferred Sectors">
              <TagInput tags={formData.preferred_sectors} onChange={(tags) => updateForm('preferred_sectors', tags)} placeholder="Press enter to add sector" />
            </FormField>
            <FormField label="Key Strengths">
              <TagInput tags={formData.strengths} onChange={(tags) => updateForm('strengths', tags)} placeholder="Press enter to add strength" />
            </FormField>
            <FormField label="Key Weaknesses">
              <TagInput tags={formData.weaknesses} onChange={(tags) => updateForm('weaknesses', tags)} placeholder="Press enter to add weakness" />
            </FormField>
            <FormField label="Annual Family Income">
              <select className="flex h-10 w-full rounded-md border border-border-soft bg-transparent px-3 py-2 text-sm text-ink placeholder:text-ink-muted focus:outline-none focus:ring-1 focus:ring-brand" value={formData.annual_family_income} onChange={(e) => updateForm('annual_family_income', e.target.value)}>
                <option value="">Select Range</option>
                <option value="< 3 Lakhs">Less than 3 Lakhs</option>
                <option value="3-5 Lakhs">3 - 5 Lakhs</option>
                <option value="5-10 Lakhs">5 - 10 Lakhs</option>
                <option value="10+ Lakhs">Above 10 Lakhs</option>
              </select>
            </FormField>
          </div>
        </section>

        <section>
          <EducationSection items={formData.education} onChange={(items) => updateForm('education', items)} />
        </section>
        
        <section>
          <ExperienceSection items={formData.experience} onChange={(items) => updateForm('experience', items)} />
        </section>

        <section>
          <CertificationsSection items={formData.certifications} onChange={(items) => updateForm('certifications', items)} />
        </section>
        
        <section>
          <SkillsSection skills={formData.skills} onChange={(skills) => updateForm('skills', skills)} />
        </section>

        <section>
          <ProjectsSection items={formData.projects} onChange={(items) => updateForm('projects', items)} />
        </section>

        <div className="mt-8 pt-6 border-t border-border-soft flex items-center justify-end">
          <Button variant="primary" onClick={handleSave} disabled={saving} className="px-8">
            {saving ? 'Saving...' : 'Save Profile'}
          </Button>
        </div>
      </div>
    </div>
  );
}
