"use client";

import React, { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { FormField, Input, Textarea } from '@/components/ui/FormField';
import { TagInput } from '@/components/ui/TagInput';
import { RepeatableSection } from '@/components/ui/RepeatableSection';

export default function PersonalDetailsForm() {
  const [formData, setFormData] = useState<any>({
    family: []
  });

  const updateForm = (key: string, value: any) => {
    setFormData((prev: any) => ({ ...prev, [key]: value }));
  };

  const handleSave = () => console.log('Save', formData);

  return (
    <div className="max-w-4xl mx-auto py-10 px-4">
      <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-8 space-y-8">
        
        <section>
          <h2 className="text-xl font-bold text-slate-900 border-b pb-2 mb-4">Basic Information</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <FormField label="Date of Birth"><Input type="date" /></FormField>
            <FormField label="Gender">
              <select className="px-3 py-2 bg-white border border-slate-200 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-slate-900">
                <option>Select</option>
                <option>Male</option>
                <option>Female</option>
                <option>Other</option>
              </select>
            </FormField>
            <FormField label="Marital Status">
              <select className="px-3 py-2 bg-white border border-slate-200 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent text-slate-900">
                <option>Select</option>
                <option>Single</option>
                <option>Married</option>
              </select>
            </FormField>
            <FormField label="Religion">
              <div className="flex flex-col gap-2">
                <Input placeholder="Enter religion" />
                <label className="flex items-center gap-2 text-sm text-slate-600">
                  <input type="checkbox" /> Prefer not to say
                </label>
              </div>
            </FormField>
          </div>
        </section>

        <section>
          <h2 className="text-xl font-bold text-slate-900 border-b pb-2 mb-4">Address & Preferences</h2>
          <div className="space-y-4">
            <FormField label="Present Address"><Textarea className="min-h-[60px]" /></FormField>
            <label className="flex items-center gap-2 text-sm font-medium text-slate-800">
              <input type="checkbox" /> Permanent address same as present
            </label>
            <FormField label="Permanent Address"><Textarea className="min-h-[60px]" /></FormField>
            <FormField label="Preferred Locations"><TagInput tags={[]} onChange={()=>{}} placeholder="Add locations..." /></FormField>
            <FormField label="Preferred Sectors"><TagInput tags={[]} onChange={()=>{}} placeholder="Add sectors..." /></FormField>
          </div>
        </section>

        <section>
          <h2 className="text-xl font-bold text-slate-900 border-b pb-2 mb-4">Professional Info</h2>
          <div className="space-y-4">
            <FormField label="Strengths"><TagInput tags={[]} onChange={()=>{}} /></FormField>
            <FormField label="Weaknesses"><TagInput tags={[]} onChange={()=>{}} /></FormField>
            <FormField label="Annual Family Income"><Input placeholder="e.g. $50,000 - $80,000" /></FormField>
            
            <RepeatableSection
              title="Web Links"
              addLabel="Add Link"
              items={[]}
              onAdd={() => {}}
              onRemove={() => {}}
              renderItem={() => (
                <div className="flex gap-4">
                  <select className="w-1/3 px-3 py-2 bg-white border border-slate-200 rounded-lg text-slate-900">
                    <option>LinkedIn</option><option>GitHub</option><option>Portfolio</option>
                  </select>
                  <Input className="w-2/3" placeholder="URL" />
                </div>
              )}
            />
          </div>
        </section>

        <section>
          <h2 className="text-xl font-bold text-slate-900 border-b pb-2 mb-4">Family Members</h2>
          <RepeatableSection
            title="Family"
            addLabel="Add Family Member"
            items={formData.family}
            onAdd={() => updateForm('family', [...formData.family, {}])}
            onRemove={(idx) => updateForm('family', formData.family.filter((_: any, i: number) => i !== idx))}
            renderItem={() => (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <FormField label="Name"><Input /></FormField>
                <FormField label="Education"><Input /></FormField>
                <FormField label="Occupation"><Input /></FormField>
                <FormField label="Contact"><Input /></FormField>
                <FormField label="Email"><Input type="email" /></FormField>
              </div>
            )}
          />
        </section>

        <div className="mt-8 pt-6 border-t border-slate-100 flex items-center justify-between">
          <Button variant="ghost">Cancel</Button>
          <div className="space-x-4">
            <Button variant="outline" onClick={handleSave}>Save as Draft</Button>
            <Button variant="primary" onClick={handleSave}>Save & Continue</Button>
          </div>
        </div>

      </div>
    </div>
  );
}
