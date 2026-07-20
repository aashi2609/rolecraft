"use client";

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/Button';
import { CheckCircle2, Download, FileText } from 'lucide-react';

export default function ResumePreviewPage() {
  const router = useRouter();
  const [vertical, setVertical] = useState("your targeted role");

  useEffect(() => {
    const stored = localStorage.getItem('rolecraft_target_vertical');
    if (stored) setVertical(stored);
  }, []);

  return (
    <div className="max-w-4xl mx-auto py-10 px-4">
      <div className="flex justify-between items-end mb-8">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 mb-2">Your Resume is Ready!</h1>
          <p className="text-slate-500">
            Perfectly tailored for <span className="font-medium text-slate-900">{vertical}</span> positions.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" className="gap-2">
            <Download className="w-4 h-4" /> Download PDF
          </Button>
          <Button onClick={() => router.push('/dashboard')}>
            Continue to Dashboard
          </Button>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="bg-slate-50 border-b border-slate-200 p-4 flex items-center justify-between">
          <div className="flex items-center gap-2 text-slate-700 font-medium">
            <FileText className="w-5 h-5 text-primary" />
            Jane_Doe_{vertical.replace(/\s+/g, '_')}_Resume.pdf
          </div>
          <div className="flex items-center gap-1.5 bg-green-50 text-green-700 px-3 py-1 rounded-full text-sm font-medium border border-green-200">
            <CheckCircle2 className="w-4 h-4" />
            87/100 — ATS Ready
          </div>
        </div>
        
        {/* Mock Resume Content */}
        <div className="p-12 aspect-[1/1.4] bg-white text-sm text-slate-600 font-serif leading-relaxed mx-auto max-w-3xl">
          <div className="text-center mb-8 border-b border-slate-200 pb-6">
            <h2 className="text-3xl font-bold text-slate-900 font-sans mb-2">Jane Doe</h2>
            <p>San Francisco, CA • (555) 123-4567 • jane.doe@example.com</p>
            <p className="text-primary font-medium mt-1">{vertical}</p>
          </div>
          
          <div className="mb-6">
            <h3 className="font-bold text-slate-900 uppercase tracking-wide mb-2">Professional Summary</h3>
            <p>
              Results-driven professional with expertise aligned to {vertical} requirements. 
              Proven track record of delivering high-quality outcomes, collaborating across cross-functional teams, 
              and leveraging modern tools to solve complex problems.
            </p>
          </div>

          <div className="mb-6">
            <h3 className="font-bold text-slate-900 uppercase tracking-wide mb-2">Experience</h3>
            <div className="mb-4">
              <div className="flex justify-between font-bold text-slate-800">
                <span>Senior Role • Tech Company</span>
                <span>2021 - Present</span>
              </div>
              <ul className="list-disc pl-5 mt-2 space-y-1">
                <li>Spearheaded initiatives that increased efficiency by 24% over 6 months.</li>
                <li>Collaborated closely with stakeholders to define project roadmaps.</li>
                <li>Mentored junior team members and established best practices.</li>
              </ul>
            </div>
          </div>

          <div className="mb-6">
            <h3 className="font-bold text-slate-900 uppercase tracking-wide mb-2">Education</h3>
            <div className="flex justify-between font-bold text-slate-800">
              <span>B.S. in Computer Science • Top University</span>
              <span>2017 - 2021</span>
            </div>
            <p>GPA: 3.8/4.0</p>
          </div>

        </div>
      </div>
    </div>
  );
}
