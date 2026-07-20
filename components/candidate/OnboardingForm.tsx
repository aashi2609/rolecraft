"use client";

import React, { useState } from 'react';
import { StepProgress } from '@/components/ui/StepProgress';
import { Button } from '@/components/ui/Button';
import { FormField, Input, Textarea } from '@/components/ui/FormField';
import { FileDropzone } from '@/components/ui/FileDropzone';
import { TagInput } from '@/components/ui/TagInput';
import { RepeatableSection } from '@/components/ui/RepeatableSection';
import { Card } from '@/components/ui/Card';

const STEPS = ['Basic', 'Education', 'Certifications', 'Experience', 'Skills'];

export default function OnboardingForm() {
  const [currentStep, setCurrentStep] = useState(0);
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

  const handleSave = () => {
    console.log('Saved form data:', formData);
    if (currentStep < STEPS.length - 1) {
      nextStep();
    } else {
      alert('Onboarding completed! Data saved to console.');
    }
  };

  return (
    <div className="max-w-3xl mx-auto py-10 px-4">
      <div className="mb-12">
        <StepProgress steps={STEPS} currentStep={currentStep} />
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-8">
        {currentStep === 0 && (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-slate-900">Basic Information</h2>
            <FormField label="Photo Upload">
              <FileDropzone onFileSelect={(f) => console.log(f)} accept="image/*" />
            </FormField>
            
            <FormField label="Career Level" required>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {['Fresher', 'Early Career', 'Mid Career', 'Experienced'].map(level => (
                  <button
                    key={level}
                    onClick={() => updateForm('careerLevel', level)}
                    className={`p-4 rounded-xl border-2 text-center transition-all ${
                      formData.careerLevel === level 
                        ? 'border-primary bg-blue-50 text-primary font-bold' 
                        : 'border-slate-200 text-slate-600 hover:border-slate-300'
                    }`}
                  >
                    {level}
                  </button>
                ))}
              </div>
            </FormField>

            <FormField label="Resume Upload">
              <FileDropzone onFileSelect={(f) => console.log(f)} accept=".pdf,.doc,.docx" maxSizeMB={10} />
            </FormField>
          </div>
        )}

        {currentStep === 1 && (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-slate-900">Education Details</h2>
            <RepeatableSection
              title="Education History"
              addLabel="Add Education"
              items={formData.education}
              onAdd={() => updateForm('education', [...formData.education, {}])}
              onRemove={(idx) => updateForm('education', formData.education.filter((_: any, i: number) => i !== idx))}
              renderItem={(item, index) => (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <FormField label="Qualification Level" required>
                      <Input placeholder="e.g., Bachelor's" />
                    </FormField>
                    <FormField label="Degree" required>
                      <Input placeholder="e.g., B.Tech Computer Science" />
                    </FormField>
                    <FormField label="University/College" required>
                      <Input placeholder="Institution Name" />
                    </FormField>
                    <FormField label="Passing Year" required>
                      <Input type="number" placeholder="YYYY" />
                    </FormField>
                    <FormField label="CGPA/Percentage" required>
                      <Input placeholder="e.g., 8.5 or 85%" />
                    </FormField>
                  </div>
                  <FormField label="Marksheet / Certificate Upload">
                    <FileDropzone onFileSelect={(f) => console.log(f)} accept=".pdf,.jpg,.png" />
                  </FormField>
                </div>
              )}
            />
          </div>
        )}

        {currentStep === 2 && (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-slate-900">Certifications</h2>
            <RepeatableSection
              title="Certifications & Licenses"
              addLabel="Add Certification"
              items={formData.certifications}
              onAdd={() => updateForm('certifications', [...formData.certifications, {}])}
              onRemove={(idx) => updateForm('certifications', formData.certifications.filter((_: any, i: number) => i !== idx))}
              renderItem={(item, index) => (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <FormField label="Certification Name" required>
                      <Input placeholder="e.g., AWS Certified Solutions Architect" />
                    </FormField>
                    <FormField label="Issuing Organization" required>
                      <Input placeholder="e.g., Amazon Web Services" />
                    </FormField>
                    <FormField label="Completion Date">
                      <Input type="date" />
                    </FormField>
                    <FormField label="Credential ID">
                      <Input placeholder="Optional" />
                    </FormField>
                  </div>
                  <FormField label="Description">
                    <Textarea placeholder="Brief description of what you learned" className="min-h-[80px]" />
                  </FormField>
                  <FormField label="Certificate File (Optional)">
                    <FileDropzone onFileSelect={(f) => console.log(f)} />
                  </FormField>
                </div>
              )}
            />
          </div>
        )}

        {currentStep === 3 && (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-slate-900">Work Experience</h2>
            <RepeatableSection
              title="Experience"
              addLabel="Add Experience"
              items={formData.experience}
              onAdd={() => updateForm('experience', [...formData.experience, {}])}
              onRemove={(idx) => updateForm('experience', formData.experience.filter((_: any, i: number) => i !== idx))}
              renderItem={(item, index) => (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <FormField label="Company Name" required>
                      <Input placeholder="Company Name" />
                    </FormField>
                    <FormField label="Role / Designation" required>
                      <Input placeholder="e.g., Software Engineer" />
                    </FormField>
                    <FormField label="Employment Type">
                      <Input placeholder="e.g., Full-time, Contract" />
                    </FormField>
                    <FormField label="Salary">
                      <Input placeholder="Current / Expected" />
                    </FormField>
                    <FormField label="From Date" required>
                      <Input type="date" />
                    </FormField>
                    <FormField label="To Date">
                      <div className="flex flex-col gap-2">
                         <Input type="date" disabled={item.currentlyWorking} />
                         <label className="flex items-center gap-2 text-sm text-slate-600">
                           <input type="checkbox" onChange={(e) => {
                             const newExp = [...formData.experience];
                             newExp[index].currentlyWorking = e.target.checked;
                             updateForm('experience', newExp);
                           }} />
                           Currently working here
                         </label>
                      </div>
                    </FormField>
                  </div>
                  <FormField label="Responsibilities">
                    <Textarea placeholder="What did you do? (Max 1000 chars)" maxLength={1000} />
                  </FormField>
                  <div className="p-4 bg-slate-50 rounded-lg border border-slate-200 mt-4">
                    <FormField label="Employment Gap (if any)">
                      <Input placeholder="Reason for gap before/after this role" />
                    </FormField>
                  </div>
                </div>
              )}
            />
          </div>
        )}

        {currentStep === 4 && (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-slate-900">Skills & Additional Info</h2>
            <FormField label="Skills">
              <TagInput tags={formData.skills} onChange={(tags) => updateForm('skills', tags)} placeholder="Add a skill and press Enter" />
            </FormField>
            
            <FormField label="Hobbies">
              <TagInput tags={formData.hobbies} onChange={(tags) => updateForm('hobbies', tags)} placeholder="Add a hobby and press Enter" />
            </FormField>
            
            <FormField label="Extracurricular Activities">
              <Textarea placeholder="Details about extracurriculars" />
            </FormField>

            <RepeatableSection
              title="Projects"
              addLabel="Add Project"
              items={formData.projects}
              onAdd={() => updateForm('projects', [...formData.projects, {}])}
              onRemove={(idx) => updateForm('projects', formData.projects.filter((_: any, i: number) => i !== idx))}
              renderItem={(item, index) => (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <FormField label="Project Name"><Input /></FormField>
                    <FormField label="Organization"><Input /></FormField>
                    <FormField label="Team Size"><Input type="number" /></FormField>
                    <FormField label="Tools/Tech"><Input /></FormField>
                  </div>
                  <FormField label="Responsibilities / Achievements"><Textarea /></FormField>
                </div>
              )}
            />
          </div>
        )}

        <div className="mt-8 pt-6 border-t border-slate-100 flex items-center justify-between">
          <Button variant="ghost" onClick={prevStep} disabled={currentStep === 0}>
            Back
          </Button>
          <Button variant="primary" onClick={handleSave}>
            {currentStep === STEPS.length - 1 ? 'Finish' : 'Save & Continue'}
          </Button>
        </div>
      </div>
    </div>
  );
}
