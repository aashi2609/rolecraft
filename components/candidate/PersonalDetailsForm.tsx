"use client";

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/Button';
import { FormField, Input, Textarea } from '@/components/ui/FormField';
import { TagInput } from '@/components/ui/TagInput';
import { RepeatableSection } from '@/components/ui/RepeatableSection';
import { candidateApi } from '@/lib/api';
import { useUser } from '@/context/UserContext';

export default function PersonalDetailsForm() {
  const router = useRouter();
  const { candidateProfile, refreshSession } = useUser();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [formData, setFormData] = useState({
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
  });

  useEffect(() => {
    const p = candidateProfile || {};
    const links = (p.weblinks as Record<string, string>) || {};
    setFormData((prev) => ({
      ...prev,
      dob: p.dob ? String(p.dob).slice(0, 10) : '',
      gender: (p.gender as string) || '',
      marital_status: (p.marital_status as string) || '',
      present_address: (p.present_address as string) || '',
      permanent_address: (p.permanent_address as string) || '',
      preferred_locations: (p.preferred_locations as string[]) || [],
      preferred_sectors: (p.preferred_sectors as string[]) || [],
      strengths: (p.strengths as string[]) || [],
      weaknesses: (p.weaknesses as string[]) || [],
      annual_family_income: (p.annual_family_income as string) || '',
      weblinks: links,
    }));
  }, [candidateProfile]);

  const updateForm = (key: string, value: unknown) => {
    setFormData((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = async () => {
    setSaving(true);
    setError('');
    try {
      const payload: Record<string, unknown> = {
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
      await refreshSession();
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
            <FormField label="Date of Birth">
              <Input
                type="date"
                value={formData.dob}
                onChange={(e) => updateForm('dob', e.target.value)}
              />
            </FormField>
            <FormField label="Gender">
              <select
                className="w-full px-3 py-2 bg-white border border-border-soft rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-primary text-ink"
                value={formData.gender}
                onChange={(e) => updateForm('gender', e.target.value)}
              >
                <option value="">Select</option>
                <option value="Male">Male</option>
                <option value="Female">Female</option>
                <option value="Other">Other</option>
              </select>
            </FormField>
            <FormField label="Marital Status">
              <select
                className="w-full px-3 py-2 bg-white border border-border-soft rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-primary text-ink"
                value={formData.marital_status}
                onChange={(e) => updateForm('marital_status', e.target.value)}
              >
                <option value="">Select</option>
                <option value="Single">Single</option>
                <option value="Married">Married</option>
              </select>
            </FormField>
          </div>
        </section>

        <section>
          <h2 className="text-xl font-bold text-ink border-b pb-2 mb-4">Address & Preferences</h2>
          <div className="space-y-4">
            <FormField label="Present Address">
              <Textarea
                className="min-h-[60px]"
                value={formData.present_address}
                onChange={(e) => updateForm('present_address', e.target.value)}
              />
            </FormField>
            <label className="flex items-center gap-2 text-sm font-medium text-ink">
              <input
                type="checkbox"
                checked={formData.sameAddress}
                onChange={(e) => updateForm('sameAddress', e.target.checked)}
              />
              Permanent address same as present
            </label>
            <FormField label="Permanent Address">
              <Textarea
                className="min-h-[60px]"
                value={formData.sameAddress ? formData.present_address : formData.permanent_address}
                disabled={formData.sameAddress}
                onChange={(e) => updateForm('permanent_address', e.target.value)}
              />
            </FormField>
            <FormField label="Preferred Locations">
              <TagInput
                tags={formData.preferred_locations}
                onChange={(tags) => updateForm('preferred_locations', tags)}
                placeholder="Add locations..."
              />
            </FormField>
            <FormField label="Preferred Sectors">
              <TagInput
                tags={formData.preferred_sectors}
                onChange={(tags) => updateForm('preferred_sectors', tags)}
                placeholder="Add sectors..."
              />
            </FormField>
          </div>
        </section>

        <section>
          <h2 className="text-xl font-bold text-ink border-b pb-2 mb-4">Professional Info</h2>
          <div className="space-y-4">
            <FormField label="Strengths">
              <TagInput
                tags={formData.strengths}
                onChange={(tags) => updateForm('strengths', tags)}
              />
            </FormField>
            <FormField label="Weaknesses">
              <TagInput
                tags={formData.weaknesses}
                onChange={(tags) => updateForm('weaknesses', tags)}
              />
            </FormField>
            <FormField label="Annual Family Income">
              <Input
                placeholder="e.g. $50,000 - $80,000"
                value={formData.annual_family_income}
                onChange={(e) => updateForm('annual_family_income', e.target.value)}
              />
            </FormField>
          </div>
        </section>

        <div className="mt-8 pt-6 border-t border-border-soft flex items-center justify-between">
          <Button variant="ghost" onClick={() => router.back()} disabled={saving}>
            Cancel
          </Button>
          <div className="space-x-4">
            <Button variant="outline" onClick={handleSave} disabled={saving}>
              {saving ? 'Saving…' : 'Save as Draft'}
            </Button>
            <Button variant="primary" onClick={handleSave} disabled={saving}>
              {saving ? 'Saving…' : 'Save & Continue'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
