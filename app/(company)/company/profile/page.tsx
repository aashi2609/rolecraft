"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useUser } from '@/context/UserContext';
import { Button } from '@/components/ui/Button';
import { FormField, Input, Textarea } from '@/components/ui/FormField';
import { FileDropzone } from '@/components/ui/FileDropzone';
import { SearchableCombobox } from '@/components/ui/SearchableCombobox';
import { companyApi } from '@/lib/api';
import { Card } from '@/components/ui/Card';

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

export default function EditCompanyProfilePage() {
  const router = useRouter();
  const { companyProfile, setCompanyProfileComplete } = useUser();
  const [formData, setFormData] = useState({
    name: (companyProfile?.name as string) || 'Example Company',
    about: (companyProfile?.about as string) || '',
    size: (companyProfile?.size as string) || '11-50',
    website: (companyProfile?.website as string) || '',
    location: (companyProfile?.hq_location as string) || '',
    industry: (companyProfile?.industry as string) || 'Technology / IT Services',
  });

  const handleSave = async () => {
    try {
      await companyApi.updateMe({
        name: formData.name,
        about: formData.about,
        size: formData.size,
        website: formData.website,
        hq_location: formData.location,
        industry: formData.industry,
      });
    } catch {
      /* offline */
    }
    setCompanyProfileComplete(true);
    router.push('/company/dashboard');
  };

  return (
    <div className="min-h-screen bg-surface-soft py-10">
      <div className="max-w-3xl mx-auto px-4">
        <h1 className="text-3xl font-bold text-ink mb-2">Edit Company Profile</h1>
        <p className="text-ink-muted mb-8">
          Update the profile information visible to candidates.
        </p>

        <Card className="bg-white p-8">
          <div className="space-y-6">
            <FormField label="Company Logo">
              <FileDropzone onFileSelect={(f) => {/* TODO: Implement file upload */}} accept="image/*" />
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
              <div className="text-right text-xs text-ink-muted mt-1">{formData.about.length}/500</div>
            </FormField>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <FormField label="Company Size" required>
                <select 
                  className="w-full px-3 py-2 bg-white border border-border-soft rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-primary text-ink"
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

            <div className="pt-6 border-t border-border-soft flex justify-end gap-3">
              <Button variant="ghost" onClick={() => router.push('/company/dashboard')}>
                Cancel
              </Button>
              <Button variant="primary" onClick={handleSave}>
                Save Changes
              </Button>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
