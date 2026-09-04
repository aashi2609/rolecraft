"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useUser } from '@/context/UserContext';
import { Button } from '@/components/ui/Button';
import { FormField, Input, Textarea } from '@/components/ui/FormField';
import { FileDropzone } from '@/components/ui/FileDropzone';
import { SearchableCombobox } from '@/components/ui/SearchableCombobox';
import { companyApi, jobsApi } from '@/lib/api';

const CITIES = [
  'Bengaluru', 'Mumbai', 'New Delhi', 'Hyderabad', 'Pune', 'Chennai',
  'Gurugram', 'Noida', 'Kolkata', 'Ahmedabad', 'Remote',
];

const INDUSTRIES = [
  'Technology / IT Services', 'EdTech', 'FinTech', 'E-commerce', 'Healthcare',
  'Manufacturing', 'BFSI (Banking, Financial Services & Insurance)', 'Consulting',
  'Retail', 'Media & Entertainment', 'Logistics & Supply Chain', 'Real Estate',
  'Telecommunications', 'Automotive', 'Other',
];

export const PARSED_JD_STORAGE_KEY = 'rolecraft_parsed_jd';

export default function CompanyProfileOnboarding() {
  const router = useRouter();
  const { setCompanyProfileComplete } = useUser();
  const [saving, setSaving] = useState(false);
  const [parsingJd, setParsingJd] = useState(false);
  const [jdFileName, setJdFileName] = useState<string | null>(null);
  const [jdNote, setJdNote] = useState<string | null>(null);
  const [parsedJd, setParsedJd] = useState<Record<string, unknown> | null>(null);
  const [formData, setFormData] = useState({
    name: 'Example Company',
    about: '',
    size: '11-50',
    website: '',
    location: '',
    industry: 'Technology / IT Services',
  });

  const handleJdUpload = async (file: File) => {
    setParsingJd(true);
    setJdFileName(file.name);
    setJdNote(null);
    try {
      const parsed = await jobsApi.parseJd(file);
      setParsedJd(parsed as Record<string, unknown>);
      setFormData((prev) => ({
        ...prev,
        location: prev.location || parsed.city || prev.location,
      }));
      const src = parsed.parse_source || 'llm';
      setJdNote(
        src.includes('heuristic')
          ? `Parsed ${file.name} with local fallback. Save profile to continue into Post a Job with fields filled.`
          : `Parsed ${file.name}. Save profile to continue into Post a Job with fields filled.`
      );
    } catch (err: unknown) {
      setParsedJd(null);
      setJdNote(err instanceof Error ? err.message : 'Failed to parse JD');
    } finally {
      setParsingJd(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
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

    if (parsedJd) {
      try {
        localStorage.setItem(PARSED_JD_STORAGE_KEY, JSON.stringify(parsedJd));
      } catch {
        /* ignore */
      }
      router.push('/company/jobs/new?fromJd=1');
      return;
    }
    router.push('/company/dashboard');
  };

  return (
    <div className="min-h-screen bg-surface-soft flex items-center justify-center py-12 px-4">
      <div className="w-full max-w-2xl bg-white rounded-xl shadow-sm border border-border-soft p-8">
        <h1 className="text-3xl font-bold text-ink mb-2">Complete your Company Profile</h1>
        <p className="text-ink-muted mb-8">
          This information will be visible to candidates when they view your job postings.
        </p>

        <div className="space-y-6">
          <div className="bg-brand-blue/5 border border-brand-blue/20 rounded-xl p-6">
            <h3 className="text-lg font-semibold text-brand-blue mb-2">Magic Auto-fill from JD</h3>
            <p className="text-ink-muted text-sm mb-4">
              Like candidates uploading a resume, upload a job description (PDF or TXT).
              We extract title, role, level, experience, salary, location, and description for your first job.
            </p>
            <FileDropzone
              onFileSelect={handleJdUpload}
              accept="application/pdf,text/plain,.pdf,.txt"
              maxSizeMB={5}
            />
            {parsingJd && (
              <p className="mt-3 text-sm text-primary font-medium animate-pulse">
                Parsing job description…
              </p>
            )}
            {jdFileName && !parsingJd && (
              <p className="mt-3 text-sm text-primary font-medium">Uploaded: {jdFileName}</p>
            )}
            {jdNote && (
              <p className="mt-2 text-xs text-ink-muted bg-white/70 border border-border-soft rounded-lg px-3 py-2">
                {jdNote}
              </p>
            )}
          </div>

          <FormField label="Company Logo">
            <FileDropzone onFileSelect={() => { /* TODO: logo upload */ }} accept="image/*" />
          </FormField>

          <FormField label="Company Name" required>
            <Input
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            />
          </FormField>

          <FormField label="About Company" required>
            <Textarea
              placeholder="Describe your company mission, culture, and what you do..."
              value={formData.about}
              onChange={(e) => setFormData({ ...formData, about: e.target.value })}
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
                onChange={(e) => setFormData({ ...formData, size: e.target.value })}
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
                onChange={(e) => setFormData({ ...formData, website: e.target.value })}
              />
            </FormField>

            <FormField label="HQ Location" required>
              <SearchableCombobox
                options={CITIES}
                value={formData.location}
                onChange={(val) => setFormData({ ...formData, location: val })}
                placeholder="e.g. Bengaluru"
              />
            </FormField>

            <FormField label="Industry" required>
              <SearchableCombobox
                options={INDUSTRIES}
                value={formData.industry}
                onChange={(val) => setFormData({ ...formData, industry: val })}
                placeholder="Select Industry"
              />
            </FormField>
          </div>

          <div className="pt-6 border-t border-border-soft flex justify-end gap-3">
            <Button
              variant="outline"
              disabled={saving}
              onClick={() => {
                setCompanyProfileComplete(true);
                router.push('/company/dashboard');
              }}
            >
              Skip to Dashboard
            </Button>
            <Button variant="primary" onClick={handleSave} disabled={saving || parsingJd}>
              {saving
                ? 'Saving…'
                : parsedJd
                  ? 'Save & Post Job from JD'
                  : 'Save & Continue'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
