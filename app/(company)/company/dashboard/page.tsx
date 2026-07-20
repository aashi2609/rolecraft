"use client";

import React, { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { FormField, Input, Textarea } from '@/components/ui/FormField';
import { TagInput } from '@/components/ui/TagInput';
import { Search, Eye, Bookmark, TrendingUp } from 'lucide-react';

export default function CompanyDashboardPage() {
  const [jobPosting, setJobPosting] = useState<{
    title: string;
    vertical: string;
    experience: string;
    skills: string[];
  }>({
    title: '',
    vertical: '',
    experience: '',
    skills: []
  });

  const [activeTab, setActiveTab] = useState('post');

  const candidates = [
    { name: 'John Doe', fitment: '95%', rationale: 'Matches 4/5 must-have skills and exact experience range.', vertical: 'Frontend', badgeColor: 'bg-green-100 text-green-700' },
    { name: 'Sarah Jenkins', fitment: '88%', rationale: 'Excellent skills, slightly more experienced than requested.', vertical: 'Frontend', badgeColor: 'bg-green-100 text-green-700' },
    { name: 'Michael Chen', fitment: '75%', rationale: 'Missing React experience but strong fundamentals.', vertical: 'Frontend', badgeColor: 'bg-yellow-100 text-yellow-700' },
    { name: 'Emily Davis', fitment: '40%', rationale: 'Backend focused, missing key frontend skills.', vertical: 'Backend', badgeColor: 'bg-red-100 text-red-700' },
  ];

  const handlePostJob = () => {
    console.log('Job Posted:', jobPosting);
    alert('Job posted successfully! Candidates are being ranked.');
    setActiveTab('candidates');
  };

  return (
    <div className="min-h-screen bg-slate-50 py-10">
      <div className="max-w-6xl mx-auto px-4">
        
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold text-slate-900">Employer Dashboard</h1>
          <div className="flex bg-slate-200 p-1 rounded-xl">
            <button 
              className={`px-4 py-2 text-sm font-semibold rounded-lg transition-colors ${activeTab === 'post' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
              onClick={() => setActiveTab('post')}
            >
              Post a Job
            </button>
            <button 
              className={`px-4 py-2 text-sm font-semibold rounded-lg transition-colors ${activeTab === 'candidates' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
              onClick={() => setActiveTab('candidates')}
            >
              Ranked Candidates
            </button>
          </div>
        </div>

        {activeTab === 'post' && (
          <Card className="max-w-3xl mx-auto p-8">
            <h2 className="text-xl font-bold text-slate-900 mb-6 border-b pb-2">Create New Job Posting</h2>
            
            <div className="space-y-6">
              <FormField label="Job Title" required>
                <Input 
                  placeholder="e.g. Senior Frontend Engineer" 
                  value={jobPosting.title}
                  onChange={e => setJobPosting({...jobPosting, title: e.target.value})}
                />
              </FormField>

              <div className="grid grid-cols-2 gap-6">
                <FormField label="Vertical" required>
                  <select 
                    className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-primary text-slate-900"
                    value={jobPosting.vertical}
                    onChange={e => setJobPosting({...jobPosting, vertical: e.target.value})}
                  >
                    <option value="">Select Vertical</option>
                    <option value="Frontend">Frontend</option>
                    <option value="Backend">Backend</option>
                    <option value="Fullstack">Fullstack</option>
                    <option value="DevOps">DevOps</option>
                  </select>
                </FormField>
                <FormField label="Experience Range" required>
                  <Input 
                    placeholder="e.g. 3-5 Years" 
                    value={jobPosting.experience}
                    onChange={e => setJobPosting({...jobPosting, experience: e.target.value})}
                  />
                </FormField>
              </div>

              <FormField label="Must-have Skills" required>
                <TagInput 
                  tags={jobPosting.skills} 
                  onChange={tags => setJobPosting({...jobPosting, skills: tags})} 
                  placeholder="Type a skill and press Enter" 
                />
              </FormField>

              <div className="pt-4 flex justify-end">
                <Button variant="primary" size="lg" onClick={handlePostJob}>
                  Post Job & Find Matches
                </Button>
              </div>
            </div>
          </Card>
        )}

        {activeTab === 'candidates' && (
          <Card className="p-0 overflow-hidden">
            <div className="p-6 border-b border-slate-200 flex justify-between items-center bg-white">
              <div>
                <h2 className="text-xl font-bold text-slate-900">Ranked Candidates</h2>
                <p className="text-sm text-slate-500 mt-1">Showing AI-matched candidates for "Senior Frontend Engineer"</p>
              </div>
              <div className="relative">
                <Search className="w-5 h-5 absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" />
                <Input className="pl-10 w-64" placeholder="Search candidates..." />
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-600">
                <thead className="bg-slate-50 text-slate-700 font-semibold border-b border-slate-200">
                  <tr>
                    <th className="p-4 w-1/4">Candidate Name</th>
                    <th className="p-4 w-32">Fitment Score</th>
                    <th className="p-4">AI Rationale</th>
                    <th className="p-4 w-32 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {candidates.map((candidate, i) => (
                    <tr key={i} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                      <td className="p-4 font-medium text-slate-900">
                        {candidate.name}
                        <div className="text-xs text-slate-500 font-normal">{candidate.vertical}</div>
                      </td>
                      <td className="p-4">
                        <span className={`inline-flex items-center justify-center px-2.5 py-1 text-xs font-bold rounded-full ${candidate.badgeColor}`}>
                          <TrendingUp className="w-3 h-3 mr-1" /> {candidate.fitment}
                        </span>
                      </td>
                      <td className="p-4 text-slate-500">
                        {candidate.rationale}
                      </td>
                      <td className="p-4 text-right space-x-2">
                        <button className="p-2 text-slate-400 hover:text-primary hover:bg-blue-50 rounded-lg transition-colors" title="View Resume">
                          <Eye className="w-5 h-5" />
                        </button>
                        <button className="p-2 text-slate-400 hover:text-primary hover:bg-blue-50 rounded-lg transition-colors" title="Shortlist">
                          <Bookmark className="w-5 h-5" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )}

      </div>
    </div>
  );
}
