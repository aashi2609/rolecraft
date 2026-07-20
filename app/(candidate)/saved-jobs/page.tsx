"use client";

import React from 'react';
import { useUser } from '@/context/UserContext';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Bookmark, MapPin, Briefcase, BookmarkCheck } from 'lucide-react';
import Link from 'next/link';

export default function SavedJobsPage() {
  const { jobs, savedJobs, toggleSavedJob } = useUser();

  const savedJobsData = jobs.filter(job => savedJobs.includes(job.id));

  return (
    <div className="min-h-screen bg-slate-50 py-10">
      <div className="max-w-6xl mx-auto px-4">
        
        <div className="mb-8 flex justify-between items-end">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 mb-2">Saved Jobs</h1>
            <p className="text-slate-500">Keep track of the roles you're interested in applying for.</p>
          </div>
          <div className="text-slate-500 font-medium">
            {savedJobsData.length} Saved
          </div>
        </div>

        {savedJobsData.length === 0 ? (
          <Card className="text-center py-20 border-dashed">
            <Bookmark className="w-16 h-16 text-slate-300 mx-auto mb-4" />
            <h3 className="text-xl font-bold text-slate-900 mb-2">You haven't saved any jobs yet</h3>
            <p className="text-slate-500 mb-6 max-w-md mx-auto">
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
                    <div className="w-10 h-10 bg-slate-100 rounded-lg flex items-center justify-center font-bold text-slate-600">
                      {job.companyName.charAt(0)}
                    </div>
                    <div>
                      <h3 className="font-bold text-slate-900 line-clamp-1">{job.title}</h3>
                      <Link href={`/companies/${job.companyId}`} className="text-sm text-primary hover:underline" onClick={e => e.stopPropagation()}>
                        {job.companyName}
                      </Link>
                    </div>
                  </div>
                  <button 
                    className="text-slate-400 hover:text-primary transition-colors"
                    onClick={(e) => { e.stopPropagation(); toggleSavedJob(job.id); }}
                  >
                    <BookmarkCheck className="w-5 h-5 text-primary" />
                  </button>
                </div>
                
                <div className="flex items-center gap-4 text-xs text-slate-500 mb-4">
                  <div className="flex items-center gap-1"><MapPin className="w-3 h-3" /> {job.location}</div>
                  <div className="flex items-center gap-1"><Briefcase className="w-3 h-3" /> {job.employmentType}</div>
                </div>
                
                <p className="text-sm text-slate-600 line-clamp-2 mb-6 flex-1">
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

      </div>
    </div>
  );
}
