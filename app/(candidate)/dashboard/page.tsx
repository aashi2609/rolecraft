"use client";

import React, { useEffect, useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Crown, ArrowRight, Sparkles, FileText, CheckCircle2 } from 'lucide-react';
import Link from 'next/link';

export default function CandidateDashboardPage() {
  const [vertical, setVertical] = useState("");

  useEffect(() => {
    const stored = localStorage.getItem('rolecraft_target_vertical');
    if (stored) setVertical(stored);
  }, []);

  return (
    <div className="min-h-screen bg-slate-50 py-8">
      <div className="max-w-6xl mx-auto px-4 space-y-8">
        
        {/* Welcome Header */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <h1 className="text-3xl font-bold text-slate-900">Welcome back, Jane! 👋</h1>
            <p className="text-slate-500 mt-1">Here is what's happening with your job search today.</p>
          </div>
          <Link href="/profile/personal-details">
            <Button variant="outline">Edit Profile</Button>
          </Link>
        </div>

        {/* Hero Area / Resume Card */}
        <Card className="bg-white p-0 overflow-hidden border-0 shadow-md">
          {vertical ? (
            <div className="flex flex-col md:flex-row p-8">
              <div className="flex-1">
                <h2 className="text-2xl font-bold text-slate-900 mb-2">Your Resume</h2>
                <p className="text-slate-600 mb-6">Targeting: <span className="font-semibold text-primary">{vertical}</span></p>
                
                <div className="flex items-center gap-4 p-4 border border-slate-200 rounded-lg bg-slate-50 w-fit">
                  <div className="p-3 bg-white rounded-md shadow-sm border border-slate-100">
                    <FileText className="w-8 h-8 text-primary" />
                  </div>
                  <div>
                    <div className="font-semibold text-slate-900">Jane_Doe_{vertical.replace(/\s+/g, '_')}_Resume.pdf</div>
                    <div className="flex items-center gap-1.5 text-sm text-green-700 font-medium mt-1">
                      <CheckCircle2 className="w-4 h-4" />
                      87/100 — ATS Ready
                    </div>
                  </div>
                </div>

                <div className="mt-8 flex gap-3">
                  <Button variant="primary">Apply to Jobs</Button>
                  <Button variant="outline">Download PDF</Button>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex flex-col md:flex-row">
              <div className="p-8 md:p-12 flex-1 flex flex-col justify-center">
                <div className="inline-flex items-center gap-2 px-3 py-1 bg-blue-50 text-blue-700 text-sm font-bold rounded-full w-fit mb-4">
                  <Sparkles className="w-4 h-4" /> Profile Completeness: 85%
                </div>
                <h2 className="text-2xl md:text-3xl font-bold text-slate-900 mb-4">
                  Stand out to top employers
                </h2>
                <p className="text-slate-600 mb-8 max-w-md">
                  Complete the remaining sections of your profile to increase your visibility by up to 3x and get matched with better roles.
                </p>
                <Link href="/onboarding/profile">
                  <Button variant="primary" className="w-fit">
                    Complete Profile <ArrowRight className="w-4 h-4 ml-2" />
                  </Button>
                </Link>
              </div>
              <div className="bg-blue-50 hidden md:flex items-center justify-center p-12 w-1/3">
                {/* Placeholder for Hero Illustration */}
                <div className="text-blue-300 text-center">
                  <div className="w-48 h-48 rounded-full bg-blue-100 mx-auto mb-4 border-8 border-white shadow-sm"></div>
                  <span className="font-semibold text-sm tracking-widest uppercase">Illustration</span>
                </div>
              </div>
            </div>
          )}
        </Card>

        {/* Premium Upsell Banner */}
        <Card className="bg-gradient-to-r from-slate-900 to-slate-800 text-white border-0">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex items-start gap-4">
              <div className="p-3 bg-yellow-500/20 rounded-xl text-yellow-500">
                <Crown className="w-8 h-8" />
              </div>
              <div>
                <h3 className="text-xl font-bold mb-1">Upgrade to Elite</h3>
                <p className="text-slate-300 max-w-xl">
                  Get priority placement in company searches, see who viewed your profile, and access AI-powered resume tailoring.
                </p>
              </div>
            </div>
            <Link href="/pricing" className="shrink-0 w-full md:w-auto">
              <Button className="w-full bg-yellow-500 text-slate-900 hover:bg-yellow-400 focus:ring-yellow-500">
                View Plans
              </Button>
            </Link>
          </div>
        </Card>

      </div>
    </div>
  );
}
