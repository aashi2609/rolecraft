"use client";

import React, { useEffect, useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Crown, ArrowRight, Sparkles, FileText, CheckCircle2, Briefcase, Bookmark, MessageSquare } from 'lucide-react';
import Link from 'next/link';
import { useUser } from '@/context/UserContext';

export default function CandidateDashboardPage() {
  const [vertical, setVertical] = useState("");
  const { applications, savedJobs, messages, jobs } = useUser();

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

        {/* Recent Activity Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mt-8">
          
          {/* Applications */}
          <Card className="p-6">
            <h3 className="font-bold text-slate-900 mb-4 flex items-center justify-between">
              Recent Applications
              <Link href="/jobs" className="text-xs text-primary hover:underline font-normal">Browse Jobs</Link>
            </h3>
            {applications.length === 0 ? (
              <div className="text-center py-8">
                <Briefcase className="w-10 h-10 text-slate-200 mx-auto mb-3" />
                <p className="text-sm text-slate-500 font-medium">No applications yet</p>
                <p className="text-xs text-slate-400 mt-1">Start applying to see your progress here.</p>
              </div>
            ) : (
              <div className="space-y-4">
                {applications.slice(0, 3).map(app => (
                  <div key={app.id} className="border-b border-slate-100 pb-3 last:border-0 last:pb-0">
                    <h4 className="font-bold text-slate-900 text-sm">{app.jobTitle}</h4>
                    <div className="flex justify-between items-center mt-1">
                      <span className="text-xs text-slate-500">{app.companyName}</span>
                      <span className="text-xs font-medium bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full">{app.status}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* Saved Jobs */}
          <Card className="p-6">
            <h3 className="font-bold text-slate-900 mb-4 flex items-center justify-between">
              Saved Jobs
              <Link href="/saved-jobs" className="text-xs text-primary hover:underline font-normal">View All</Link>
            </h3>
            {savedJobs.length === 0 ? (
              <div className="text-center py-8">
                <Bookmark className="w-10 h-10 text-slate-200 mx-auto mb-3" />
                <p className="text-sm text-slate-500 font-medium">No saved jobs</p>
                <p className="text-xs text-slate-400 mt-1">Bookmark jobs to apply later.</p>
              </div>
            ) : (
              <div className="space-y-4">
                {savedJobs.slice(0, 3).map(jobId => {
                  const job = jobs.find(j => j.id === jobId);
                  if (!job) return null;
                  return (
                    <div key={job.id} className="border-b border-slate-100 pb-3 last:border-0 last:pb-0">
                      <h4 className="font-bold text-slate-900 text-sm line-clamp-1">{job.title}</h4>
                      <div className="flex justify-between items-center mt-1">
                        <span className="text-xs text-slate-500">{job.companyName}</span>
                        <Link href={`/jobs/${job.id}`} className="text-xs text-primary hover:underline">Apply</Link>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </Card>

          {/* Messages */}
          <Card className="p-6">
            <h3 className="font-bold text-slate-900 mb-4 flex items-center justify-between">
              Recent Messages
              <Link href="/messages" className="text-xs text-primary hover:underline font-normal">Open Inbox</Link>
            </h3>
            {messages.length === 0 ? (
              <div className="text-center py-8">
                <MessageSquare className="w-10 h-10 text-slate-200 mx-auto mb-3" />
                <p className="text-sm text-slate-500 font-medium">No new messages</p>
                <p className="text-xs text-slate-400 mt-1">Employers will reach out here.</p>
              </div>
            ) : (
              <div className="space-y-4">
                 {messages.slice(0, 3).map(msg => (
                  <div key={msg.id} className="border-b border-slate-100 pb-3 last:border-0 last:pb-0">
                    <h4 className="font-bold text-slate-900 text-sm">{msg.sender}</h4>
                    <p className="text-xs text-slate-500 line-clamp-1 mt-0.5">{msg.text}</p>
                  </div>
                 ))}
              </div>
            )}
          </Card>
        </div>

      </div>
    </div>
  );
}
