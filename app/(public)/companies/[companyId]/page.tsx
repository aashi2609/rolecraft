"use client";

import React from 'react';
import { useUser } from '@/context/UserContext';
import { useParams, useRouter } from 'next/navigation';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { MapPin, Briefcase, Users, Link as LinkIcon } from 'lucide-react';
import Link from 'next/link';

export default function CompanyPublicProfilePage() {
  const { companyId } = useParams();
  const { jobs } = useUser();
  const router = useRouter();

  // Mock company details based on the jobs we have
  const companyJobs = jobs.filter(j => j.companyId === Number(companyId) && j.status === 'Live');
  
  if (companyJobs.length === 0) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center text-slate-500">
        Company not found or has no active listings.
      </div>
    );
  }

  const company = {
    id: companyId,
    name: companyJobs[0].companyName,
    industry: 'Technology / IT Services',
    size: '51-200 employees',
    hq: companyJobs[0].location || 'Bengaluru',
    website: 'https://example.com',
    about: 'We are a leading technology company dedicated to building innovative products and fostering a culture of continuous learning. Our mission is to empower developers worldwide with cutting-edge tools.'
  };

  return (
    <div className="min-h-screen bg-slate-50 py-10">
      <div className="max-w-4xl mx-auto px-4">
        
        <button onClick={() => router.back()} className="text-sm text-slate-500 hover:text-primary mb-6 inline-block">
          ← Back
        </button>

        {/* Header */}
        <Card className="p-8 mb-8">
          <div className="flex flex-col md:flex-row gap-6 items-start">
            <div className="w-24 h-24 bg-slate-100 rounded-2xl flex items-center justify-center text-4xl font-bold text-slate-600 shrink-0 shadow-sm border border-slate-200">
              {company.name.charAt(0)}
            </div>
            <div className="flex-1">
              <h1 className="text-3xl font-bold text-slate-900 mb-2">{company.name}</h1>
              <div className="flex flex-wrap gap-4 text-sm text-slate-600 mb-4">
                <div className="flex items-center gap-1"><MapPin className="w-4 h-4" /> {company.hq}</div>
                <div className="flex items-center gap-1"><Briefcase className="w-4 h-4" /> {company.industry}</div>
                <div className="flex items-center gap-1"><Users className="w-4 h-4" /> {company.size}</div>
                <a href={company.website} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-primary hover:underline">
                  <LinkIcon className="w-4 h-4" /> Website
                </a>
              </div>
            </div>
          </div>
        </Card>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Main Column */}
          <div className="md:col-span-2 space-y-8">
            <Card className="p-8">
              <h2 className="text-xl font-bold text-slate-900 mb-4">About Us</h2>
              <div className="prose text-slate-600 max-w-none">
                <p>{company.about}</p>
              </div>
            </Card>

            <div>
              <h2 className="text-xl font-bold text-slate-900 mb-4">Open Positions ({companyJobs.length})</h2>
              <div className="space-y-4">
                {companyJobs.map(job => (
                  <Card key={job.id} className="p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:border-primary transition-colors">
                    <div>
                      <h3 className="font-bold text-slate-900">{job.title}</h3>
                      <div className="flex items-center gap-3 text-sm text-slate-500 mt-2">
                        <span className="flex items-center gap-1"><MapPin className="w-3 h-3" /> {job.location}</span>
                        <span className="flex items-center gap-1"><Briefcase className="w-3 h-3" /> {job.employmentType}</span>
                      </div>
                    </div>
                    <Link href={`/jobs/${job.id}`}>
                      <Button variant="outline">View Job</Button>
                    </Link>
                  </Card>
                ))}
              </div>
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-8">
            <Card className="p-6 bg-primary text-white border-primary">
              <h3 className="font-bold mb-2">Want to join {company.name}?</h3>
              <p className="text-sm text-primary-foreground/80 mb-4">
                Create a tailored AI resume specifically optimized for their open roles.
              </p>
              <Link href="/onboarding/generate?skipProfile=true">
                <Button variant="secondary" className="w-full text-primary bg-white hover:bg-slate-100">
                  Generate Tailored Resume
                </Button>
              </Link>
            </Card>
          </div>
        </div>

      </div>
    </div>
  );
}
