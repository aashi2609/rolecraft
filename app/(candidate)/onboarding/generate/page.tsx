"use client";

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/Button';
import { FormField } from '@/components/ui/FormField';
import { SearchableCombobox } from '@/components/ui/SearchableCombobox';

const VERTICALS = [
  'Software Engineer',
  'Data Analyst',
  'Product Manager',
  'UX Designer',
  'Marketing Specialist',
  'Sales Executive',
  'Financial Analyst',
  'HR Manager'
];

export default function GenerateResumePage() {
  const router = useRouter();
  const [vertical, setVertical] = useState("");
  const [generating, setGenerating] = useState(false);

  const handleGenerate = () => {
    if (!vertical) return;
    setGenerating(true);
    
    // Simulate API call for 2.5 seconds
    setTimeout(() => {
      // Store vertical in localStorage to simulate passing it to the dashboard
      localStorage.setItem('rolecraft_target_vertical', vertical);
      router.push('/onboarding/resume-preview');
    }, 2500);
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center py-10 px-4">
      <div className="w-full max-w-lg bg-white rounded-xl shadow-sm border border-slate-100 p-8 text-center">
        {!generating ? (
          <>
            <h2 className="text-2xl font-bold text-slate-900 mb-2">Almost there!</h2>
            <p className="text-slate-500 mb-8 text-sm">
              To build a tailored resume that gets past the ATS, we need to know what role you're targeting.
            </p>
            
            <div className="text-left mb-6">
              <FormField label="What role are you targeting?" required>
                <SearchableCombobox 
                  options={VERTICALS} 
                  value={vertical} 
                  onChange={setVertical} 
                  placeholder="e.g. Product Manager"
                />
              </FormField>
            </div>

            <Button className="w-full" onClick={handleGenerate} disabled={!vertical}>
              Generate Resume
            </Button>
          </>
        ) : (
          <div className="py-12 flex flex-col items-center justify-center">
            <div className="w-12 h-12 border-4 border-primary/30 border-t-primary rounded-full animate-spin mb-6"></div>
            <h2 className="text-xl font-bold text-slate-900 mb-2">Building your tailored resume...</h2>
            <p className="text-slate-500 text-sm">
              Our AI is analyzing your profile and formatting it perfectly for a {vertical} role.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
