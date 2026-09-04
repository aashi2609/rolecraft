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

const STEPS = ['Basic', 'Education', 'Certifications', 'Experience', 'Skills'];

const EDU_LEVELS = ['10th', '12th', 'Diploma', 'B.Tech/B.E.', 'B.Sc', 'B.Com', 'BA', 'BBA', 'BCA', 'M.Tech/M.E.', 'M.Sc', 'MBA', 'MCA', 'PhD', 'Other'];
const DEGREES = ['Computer Science', 'Information Technology', 'Electronics', 'Electronics & Communication', 'Mechanical', 'Commerce', 'Business Administration', 'Physics', 'Mathematics'];
const UNIVERSITIES = ['IIT Bombay', 'IIT Delhi', 'IIT Madras', 'BITS Pilani', 'NIT Trichy', 'Delhi University', 'Mumbai University', 'Anna University', 'CBSE Board', 'ICSE Board'];
const CERT_NAMES = ['AWS Certified Solutions Architect', 'Google Cloud Professional', 'Meta Front-End Developer', 'PMP', 'Scrum Master/CSM'];
const ORGS = ['Coursera', 'Udemy', 'edX', 'Google', 'AWS', 'Microsoft', 'Meta', 'IBM'];
const TECH_SKILLS = SKILLS;

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
              <h3 className="text-lg font-semibold text-brand-blue mb-2">⚡ Magic Auto-fill</h3>
              <p className="text-ink-muted text-sm mb-4">Upload your existing resume and let AI fill out all the tedious details for you!</p>
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

            <FormField label="Resume Upload">
              <FileDropzone onFileSelect={(_file) => {/* TODO: Implement file upload */}} accept=".pdf,.doc,.docx" maxSizeMB={10} />
            </FormField>
          </div>
        )}

        {currentStep === 1 && (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-ink">Education Details</h2>
            <RepeatableSection
              title="Education History"
              addLabel="Add Education"
              items={formData.education}
              onAdd={() => updateForm('education', [...formData.education, {}])}
              onRemove={(idx) => updateForm('education', formData.education.filter((_: any, i: number) => i !== idx))}
              renderItem={(item: any, index: number) => (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <FormField label="Qualification Level" required>
                      <SearchableCombobox 
                        options={EDU_LEVELS} 
                        value={item.level || ""} 
                        onChange={(val) => updateArrayItem('education', index, 'level', val)} 
                        placeholder="e.g., Bachelor's"
                      />
                    </FormField>
                    <FormField label="Degree" required>
                      <SearchableCombobox 
                        options={DEGREES} 
                        value={item.degree || ""} 
                        onChange={(val) => updateArrayItem('education', index, 'degree', val)} 
                        placeholder="e.g., B.Tech Computer Science"
                      />
                    </FormField>
                    <FormField label="University/College" required>
                      <SearchableCombobox 
                        options={UNIVERSITIES} 
                        value={item.university || ""} 
                        onChange={(val) => updateArrayItem('education', index, 'university', val)} 
                        placeholder="Institution Name"
                      />
                    </FormField>
                    <FormField label="Passing Year" required>
                      <Input type="number" placeholder="YYYY" value={item.year || ""} onChange={(e) => updateArrayItem('education', index, 'year', e.target.value)} />
                    </FormField>
                    <FormField label="CGPA/Percentage" required>
                      <Input placeholder="e.g., 8.5 or 85%" value={item.score || ""} onChange={(e) => updateArrayItem('education', index, 'score', e.target.value)} />
                    </FormField>
                  </div>
                  <FormField label="Marksheet / Certificate Upload">
                    <FileDropzone onFileSelect={(_file) => {/* TODO: Implement file upload */}} accept=".pdf,.jpg,.png" />
                  </FormField>
                </div>
              )}
            />
          </div>
        )}

        {currentStep === 2 && (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-ink">Certifications</h2>
            <RepeatableSection
              title="Certifications & Licenses"
              addLabel="Add Certification"
              items={formData.certifications}
              onAdd={() => updateForm('certifications', [...formData.certifications, {}])}
              onRemove={(idx) => updateForm('certifications', formData.certifications.filter((_: any, i: number) => i !== idx))}
              renderItem={(item: any, index: number) => (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <FormField label="Certification Name" required>
                      <SearchableCombobox 
                        options={CERT_NAMES} 
                        value={item.name || ""} 
                        onChange={(val) => updateArrayItem('certifications', index, 'name', val)} 
                        placeholder="e.g., AWS Certified Solutions Architect"
                      />
                    </FormField>
                    <FormField label="Issuing Organization" required>
                      <SearchableCombobox 
                        options={ORGS} 
                        value={item.org || ""} 
                        onChange={(val) => updateArrayItem('certifications', index, 'org', val)} 
                        placeholder="e.g., Amazon Web Services"
                      />
                    </FormField>
                    <FormField label="Completion Date">
                      <Input type="date" value={item.date || ""} onChange={(e) => updateArrayItem('certifications', index, 'date', e.target.value)} />
                    </FormField>
                    <FormField label="Credential ID">
                      <Input placeholder="Optional" value={item.id || ""} onChange={(e) => updateArrayItem('certifications', index, 'id', e.target.value)} />
                    </FormField>
                  </div>
                  <FormField label="Description">
                    <Textarea placeholder="Brief description of what you learned" className="min-h-[80px]" value={item.desc || ""} onChange={(e) => updateArrayItem('certifications', index, 'desc', e.target.value)} />
                  </FormField>
                  <FormField label="Certificate File (Optional)">
                    <FileDropzone onFileSelect={(_file) => {/* TODO: Implement file upload */}} />
                  </FormField>
                </div>
              )}
            />
          </div>
        )}

        {currentStep === 3 && (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-ink">Work Experience</h2>
            <RepeatableSection
              title="Experience"
              addLabel="Add Experience"
              items={formData.experience}
              onAdd={() => updateForm('experience', [...formData.experience, {}])}
              onRemove={(idx) => updateForm('experience', formData.experience.filter((_: any, i: number) => i !== idx))}
              renderItem={(item: any, index: number) => (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <FormField label="Company Name" required>
                      <Input placeholder="Company Name" value={item.company || ""} onChange={(e) => updateArrayItem('experience', index, 'company', e.target.value)} />
                    </FormField>
                    <FormField label="Role / Designation" required>
                      <Input placeholder="e.g., Software Engineer" value={item.role || ""} onChange={(e) => updateArrayItem('experience', index, 'role', e.target.value)} />
                    </FormField>
                    <FormField label="Employment Type">
                      <Input placeholder="e.g., Full-time, Contract" value={item.type || ""} onChange={(e) => updateArrayItem('experience', index, 'type', e.target.value)} />
                    </FormField>
                    <FormField label="Salary">
                      <Input placeholder="Current / Expected" value={item.salary || ""} onChange={(e) => updateArrayItem('experience', index, 'salary', e.target.value)} />
                    </FormField>
                    <FormField label="From Date" required>
                      <Input type="date" value={item.fromDate || ""} onChange={(e) => updateArrayItem('experience', index, 'fromDate', e.target.value)} />
                    </FormField>
                    <FormField label="To Date">
                      <div className="flex flex-col gap-2">
                         <Input type="date" disabled={item.currentlyWorking} value={item.toDate || ""} onChange={(e) => updateArrayItem('experience', index, 'toDate', e.target.value)} />
                         <label className="flex items-center gap-2 text-sm text-ink-muted">
                           <input type="checkbox" checked={item.currentlyWorking || false} onChange={(e) => {
                             updateArrayItem('experience', index, 'currentlyWorking', e.target.checked);
                           }} />
                           Currently working here
                         </label>
                      </div>
                    </FormField>
                  </div>
                  <FormField label="Responsibilities">
                    <Textarea placeholder="What did you do? (Max 1000 chars)" maxLength={1000} value={item.desc || ""} onChange={(e) => updateArrayItem('experience', index, 'desc', e.target.value)} />
                  </FormField>
                  <div className="p-4 bg-surface-soft rounded-lg border border-border-soft mt-4">
                    <FormField label="Employment Gap (if any)">
                      <Input placeholder="Reason for gap before/after this role" value={item.gap || ""} onChange={(e) => updateArrayItem('experience', index, 'gap', e.target.value)} />
                    </FormField>
                  </div>
                </div>
              )}
            />
          </div>
        )}

        {currentStep === 4 && (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-ink">Skills & Additional Info</h2>
            <FormField label="Skills">
              <SearchableCombobox 
                options={TECH_SKILLS} 
                value={formData.skills} 
                onChange={(tags) => updateForm('skills', tags)} 
                placeholder="Select or type to add a skill"
                multiSelect={true}
              />
            </FormField>
            
            <FormField label="Hobbies">
              <TagInput tags={formData.hobbies} onChange={(tags) => updateForm('hobbies', tags)} placeholder="Add a hobby and press Enter" />
            </FormField>
            
            <FormField label="Extracurricular Activities">
              <Textarea placeholder="Details about extracurriculars" value={formData.extra || ""} onChange={(e) => updateForm('extra', e.target.value)} />
            </FormField>

            <RepeatableSection
              title="Projects"
              addLabel="Add Project"
              items={formData.projects}
              onAdd={() => updateForm('projects', [...formData.projects, {}])}
              onRemove={(idx) => updateForm('projects', formData.projects.filter((_: any, i: number) => i !== idx))}
              renderItem={(item: any, index: number) => (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <FormField label="Project Name"><Input value={item.name || ""} onChange={(e) => updateArrayItem('projects', index, 'name', e.target.value)} /></FormField>
                    <FormField label="Organization"><Input value={item.org || ""} onChange={(e) => updateArrayItem('projects', index, 'org', e.target.value)} /></FormField>
                    <FormField label="Team Size"><Input type="number" value={item.size || ""} onChange={(e) => updateArrayItem('projects', index, 'size', e.target.value)} /></FormField>
                    <FormField label="Tools/Tech"><Input value={item.tools || ""} onChange={(e) => updateArrayItem('projects', index, 'tools', e.target.value)} /></FormField>
                  </div>
                  <FormField label="Responsibilities / Achievements"><Textarea value={item.desc || ""} onChange={(e) => updateArrayItem('projects', index, 'desc', e.target.value)} /></FormField>
                </div>
              )}
            />
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
