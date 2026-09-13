"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { StepProgress } from '@/components/ui/StepProgress';
import { StrengthMeter } from '@/components/ui/StrengthMeter';
import { Button } from '@/components/ui/Button';
import { FormField, Input, Textarea } from '@/components/ui/FormField';
import { FileDropzone } from '@/components/ui/FileDropzone';
import { TagInput } from '@/components/ui/TagInput';
import { RepeatableSection } from '@/components/ui/RepeatableSection';
import { SearchableCombobox } from '@/components/ui/SearchableCombobox';
import { useUser } from '@/context/UserContext';
import { SKILLS } from '@/lib/constants';
import { candidateApi, resumesApi } from '@/lib/api';

import {
  EducationSection,
  CertificationsSection,
  ExperienceSection,
  ProjectsSection,
  SkillsSection,
  EDU_LEVELS,
  DEGREES,
  UNIVERSITIES,
  CERT_NAMES,
  ORGS,
  TECH_SKILLS
} from './ProfileSections';

const STEPS = ['Basic', 'Education', 'Certifications', 'Experience', 'Skills'];

export default function OnboardingForm() {
  const router = useRouter();
  const { setCandidateProfile, setProfileComplete } = useUser();
  const [currentStep, setCurrentStep] = useState(0);
  const [isParsing, setIsParsing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState<any>({
    careerLevel: '',
    education: [],
    certifications: [],
    experience: [],
    skills: [],
    hobbies: [],
    languages: [],
    projects: [],
  });

  const nextStep = () => setCurrentStep((prev) => Math.min(prev + 1, STEPS.length - 1));
  const prevStep = () => setCurrentStep((prev) => Math.max(prev - 1, 0));

  const updateForm = (key: string, value: any) => {
    setFormData((prev: any) => ({ ...prev, [key]: value }));
  };

  const handleResumeUpload = async (file: File | null) => {
    if (!file) return;
    setIsParsing(true);
    try {
      const parsed = await resumesApi.parse(file);
      setFormData((prev: any) => ({
        ...prev,
        careerLevel: parsed.career_level || prev.careerLevel,
        skills: parsed.skills || prev.skills,
        education: parsed.education?.map((e: any) => ({
          level: e.qualification_level,
          degree: e.degree,
          institute: e.institute,
          field: e.field_of_study,
          year: e.passing_year ? String(e.passing_year) : '',
          cgpa: e.cgpa
        })) || prev.education,
        experience: parsed.experience?.map((e: any) => ({
          company: e.company_name,
          role: e.role,
          current: e.is_current,
          desc: e.responsibilities,
        })) || prev.experience,
        certifications: parsed.certifications?.map((c: any) => ({
          name: c.name,
          org: c.issuing_org
        })) || prev.certifications,
        projects: parsed.projects?.map((p: any) => ({
          name: p.project_name,
          tools: p.tools_used,
          desc: p.responsibilities
        })) || prev.projects,
      }));
    } catch (error) {
      console.error('Failed to parse resume', error);
      alert('Failed to parse resume: ' + (error as Error).message);
    } finally {
      setIsParsing(false);
    }
  };

  const updateArrayItem = (key: string, index: number, field: string, value: any) => {
    const newArr = [...formData[key]];
    newArr[index] = { ...newArr[index], [field]: value };
    updateForm(key, newArr);
  };

  const handleSave = async () => {
    if (saving) return;

    if (currentStep < STEPS.length - 1) {
      try {
        if (currentStep === 0 && formData.careerLevel) {
          await candidateApi.updateMe({ career_level: formData.careerLevel });
        }
      } catch (err) {
        console.error('Step save failed', err);
      }
      nextStep();
      return;
    }

    setSaving(true);
    try {
      if (formData.careerLevel) {
        await candidateApi.updateMe({ career_level: formData.careerLevel });
      }
      if (formData.skills?.length) {
        await candidateApi.putSkills(formData.skills);
      }
      for (const ed of formData.education || []) {
        if (!ed.level && !ed.degree && !ed.university && !ed.institute) continue;
        await candidateApi.addEducation({
          qualification_level: ed.level,
          degree: ed.degree || ed.field,
          institute: ed.institute || ed.university,
          field_of_study: ed.field || ed.degree,
          passing_year: ed.year ? Number(ed.year) : undefined,
          cgpa: ed.cgpa || ed.score,
        });
      }
      for (const c of formData.certifications || []) {
        if (!c.name) continue;
        await candidateApi.addCertification({
          name: c.name,
          issuing_org: c.org || c.issuer,
          description: c.desc,
          credential_id: c.id || undefined,
          completion_date: c.date || undefined,
        });
      }
      for (const e of formData.experience || []) {
        if (!e.company && !e.role && !e.title) continue;
        await candidateApi.addExperience({
          company_name: e.company,
          role: e.title || e.role,
          designation: e.title || e.role,
          employment_type: e.type || undefined,
          current_salary: e.salary || undefined,
          from_date: e.fromDate || undefined,
          to_date: e.currentlyWorking ? undefined : e.toDate || undefined,
          responsibilities: e.desc || e.description,
          is_current: Boolean(e.currentlyWorking || e.current),
          gap_reason: e.gap || undefined,
        });
      }
      for (const p of formData.projects || []) {
        if (!p.name && !p.desc && !p.tools) continue;
        await candidateApi.addProject({
          org: p.org || undefined,
          project_name: p.name,
          team_size: p.size ? Number(p.size) : undefined,
          tools_used: p.tools,
          responsibilities: p.desc,
        });
      }
    } catch (err: any) {
      alert(err?.detail || err?.message || 'Failed to save profile. Please try again.');
      setSaving(false);
      return;
    }
    setCandidateProfile({
      skills: formData.skills,
      education: formData.education,
      experience: formData.experience,
      certifications: formData.certifications,
      projects: formData.projects,
      careerLevel: formData.careerLevel,
    });
    setProfileComplete(true);
    router.push('/onboarding/generate');
  };

  return (
    <div className="max-w-3xl mx-auto py-10 px-4">
        <div className="flex flex-col items-center mb-6">
          <StrengthMeter 
            completionPercentage={Math.round(((currentStep) / STEPS.length) * 100) || 10} 
            nextStepTip={`Add your ${STEPS[currentStep].toLowerCase()} to strengthen your profile.`} 
          />
          <div className="mt-4 w-full max-w-md scale-90 opacity-70 origin-top">
            <StepProgress steps={STEPS} currentStep={currentStep} />
          </div>
        </div>

      <div className="bg-white rounded-xl shadow-sm border border-border-soft p-8">
        {currentStep === 0 && (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-ink">Basic Information</h2>
            
            <div className="bg-brand-blue/5 border border-brand-blue/20 rounded-xl p-6 mb-6">
              <h3 className="text-lg font-semibold text-brand-blue mb-2">⚡ Resume Auto-fill</h3>
              <p className="text-ink-muted text-sm mb-4">Upload your existing resume and let AI extract and fill out your profile details automatically!</p>
              <FileDropzone 
                onFileSelect={handleResumeUpload} 
                accept="application/pdf"
                maxSizeMB={5}
              />
              {isParsing && (
                <div className="mt-4 flex items-center justify-center text-primary font-medium animate-pulse">
                  🤖 AI is reading your resume... this might take a few seconds...
                </div>
              )}
            </div>

            <FormField label="Photo Upload">
              <FileDropzone onFileSelect={(_file) => {/* TODO: Implement file upload */}} accept="image/*" />
            </FormField>
            
            <FormField label="Career Level" required>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {['Fresher', 'Early Career', 'Mid Career', 'Experienced'].map(level => (
                  <button
                    key={level}
                    onClick={() => updateForm('careerLevel', level)}
                    className={`p-4 rounded-xl border-2 text-center transition-all ${
                      formData.careerLevel === level 
                        ? 'border-primary bg-brand-blue/10 text-primary font-bold' 
                        : 'border-border-soft text-ink-muted hover:border-border-soft'
                    }`}
                  >
                    {level}
                  </button>
                ))}
              </div>
            </FormField>
          </div>
        )}

        {currentStep === 1 && (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-ink">Education Details</h2>
            <EducationSection items={formData.education} onChange={(items) => updateForm('education', items)} />
          </div>
        )}

        {currentStep === 2 && (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-ink">Certifications</h2>
            <CertificationsSection items={formData.certifications} onChange={(items) => updateForm('certifications', items)} />
          </div>
        )}

        {currentStep === 3 && (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-ink">Work Experience</h2>
            <ExperienceSection items={formData.experience} onChange={(items) => updateForm('experience', items)} />
          </div>
        )}

        {currentStep === 4 && (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-ink">Skills & Additional Info</h2>
            <SkillsSection skills={formData.skills} onChange={(skills) => updateForm('skills', skills)} />
            
            <FormField label="Hobbies">
              <TagInput tags={formData.hobbies} onChange={(tags) => updateForm('hobbies', tags)} placeholder="Add a hobby and press Enter" />
            </FormField>
            
            <FormField label="Extracurricular Activities">
              <Textarea placeholder="Details about extracurriculars" value={formData.extra || ""} onChange={(e) => updateForm('extra', e.target.value)} />
            </FormField>

            <ProjectsSection items={formData.projects} onChange={(items) => updateForm('projects', items)} />
          </div>
        )}

        <div className="mt-8 pt-6 border-t border-border-soft flex items-center justify-between">
          <Button variant="ghost" onClick={prevStep} disabled={currentStep === 0 || saving}>
            Back
          </Button>
          <Button variant="primary" onClick={handleSave} disabled={saving}>
            {saving
              ? 'Saving...'
              : currentStep === STEPS.length - 1
                ? 'Finish'
                : 'Save & Continue'}
          </Button>
        </div>
      </div>
    </div>
  );
}
