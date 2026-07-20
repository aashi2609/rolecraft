"use client";

import React, { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { FormField, Input, Textarea } from '@/components/ui/FormField';
import { SearchableCombobox } from '@/components/ui/SearchableCombobox';
import { Search, Eye, Bookmark, TrendingUp, CheckCircle2, MessageCircle, MoreVertical, Briefcase, Users, Check } from 'lucide-react';
import { CandidateProfileModal } from '@/components/company/CandidateProfileModal';
import { MessageModal } from '@/components/company/MessageModal';
import Link from 'next/link';
import { useUser } from '@/context/UserContext';

const TECH_SKILLS = ['Python', 'Java', 'JavaScript', 'TypeScript', 'C++', 'Go', 'Rust', 'React', 'Next.js', 'Vue', 'Angular', 'Tailwind CSS', 'Node.js', 'FastAPI', 'Django', 'Spring Boot', 'Express', 'PostgreSQL', 'MongoDB', 'MySQL', 'Redis', 'AWS', 'GCP', 'Azure', 'Docker', 'Kubernetes', 'Terraform', 'LangChain', 'LangGraph', 'TensorFlow', 'PyTorch', 'Gemini API', 'OpenAI API', 'Git', 'Figma', 'Jira', 'Postman', 'Communication', 'Leadership', 'Problem Solving', 'Teamwork'];
const CITIES = ['Bengaluru', 'Mumbai', 'New Delhi', 'Hyderabad', 'Pune', 'Chennai', 'Gurugram', 'Noida', 'Kolkata', 'Ahmedabad', 'Remote', 'Hybrid'];

export default function CompanyDashboardPage() {
  const { plan } = useUser();
  const [activeTab, setActiveTab] = useState('overview');
  
  // Modals state
  const [selectedCandidate, setSelectedCandidate] = useState<any>(null);
  const [isProfileModalOpen, setIsProfileModalOpen] = useState(false);
  const [isMessageModalOpen, setIsMessageModalOpen] = useState(false);
  const [candidateToMessage, setCandidateToMessage] = useState('');

  // Processing state
  const [isPosting, setIsPosting] = useState(false);

  // Job Posting Form
  const [jobPosting, setJobPosting] = useState({
    id: null as number | null,
    title: '',
    vertical: '',
    experience: '',
    skills: [] as string[],
    description: '',
    location: '',
    employmentType: '',
    salaryMin: '',
    salaryMax: '',
    salaryUndisclosed: false
  });

  // Mock Data
  const [jobs, setJobs] = useState<any[]>([
    { id: 1, title: 'Senior Frontend Engineer', vertical: 'Frontend', status: 'Live', matched: 24, shortlisted: 3, date: '2026-07-15' },
    { id: 2, title: 'Backend Developer', vertical: 'Backend', status: 'Draft', matched: 0, shortlisted: 0, date: '2026-07-18' }
  ]);
  const [selectedJobId, setSelectedJobId] = useState<number>(1);
  const [showShortlistedOnly, setShowShortlistedOnly] = useState(false);

  const [candidates, setCandidates] = useState([
    { id: 101, jobId: 1, name: 'John Doe', fitment: '95%', rationale: 'Matches 4/5 must-have skills and exact experience range.', vertical: 'Frontend', badgeColor: 'bg-green-100 text-green-700', isShortlisted: false },
    { id: 102, jobId: 1, name: 'Sarah Jenkins', fitment: '88%', rationale: 'Excellent skills, slightly more experienced than requested.', vertical: 'Frontend', badgeColor: 'bg-green-100 text-green-700', isShortlisted: true },
    { id: 103, jobId: 1, name: 'Michael Chen', fitment: '75%', rationale: 'Missing React experience but strong fundamentals.', vertical: 'Frontend', badgeColor: 'bg-yellow-100 text-yellow-700', isShortlisted: false },
    { id: 104, jobId: 1, name: 'Emily Davis', fitment: '40%', rationale: 'Backend focused, missing key frontend skills.', vertical: 'Backend', badgeColor: 'bg-red-100 text-red-700', isShortlisted: false },
  ]);

  const filteredCandidates = candidates
    .filter(c => c.jobId === selectedJobId)
    .filter(c => showShortlistedOnly ? c.isShortlisted : true);

  const handlePostJob = () => {
    // Validate
    if (!jobPosting.title || !jobPosting.vertical || !jobPosting.experience || jobPosting.skills.length === 0 || !jobPosting.description || !jobPosting.location || !jobPosting.employmentType) {
      alert("Please fill in all required fields.");
      return;
    }
    
    setIsPosting(true);
    
    setTimeout(() => {
      if (jobPosting.id) {
        setJobs(jobs.map(j => j.id === jobPosting.id ? {
          ...j,
          title: jobPosting.title,
          vertical: jobPosting.vertical
        } : j));
      } else {
        const newJobId = Date.now();
        setJobs([{
          id: newJobId,
          title: jobPosting.title,
          vertical: jobPosting.vertical,
          status: 'Live',
          matched: 0,
          shortlisted: 0,
          date: new Date().toISOString().split('T')[0]
        }, ...jobs]);
        setSelectedJobId(newJobId);
      }
      
      setIsPosting(false);
      
      // Reset form
      setJobPosting({
        id: null, title: '', vertical: '', experience: '', skills: [], description: '', location: '', employmentType: '', salaryMin: '', salaryMax: '', salaryUndisclosed: false
      });
      
      setActiveTab('my-postings');
    }, 1500);
  };

  const toggleShortlist = (candidateId: number) => {
    setCandidates(candidates.map(c => 
      c.id === candidateId ? { ...c, isShortlisted: !c.isShortlisted } : c
    ));
  };

  const openProfile = (candidate: any) => {
    setSelectedCandidate(candidate);
    setIsProfileModalOpen(true);
  };

  const openMessage = (name: string) => {
    setCandidateToMessage(name);
    setIsMessageModalOpen(true);
  };

  return (
    <div className="min-h-[90vh] bg-slate-50 py-10">
      <div className="max-w-6xl mx-auto px-4">
        
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4">
          <h1 className="text-3xl font-bold text-slate-900">Employer Dashboard</h1>
          <div className="flex bg-slate-200 p-1 rounded-xl overflow-x-auto max-w-full hide-scrollbar">
            {['overview', 'post', 'my-postings', 'candidates'].map((tab) => (
              <button 
                key={tab}
                className={`px-4 py-2 text-sm font-semibold rounded-lg transition-colors whitespace-nowrap ${activeTab === tab ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
                onClick={() => setActiveTab(tab)}
              >
                {tab === 'overview' && 'Overview'}
                {tab === 'post' && 'Post a Job'}
                {tab === 'my-postings' && 'My Postings'}
                {tab === 'candidates' && 'Ranked Candidates'}
              </button>
            ))}
          </div>
        </div>

        {/* OVERVIEW TAB */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {jobs.length === 0 ? (
              <Card className="text-center py-16">
                <Briefcase className="w-12 h-12 text-slate-300 mx-auto mb-4" />
                <h3 className="text-xl font-bold text-slate-900 mb-2">Welcome to RoleCraft!</h3>
                <p className="text-slate-500 mb-6 max-w-md mx-auto">Post your first job to start finding and ranking top candidates instantly.</p>
                <Button onClick={() => setActiveTab('post')}>Post your first job</Button>
              </Card>
            ) : (
              <>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <Card className="flex items-center p-6 gap-4">
                    <div className="p-4 bg-blue-50 text-primary rounded-full">
                      <Briefcase className="w-6 h-6" />
                    </div>
                    <div>
                      <div className="text-3xl font-bold text-slate-900">{jobs.filter(j => j.status === 'Live').length}</div>
                      <div className="text-sm text-slate-500 font-medium">Active Postings</div>
                    </div>
                  </Card>
                  <Card className="flex items-center p-6 gap-4">
                    <div className="p-4 bg-green-50 text-green-600 rounded-full">
                      <Users className="w-6 h-6" />
                    </div>
                    <div>
                      <div className="text-3xl font-bold text-slate-900">{candidates.length}</div>
                      <div className="text-sm text-slate-500 font-medium">Total Matches</div>
                    </div>
                  </Card>
                  <Card className="flex items-center p-6 gap-4">
                    <div className="p-4 bg-purple-50 text-purple-600 rounded-full">
                      <Bookmark className="w-6 h-6" />
                    </div>
                    <div>
                      <div className="text-3xl font-bold text-slate-900">{candidates.filter(c => c.isShortlisted).length}</div>
                      <div className="text-sm text-slate-500 font-medium">Shortlisted</div>
                    </div>
                  </Card>
                </div>

                <Card className="p-6">
                  <h3 className="font-bold text-slate-900 text-lg mb-4 border-b border-slate-100 pb-2">Recent Activity</h3>
                  <div className="space-y-4">
                    <div className="flex gap-4 items-start">
                      <div className="w-2 h-2 mt-2 rounded-full bg-primary shrink-0"></div>
                      <div>
                        <p className="text-slate-800 text-sm"><span className="font-semibold">Sarah Jenkins</span> was shortlisted for <span className="font-semibold">Senior Frontend Engineer</span></p>
                        <p className="text-xs text-slate-400">2 hours ago</p>
                      </div>
                    </div>
                    <div className="flex gap-4 items-start">
                      <div className="w-2 h-2 mt-2 rounded-full bg-slate-300 shrink-0"></div>
                      <div>
                        <p className="text-slate-800 text-sm">New match found: <span className="font-semibold">John Doe</span> (95% fit)</p>
                        <p className="text-xs text-slate-400">5 hours ago</p>
                      </div>
                    </div>
                    <div className="flex gap-4 items-start">
                      <div className="w-2 h-2 mt-2 rounded-full bg-slate-300 shrink-0"></div>
                      <div>
                        <p className="text-slate-800 text-sm">Job posted: <span className="font-semibold">Backend Developer</span></p>
                        <p className="text-xs text-slate-400">1 day ago</p>
                      </div>
                    </div>
                  </div>
                </Card>
              </>
            )}
          </div>
        )}

        {/* POST A JOB TAB */}
        {activeTab === 'post' && (
          <Card className="max-w-3xl mx-auto p-8 relative overflow-hidden">
            {isPosting ? (
              <div className="absolute inset-0 z-10 bg-white/80 backdrop-blur-sm flex flex-col items-center justify-center">
                <div className="w-12 h-12 border-4 border-primary/30 border-t-primary rounded-full animate-spin mb-4"></div>
                <h3 className="text-xl font-bold text-slate-900">Finding your best matches...</h3>
                <p className="text-slate-500 text-sm mt-2">Analyzing candidate profiles against your requirements.</p>
              </div>
            ) : null}

            <h2 className="text-xl font-bold text-slate-900 mb-6 border-b pb-2">Create New Job Posting</h2>
            
            {(plan === 'free' || !plan) && jobs.length >= 2 ? (
              <div className="bg-orange-50 border border-orange-200 p-6 rounded-lg text-center my-8">
                <div className="text-orange-500 font-bold mb-2 text-lg">Job Posting Cap Reached</div>
                <p className="text-orange-700 text-sm mb-4">
                  You are currently on the Free plan, which allows up to 2 active job postings. 
                  Upgrade to a premium plan to post unlimited jobs and access advanced applicant matching.
                </p>
                <Link href="/company/pricing">
                  <Button>View Pricing Plans</Button>
                </Link>
              </div>
            ) : (
            <div className="space-y-6">
              <FormField label="Job Title" required>
                <Input placeholder="e.g. Senior Frontend Engineer" value={jobPosting.title} onChange={e => setJobPosting({...jobPosting, title: e.target.value})} />
              </FormField>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <FormField label="Vertical" required>
                  <select 
                    className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-primary text-slate-900"
                    value={jobPosting.vertical} onChange={e => setJobPosting({...jobPosting, vertical: e.target.value})}
                  >
                    <option value="">Select Vertical</option>
                    <option value="Frontend">Frontend</option>
                    <option value="Backend">Backend</option>
                    <option value="Fullstack">Fullstack</option>
                    <option value="DevOps">DevOps</option>
                    <option value="Data Science">Data Science</option>
                    <option value="Product">Product Management</option>
                  </select>
                </FormField>
                <FormField label="Experience Range" required>
                  <Input placeholder="e.g. 3-5 Years" value={jobPosting.experience} onChange={e => setJobPosting({...jobPosting, experience: e.target.value})} />
                </FormField>
              </div>

              <FormField label="Must-have Skills" required>
                <SearchableCombobox 
                  options={TECH_SKILLS} 
                  value={jobPosting.skills} 
                  onChange={tags => setJobPosting({...jobPosting, skills: tags})} 
                  placeholder="Select required skills..."
                  multiSelect={true}
                />
              </FormField>

              <FormField label="Job Description" required>
                <Textarea 
                  placeholder="Describe responsibilities, requirements, and what success looks like in this role" 
                  value={jobPosting.description} onChange={e => setJobPosting({...jobPosting, description: e.target.value})} 
                  className="min-h-[120px]"
                />
              </FormField>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <FormField label="Location" required>
                  <SearchableCombobox options={CITIES} value={jobPosting.location} onChange={val => setJobPosting({...jobPosting, location: val})} placeholder="e.g. Bengaluru, Remote" />
                </FormField>
                
                <FormField label="Employment Type" required>
                  <select 
                    className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-primary text-slate-900"
                    value={jobPosting.employmentType} onChange={e => setJobPosting({...jobPosting, employmentType: e.target.value})}
                  >
                    <option value="">Select Type</option>
                    <option value="Full-time">Full-time</option>
                    <option value="Part-time">Part-time</option>
                    <option value="Contract">Contract</option>
                    <option value="Internship">Internship</option>
                  </select>
                </FormField>
              </div>

              <FormField label="Salary Range (Optional)">
                <div className="flex items-center gap-4">
                  <div className="relative flex-1">
                    <span className="absolute left-3 top-2 text-slate-500">₹</span>
                    <Input type="number" className="pl-8" placeholder="Min" value={jobPosting.salaryMin} onChange={e => setJobPosting({...jobPosting, salaryMin: e.target.value})} disabled={jobPosting.salaryUndisclosed} />
                  </div>
                  <span className="text-slate-400">to</span>
                  <div className="relative flex-1">
                    <span className="absolute left-3 top-2 text-slate-500">₹</span>
                    <Input type="number" className="pl-8" placeholder="Max" value={jobPosting.salaryMax} onChange={e => setJobPosting({...jobPosting, salaryMax: e.target.value})} disabled={jobPosting.salaryUndisclosed} />
                  </div>
                </div>
                <div className="mt-2">
                  <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
                    <input type="checkbox" checked={jobPosting.salaryUndisclosed} onChange={e => setJobPosting({...jobPosting, salaryUndisclosed: e.target.checked})} />
                    Don't disclose salary
                  </label>
                </div>
              </FormField>

              <div className="pt-4 flex justify-end">
                <Button variant="primary" size="lg" onClick={handlePostJob} disabled={isPosting}>
                  Post Job & Find Matches
                </Button>
              </div>
            </div>
            )}
          </Card>
        )}

        {/* MY POSTINGS TAB */}
        {activeTab === 'my-postings' && (
          <Card className="p-0 overflow-hidden">
            <div className="p-6 border-b border-slate-200 bg-white">
              <h2 className="text-xl font-bold text-slate-900">My Job Postings</h2>
            </div>
            {jobs.length === 0 ? (
              <div className="p-16 text-center text-slate-500">
                You haven't posted any jobs yet.
                <div className="mt-4"><Button onClick={() => setActiveTab('post')}>Post a Job</Button></div>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-slate-600">
                  <thead className="bg-slate-50 text-slate-700 font-semibold border-b border-slate-200">
                    <tr>
                      <th className="p-4">Job Title</th>
                      <th className="p-4">Status</th>
                      <th className="p-4">Matched</th>
                      <th className="p-4">Shortlisted</th>
                      <th className="p-4">Posted Date</th>
                      <th className="p-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {jobs.map((job) => (
                      <tr key={job.id} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                        <td className="p-4 font-medium text-slate-900">
                          {job.title}
                          <div className="text-xs text-slate-500 font-normal">{job.vertical}</div>
                        </td>
                        <td className="p-4">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${job.status === 'Live' ? 'bg-green-100 text-green-700' : 'bg-slate-200 text-slate-700'}`}>
                            {job.status}
                          </span>
                        </td>
                        <td className="p-4">{job.matched}</td>
                        <td className="p-4">{job.shortlisted}</td>
                        <td className="p-4">{job.date}</td>
                        <td className="p-4 text-right space-x-3">
                          <button 
                            className="text-slate-500 hover:text-primary font-medium text-sm"
                            onClick={() => {
                              setJobPosting({
                                id: job.id,
                                title: job.title,
                                vertical: job.vertical,
                                experience: '3-5 Years',
                                skills: ['React', 'TypeScript'],
                                description: 'Mock description for editing',
                                location: 'Bengaluru',
                                employmentType: 'Full-time',
                                salaryMin: '',
                                salaryMax: '',
                                salaryUndisclosed: false
                              });
                              setActiveTab('post');
                            }}
                          >
                            Edit
                          </button>
                          <button 
                            className="text-primary hover:underline font-medium text-sm"
                            onClick={() => {
                              setSelectedJobId(job.id);
                              setActiveTab('candidates');
                            }}
                          >
                            View Candidates
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        )}

        {/* RANKED CANDIDATES TAB */}
        {activeTab === 'candidates' && (
          <Card className="p-0 overflow-hidden">
            <div className="p-6 border-b border-slate-200 flex flex-col md:flex-row justify-between items-start md:items-center bg-white gap-4">
              <div className="flex-1 flex items-center gap-3">
                <span className="text-slate-600 font-medium">Showing matches for:</span>
                <select 
                  className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-900 font-semibold focus:outline-none focus:ring-2 focus:ring-primary min-w-[250px]"
                  value={selectedJobId}
                  onChange={(e) => setSelectedJobId(Number(e.target.value))}
                >
                  {jobs.map(job => (
                    <option key={job.id} value={job.id}>{job.title}</option>
                  ))}
                </select>
              </div>
              <div className="flex bg-slate-100 p-1 rounded-lg">
                <button 
                  className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors ${!showShortlistedOnly ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500'}`}
                  onClick={() => setShowShortlistedOnly(false)}
                >
                  All Matches
                </button>
                <button 
                  className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors ${showShortlistedOnly ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500'}`}
                  onClick={() => setShowShortlistedOnly(true)}
                >
                  Shortlisted
                </button>
              </div>
            </div>

            {filteredCandidates.length === 0 ? (
              <div className="p-16 text-center text-slate-500 flex flex-col items-center">
                <Users className="w-12 h-12 text-slate-300 mb-4" />
                <h3 className="text-lg font-bold text-slate-800">No matches found</h3>
                <p className="max-w-sm mt-2">
                  {showShortlistedOnly 
                    ? "You haven't shortlisted any candidates for this role yet." 
                    : "No matches yet — we'll notify you as candidates apply or as new profiles are added."}
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-slate-600">
                  <thead className="bg-slate-50 text-slate-700 font-semibold border-b border-slate-200">
                    <tr>
                      <th className="p-4 w-1/4">Candidate Name</th>
                      <th className="p-4 w-32">Fitment Score</th>
                      <th className="p-4">AI Rationale</th>
                      <th className="p-4 w-40 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredCandidates.map((candidate) => (
                      <tr key={candidate.id} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                        <td className="p-4 font-medium text-slate-900">
                          {candidate.name}
                          <div className="text-xs text-slate-500 font-normal">{candidate.vertical}</div>
                        </td>
                        <td className="p-4">
                          <span className={`inline-flex items-center justify-center px-2.5 py-1 text-xs font-bold rounded-full ${candidate.badgeColor}`}>
                            <TrendingUp className="w-3 h-3 mr-1" /> {candidate.fitment}
                          </span>
                        </td>
                        <td className="p-4 text-slate-500 text-xs">
                          {candidate.rationale}
                        </td>
                        <td className="p-4 text-right">
                          <div className="flex justify-end items-center gap-1">
                            <button 
                              className="p-1.5 text-slate-400 hover:text-primary hover:bg-blue-50 rounded-lg transition-colors" 
                              title="View Resume"
                              onClick={() => openProfile(candidate)}
                            >
                              <Eye className="w-5 h-5" />
                            </button>
                            <button 
                              className={`p-1.5 rounded-lg transition-colors flex items-center ${candidate.isShortlisted ? 'text-green-600 bg-green-50 hover:bg-green-100' : 'text-slate-400 hover:text-primary hover:bg-blue-50'}`} 
                              title={candidate.isShortlisted ? "Shortlisted" : "Shortlist"}
                              onClick={() => toggleShortlist(candidate.id)}
                            >
                              {candidate.isShortlisted ? <Check className="w-5 h-5" /> : <Bookmark className="w-5 h-5" />}
                            </button>
                            {candidate.isShortlisted && (
                              <button 
                                className="p-1.5 text-slate-400 hover:text-primary hover:bg-blue-50 rounded-lg transition-colors" 
                                title="Message"
                                onClick={() => openMessage(candidate.name)}
                              >
                                <MessageCircle className="w-5 h-5" />
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        )}

      </div>

      <CandidateProfileModal 
        isOpen={isProfileModalOpen} 
        onClose={() => setIsProfileModalOpen(false)} 
        candidate={selectedCandidate} 
      />
      
      <MessageModal
        isOpen={isMessageModalOpen}
        onClose={() => setIsMessageModalOpen(false)}
        candidateName={candidateToMessage}
      />
    </div>
  );
}
