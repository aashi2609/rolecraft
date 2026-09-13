"use client";

import React from 'react';
import { FormField, Input, Textarea } from '@/components/ui/FormField';
import { SearchableCombobox } from '@/components/ui/SearchableCombobox';
import { RepeatableSection } from '@/components/ui/RepeatableSection';
import { FileDropzone } from '@/components/ui/FileDropzone';
import { TagInput } from '@/components/ui/TagInput';
import { SKILLS } from '@/lib/constants';

export const EDU_LEVELS = ['10th', '12th', 'Diploma', 'B.Tech/B.E.', 'B.Sc', 'B.Com', 'BA', 'BBA', 'BCA', 'M.Tech/M.E.', 'M.Sc', 'MBA', 'MCA', 'PhD', 'Other'];
export const DEGREES = ['Computer Science', 'Information Technology', 'Electronics', 'Electronics & Communication', 'Mechanical', 'Commerce', 'Business Administration', 'Physics', 'Mathematics'];
export const UNIVERSITIES = ['IIT Bombay', 'IIT Delhi', 'IIT Madras', 'BITS Pilani', 'NIT Trichy', 'Delhi University', 'Mumbai University', 'Anna University', 'CBSE Board', 'ICSE Board'];
export const CERT_NAMES = ['AWS Certified Solutions Architect', 'Google Cloud Professional', 'Meta Front-End Developer', 'PMP', 'Scrum Master/CSM'];
export const ORGS = ['Coursera', 'Udemy', 'edX', 'Google', 'AWS', 'Microsoft', 'Meta', 'IBM'];
export const TECH_SKILLS = SKILLS;

export function EducationSection({ items = [], onChange }: { items: any[], onChange: (items: any[]) => void }) {
  const updateItem = (index: number, field: string, value: any) => {
    const newArr = [...items];
    newArr[index] = { ...newArr[index], [field]: value };
    onChange(newArr);
  };

  return (
    <RepeatableSection
      title="Education History"
      addLabel="Add Education"
      items={items}
      onAdd={() => onChange([...items, {}])}
      onRemove={(idx) => onChange(items.filter((_, i) => i !== idx))}
      renderItem={(item: any, index: number) => (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FormField label="Qualification Level" required>
              <SearchableCombobox 
                options={EDU_LEVELS} 
                value={item.level || item.qualification_level || ""} 
                onChange={(val) => updateItem(index, 'level', val)} 
                placeholder="e.g., Bachelor's"
              />
            </FormField>
            <FormField label="Degree" required>
              <SearchableCombobox 
                options={DEGREES} 
                value={item.degree || item.field_of_study || ""} 
                onChange={(val) => updateItem(index, 'degree', val)} 
                placeholder="e.g., B.Tech Computer Science"
              />
            </FormField>
            <FormField label="University/College" required>
              <SearchableCombobox 
                options={UNIVERSITIES} 
                value={item.university || item.institute || ""} 
                onChange={(val) => updateItem(index, 'university', val)} 
                placeholder="Institution Name"
              />
            </FormField>
            <FormField label="Passing Year" required>
              <Input type="number" placeholder="YYYY" value={item.year || item.passing_year || ""} onChange={(e) => updateItem(index, 'year', e.target.value)} />
            </FormField>
            <FormField label="CGPA/Percentage" required>
              <Input placeholder="e.g., 8.5 or 85%" value={item.score || item.cgpa || ""} onChange={(e) => updateItem(index, 'score', e.target.value)} />
            </FormField>
          </div>
          <FormField label="Marksheet / Certificate Upload">
            <FileDropzone onFileSelect={(_file) => {/* TODO: Implement file upload */}} accept=".pdf,.jpg,.png" />
          </FormField>
        </div>
      )}
    />
  );
}

export function CertificationsSection({ items = [], onChange }: { items: any[], onChange: (items: any[]) => void }) {
  const updateItem = (index: number, field: string, value: any) => {
    const newArr = [...items];
    newArr[index] = { ...newArr[index], [field]: value };
    onChange(newArr);
  };

  return (
    <RepeatableSection
      title="Certifications & Licenses"
      addLabel="Add Certification"
      items={items}
      onAdd={() => onChange([...items, {}])}
      onRemove={(idx) => onChange(items.filter((_, i) => i !== idx))}
      renderItem={(item: any, index: number) => (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FormField label="Certification Name" required>
              <SearchableCombobox 
                options={CERT_NAMES} 
                value={item.name || ""} 
                onChange={(val) => updateItem(index, 'name', val)} 
                placeholder="e.g., AWS Certified Solutions Architect"
              />
            </FormField>
            <FormField label="Issuing Organization" required>
              <SearchableCombobox 
                options={ORGS} 
                value={item.org || item.issuing_org || ""} 
                onChange={(val) => updateItem(index, 'org', val)} 
                placeholder="e.g., Amazon Web Services"
              />
            </FormField>
            <FormField label="Completion Date">
              <Input type="date" value={item.date || item.completion_date || ""} onChange={(e) => updateItem(index, 'date', e.target.value)} />
            </FormField>
            <FormField label="Credential ID">
              <Input placeholder="Optional" value={item.id || item.credential_id || ""} onChange={(e) => updateItem(index, 'id', e.target.value)} />
            </FormField>
          </div>
          <FormField label="Description">
            <Textarea placeholder="Brief description of what you learned" className="min-h-[80px]" value={item.desc || item.description || ""} onChange={(e) => updateItem(index, 'desc', e.target.value)} />
          </FormField>
          <FormField label="Certificate File (Optional)">
            <FileDropzone onFileSelect={(_file) => {/* TODO: Implement file upload */}} />
          </FormField>
        </div>
      )}
    />
  );
}

