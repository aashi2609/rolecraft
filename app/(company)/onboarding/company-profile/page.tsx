"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useUser } from '@/context/UserContext';
import { Button } from '@/components/ui/Button';
import { FormField, Input, Textarea } from '@/components/ui/FormField';
import { FileDropzone } from '@/components/ui/FileDropzone';
import { SearchableCombobox } from '@/components/ui/SearchableCombobox';

const CITIES = [
  'Bengaluru', 'Mumbai', 'New Delhi', 'Hyderabad', 'Pune', 'Chennai', 
  'Gurugram', 'Noida', 'Kolkata', 'Ahmedabad', 'Remote'
];

const INDUSTRIES = [
  'Technology / IT Services', 'EdTech', 'FinTech', 'E-commerce', 'Healthcare', 
  'Manufacturing', 'BFSI (Banking, Financial Services & Insurance)', 'Consulting', 
  'Retail', 'Media & Entertainment', 'Logistics & Supply Chain', 'Real Estate', 
  'Telecommunications', 'Automotive', 'Other'
];

export default function CompanyProfileOnboarding() {
  const router = useRouter();
  const { setCompanyProfileComplete } = useUser();
  const [formData, setFormData] = useState({
    name: 'Example Company', // Prefilled from signup realistically
    about: '',
    size: '11-50',
    website: '',
    location: '',
    industry: 'Technology / IT Services', // Carried over from signup
  });

  const handleSave = () => {
    // Save to backend logic goes here
    setCompanyProfileComplete(true);
    router.push('/company/dashboard');
  };

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center py-12 px-4">
      <div className="w-full max-w-2xl bg-white rounded-xl shadow-sm border border-slate-200 p-8">
        <h1 className="text-3xl font-bold text-slate-900 mb-2">Complete your Company Profile</h1>
        <p className="text-slate-500 mb-8">
          This information will be visible to candidates when they view your job postings.
        </p>

        <div className="space-y-6">
          <FormField label="Company Logo">
            <FileDropzone onFileSelect={(f) => console.log(f)} accept="image/*" />
          </FormField>

          <FormField label="Company Name" required>
            <Input 
              value={formData.name} 
              onChange={e => setFormData({...formData, name: e.target.value})} 
            />
          </FormField>

          <FormField label="About Company" required>
            <Textarea 
              placeholder="Describe your company mission, culture, and what you do..." 
              value={formData.about} 
              onChange={e => setFormData({...formData, about: e.target.value})} 
              maxLength={500}
              className="min-h-[100px]"
            />
            <div className="text-right text-xs text-slate-400 mt-1">{formData.about.length}/500</div>
          </FormField>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <FormField label="Company Size" required>
              <select 
                className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-primary text-slate-900"
                value={formData.size}
                onChange={e => setFormData({...formData, size: e.target.value})}
              >
                <option value="1-10">1-10 employees</option>
                <option value="11-50">11-50 employees</option>
                <option value="51-200">51-200 employees</option>
                <option value="201-1000">201-1000 employees</option>
                <option value="1000+">1000+ employees</option>
              </select>
            </FormField>

            <FormField label="Website URL" required>
              <Input 
                type="url" 
                placeholder="https://..." 
                value={formData.website} 
                onChange={e => setFormData({...formData, website: e.target.value})} 
              />
            </FormField>

            <FormField label="HQ Location" required>
              <SearchableCombobox 
                options={CITIES}
                value={formData.location}
                onChange={val => setFormData({...formData, location: val})}
                placeholder="e.g. Bengaluru"
              />
            </FormField>

            <FormField label="Industry" required>
              <SearchableCombobox 
                options={INDUSTRIES}
                value={formData.industry}
                onChange={val => setFormData({...formData, industry: val})}
                placeholder="Select Industry"
              />
            </FormField>
          </div>

          <div className="pt-6 border-t border-slate-100 flex justify-end">
            <Button variant="primary" onClick={handleSave}>
              Save & Continue
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
