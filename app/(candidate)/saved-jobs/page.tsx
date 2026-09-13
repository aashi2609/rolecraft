"use client";

import React, { useState } from 'react';
import { useUser } from '@/context/UserContext';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Bookmark, MapPin, Briefcase, BookmarkCheck, Eye, EyeOff } from 'lucide-react';
import Link from 'next/link';

export default function SavedJobsPage() {
  const { jobs, savedJobs, toggleSavedJob, hiddenJobIds, unhideJob } = useUser();
  const [activeTab, setActiveTab] = useState<'saved' | 'hidden'>('saved');

  const savedJobsData = jobs.filter(job => savedJobs.includes(job.id));
  const hiddenJobsData = jobs.filter(job => hiddenJobIds.includes(String(job.id)));

  return (
    <div className="min-h-screen bg-surface-soft py-10">
      <div className="max-w-6xl mx-auto px-4">
        
        <div className="mb-6 flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-ink mb-2">My Jobs</h1>
            <p className="text-ink-muted">Manage the roles you are tracking or have hidden.</p>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-border mb-8">
          <button
            onClick={() => setActiveTab('saved')}
            className={`pb-3 px-4 font-semibold text-sm transition-colors ${
              activeTab === 'saved'
                ? 'border-b-2 border-primary text-primary'
                : 'text-ink-muted hover:text-ink'
            }`}
          >
            Saved Jobs ({savedJobsData.length})
          </button>
          <button
            onClick={() => setActiveTab('hidden')}
            className={`pb-3 px-4 font-semibold text-sm transition-colors ${
              activeTab === 'hidden'
                ? 'border-b-2 border-primary text-primary'
                : 'text-ink-muted hover:text-ink'
            }`}
          >
            Hidden Jobs ({hiddenJobsData.length})
          </button>
        </div>

        {/* Saved Jobs Tab */}
        {activeTab === 'saved' && (
          <>
            {savedJobsData.length === 0 ? (
              <Card className="text-center py-20 border-dashed">
                <Bookmark className="w-16 h-16 text-ink-muted/40 mx-auto mb-4" />
                <h3 className="text-xl font-bold text-ink mb-2">You haven&apos;t saved any jobs yet</h3>
                <p className="text-ink-muted mb-6 max-w-md mx-auto">
                  When you see a job you like, click the bookmark icon to save it for later.
                </p>
                <Link href="/jobs">
                  <Button>Browse Jobs</Button>
                </Link>
              </Card>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {savedJobsData.map(job => (
                  <Card key={job.id} className="p-6 flex flex-col hover:border-primary transition-colors cursor-pointer group">
                    <div className="flex justify-between items-start mb-4">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-surface-soft rounded-lg flex items-center justify-center font-bold text-ink-muted">
                          {job.companyName.charAt(0)}
                        </div>
                        <div>
                          <h3 className="font-bold text-ink line-clamp-1">{job.title}</h3>
                          <Link href={`/companies/${job.companyId}`} className="text-sm text-primary hover:underline" onClick={e => e.stopPropagation()}>
                            {job.companyName}
                          </Link>
                        </div>
                      </div>
                      <button 
                        className="text-ink-muted hover:text-primary transition-colors"
                        title="Unsave Job"
                        onClick={(e) => { e.stopPropagation(); toggleSavedJob(job.id); }}
                      >
                        <BookmarkCheck className="w-5 h-5 text-primary" />
                      </button>
                    </div>
                    
                    <div className="flex items-center gap-4 text-xs text-ink-muted mb-4">
                      <div className="flex items-center gap-1"><MapPin className="w-3 h-3" /> {job.location}</div>
                      <div className="flex items-center gap-1"><Briefcase className="w-3 h-3" /> {job.employmentType}</div>
                    </div>
                    
                    <p className="text-sm text-ink-muted line-clamp-2 mb-6 flex-1">
                      {job.description}
                    </p>
                    
                    <Link href={`/jobs/${job.id}`} className="mt-auto block">
                      <Button variant="outline" className="w-full group-hover:bg-primary group-hover:text-white transition-colors">
                        View Job
                      </Button>
                    </Link>
                  </Card>
                ))}
              </div>
            )}
          </>
        )}

        {/* Hidden Jobs Tab */}
        {activeTab === 'hidden' && (
          <>
            {hiddenJobsData.length === 0 ? (
              <Card className="text-center py-20 border-dashed">
                <EyeOff className="w-16 h-16 text-ink-muted/40 mx-auto mb-4" />
                <h3 className="text-xl font-bold text-ink mb-2">No Hidden Jobs</h3>
                <p className="text-ink-muted mb-6 max-w-md mx-auto">
                  Jobs you hide from search results will appear here.
                </p>
                <Link href="/jobs">
                  <Button>Browse Jobs</Button>
                </Link>
              </Card>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {hiddenJobsData.map(job => (
                  <Card key={job.id} className="p-6 flex flex-col hover:border-primary transition-colors cursor-pointer group">
                    <div className="flex justify-between items-start mb-4">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-surface-soft rounded-lg flex items-center justify-center font-bold text-ink-muted">
                          {job.companyName.charAt(0)}
                        </div>
                        <div>
                          <h3 className="font-bold text-ink line-clamp-1">{job.title}</h3>
                          <span className="text-sm text-ink-muted">
                            {job.companyName}
                          </span>
                        </div>
                      </div>
                      <button 
                        className="text-ink-muted hover:text-primary transition-colors flex items-center gap-1"
                        title="Unhide Job"
                        onClick={(e) => { e.stopPropagation(); unhideJob(job.id); }}
                      >
                        <Eye className="w-5 h-5" />
                      </button>
                    </div>
                    
                    <div className="flex items-center gap-4 text-xs text-ink-muted mb-4">
                      <div className="flex items-center gap-1"><MapPin className="w-3 h-3" /> {job.location}</div>
                      <div className="flex items-center gap-1"><Briefcase className="w-3 h-3" /> {job.employmentType}</div>
                    </div>
                    
                    <p className="text-sm text-ink-muted line-clamp-2 mb-6 flex-1">
                      {job.description}
                    </p>
                    
                    <Button 
                      variant="outline" 
                      className="mt-auto w-full group-hover:bg-primary group-hover:text-white transition-colors"
                      onClick={(e) => { e.stopPropagation(); unhideJob(job.id); }}
                    >
                      Unhide Job
                    </Button>
                  </Card>
                ))}
              </div>
            )}
          </>
        )}

      </div>
    </div>
  );
}