export function ExperienceSection({ items = [], onChange }: { items: any[], onChange: (items: any[]) => void }) {
  const updateItem = (index: number, field: string, value: any) => {
    const newArr = [...items];
    newArr[index] = { ...newArr[index], [field]: value };
    onChange(newArr);
  };

  return (
    <RepeatableSection
      title="Experience"
      addLabel="Add Experience"
      items={items}
      onAdd={() => onChange([...items, {}])}
      onRemove={(idx) => onChange(items.filter((_, i) => i !== idx))}
      renderItem={(item: any, index: number) => (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FormField label="Company Name" required>
              <Input placeholder="Company Name" value={item.company || item.company_name || ""} onChange={(e) => updateItem(index, 'company', e.target.value)} />
            </FormField>
            <FormField label="Role / Designation" required>
              <Input placeholder="e.g., Software Engineer" value={item.role || item.designation || ""} onChange={(e) => updateItem(index, 'role', e.target.value)} />
            </FormField>
            <FormField label="Employment Type">
              <Input placeholder="e.g., Full-time, Contract" value={item.type || item.employment_type || ""} onChange={(e) => updateItem(index, 'type', e.target.value)} />
            </FormField>
            <FormField label="Salary">
              <Input placeholder="Current / Expected" value={item.salary || item.current_salary || ""} onChange={(e) => updateItem(index, 'salary', e.target.value)} />
            </FormField>
            <FormField label="From Date" required>
              <Input type="date" value={item.fromDate || (item.from_date ? String(item.from_date).slice(0, 10) : "")} onChange={(e) => updateItem(index, 'fromDate', e.target.value)} />
            </FormField>
            <FormField label="To Date">
              <div className="flex flex-col gap-2">
                 <Input type="date" disabled={item.currentlyWorking || item.is_current} value={item.toDate || (item.to_date ? String(item.to_date).slice(0, 10) : "")} onChange={(e) => updateItem(index, 'toDate', e.target.value)} />
                 <label className="flex items-center gap-2 text-sm text-ink-muted">
                   <input type="checkbox" checked={item.currentlyWorking || item.is_current || false} onChange={(e) => {
                     updateItem(index, 'currentlyWorking', e.target.checked);
                   }} />
                   Currently working here
                 </label>
              </div>
            </FormField>
          </div>
          <FormField label="Responsibilities">
            <Textarea placeholder="What did you do? (Max 1000 chars)" maxLength={1000} value={item.desc || item.responsibilities || ""} onChange={(e) => updateItem(index, 'desc', e.target.value)} />
          </FormField>
          <div className="p-4 bg-surface-soft rounded-lg border border-border-soft mt-4">
            <FormField label="Employment Gap (if any)">
              <Input placeholder="Reason for gap before/after this role" value={item.gap || item.gap_reason || ""} onChange={(e) => updateItem(index, 'gap', e.target.value)} />
            </FormField>
          </div>
        </div>
      )}
    />
  );
}

export function ProjectsSection({ items = [], onChange }: { items: any[], onChange: (items: any[]) => void }) {
  const updateItem = (index: number, field: string, value: any) => {
    const newArr = [...items];
    newArr[index] = { ...newArr[index], [field]: value };
    onChange(newArr);
  };

  return (
    <RepeatableSection
      title="Projects"
      addLabel="Add Project"
      items={items}
      onAdd={() => onChange([...items, {}])}
      onRemove={(idx) => onChange(items.filter((_, i) => i !== idx))}
      renderItem={(item: any, index: number) => (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FormField label="Project Name"><Input value={item.name || item.project_name || ""} onChange={(e) => updateItem(index, 'name', e.target.value)} /></FormField>
            <FormField label="Organization"><Input value={item.org || ""} onChange={(e) => updateItem(index, 'org', e.target.value)} /></FormField>
            <FormField label="Team Size"><Input type="number" value={item.size || item.team_size || ""} onChange={(e) => updateItem(index, 'size', e.target.value)} /></FormField>
            <FormField label="Tools/Tech"><Input value={item.tools || item.tools_used || ""} onChange={(e) => updateItem(index, 'tools', e.target.value)} /></FormField>
          </div>
          <FormField label="Responsibilities / Achievements"><Textarea value={item.desc || item.responsibilities || ""} onChange={(e) => updateItem(index, 'desc', e.target.value)} /></FormField>
        </div>
      )}
    />
  );
}

export function SkillsSection({ skills = [], onChange }: { skills: string[], onChange: (skills: string[]) => void }) {
  return (
    <FormField label="Skills">
      <SearchableCombobox 
        options={TECH_SKILLS} 
        value={skills} 
        onChange={onChange} 
        placeholder="Select or type to add a skill"
        multiSelect={true}
      />
    </FormField>
  );
}
