"use client";

import React, { useState } from 'react';
import { useUser } from '@/context/UserContext';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { SearchableCombobox } from '@/components/ui/SearchableCombobox';
import { Search, MapPin, Briefcase, Bookmark, BookmarkCheck } from 'lucide-react';
import Link from 'next/link';
import { Input } from '@/components/ui/FormField';

const CITIES = ['Bengaluru', 'Mumbai', 'New Delhi', 'Hyderabad', 'Pune', 'Chennai', 'Gurugram', 'Noida', 'Kolkata', 'Ahmedabad', 'Remote', 'Hybrid'];
const VERTICALS = ['Frontend', 'Backend', 'Fullstack', 'DevOps', 'Data Science', 'Product Management'];

export default function JobBrowsePage() {
  const { jobs, savedJobs, toggleSavedJob } = useUser();
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedVertical, setSelectedVertical] = useState('');
  const [selectedLocation, setSelectedLocation] = useState('');
  const [selectedType, setSelectedType] = useState('');

  const liveJobs = jobs.filter(job => job.status === 'Live');

  const filteredJobs = liveJobs.filter(job => {
    const matchesSearch = job.title.toLowerCase().includes(searchTerm.toLowerCase()) || job.companyName.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesVertical = selectedVertical ? job.vertical === selectedVertical : true;
    const matchesLocation = selectedLocation ? job.location === selectedLocation : true;
    const matchesType = selectedType ? job.employmentType === selectedType : true;
    return matchesSearch && matchesVertical && matchesLocation && matchesType;
  });

  return (
    <div className="min-h-screen bg-slate-50 py-10">
      <div className="max-w-6xl mx-auto px-4">
        
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-slate-900 mb-2">Browse Jobs</h1>
          <p className="text-slate-500">Find and apply to the best roles matching your skills.</p>
        </div>

        {/* Filters */}
        <div className="bg-white p-4 rounded-xl shadow-sm border border-slate-200 mb-8 grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="relative">
            <Search className="absolute left-3 top-2.5 h-5 w-5 text-slate-400" />
            <Input 
              placeholder="Search jobs or companies" 
              className="pl-10" 
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
            />
          </div>
          <div>
            <select 
              className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-primary text-slate-900"
              value={selectedVertical}
              onChange={e => setSelectedVertical(e.target.value)}
            >
              <option value="">All Verticals</option>
              {VERTICALS.map(v => <option key={v} value={v}>{v}</option>)}
            </select>
          </div>
          <div>
            <SearchableCombobox 
              options={CITIES} 
              value={selectedLocation} 
              onChange={setSelectedLocation} 
              placeholder="Location" 
            />
          </div>
          <div>
            <select 
              className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-primary text-slate-900"
              value={selectedType}
              onChange={e => setSelectedType(e.target.value)}
            >
              <option value="">All Types</option>
              <option value="Full-time">Full-time</option>
              <option value="Part-time">Part-time</option>
              <option value="Contract">Contract</option>
              <option value="Internship">Internship</option>
            </select>
          </div>
        </div>

        {/* Job Grid */}
        {filteredJobs.length === 0 ? (
          <div className="text-center py-20 bg-white rounded-xl border border-slate-200 shadow-sm">
            <Briefcase className="w-12 h-12 text-slate-300 mx-auto mb-4" />
            <h3 className="text-xl font-bold text-slate-900 mb-2">No jobs found</h3>
            <p className="text-slate-500">No jobs match your filters — try broadening your search.</p>
            <Button variant="outline" className="mt-4" onClick={() => {
              setSearchTerm(''); setSelectedVertical(''); setSelectedLocation(''); setSelectedType('');
            }}>
              Clear Filters
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredJobs.map(job => (
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
                    {savedJobs.includes(job.id) ? <BookmarkCheck className="w-5 h-5 text-primary" /> : <Bookmark className="w-5 h-5" />}
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
