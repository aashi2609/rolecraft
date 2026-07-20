"use client";

import React, { createContext, useContext, useState, ReactNode } from 'react';

type Role = 'candidate' | 'company' | null;
type Plan = 'free' | 'premium' | 'growth' | 'scale';

interface UserState {
  isAuthenticated: boolean;
  role: Role;
  profileComplete: boolean;
  companyProfileComplete: boolean;
  plan: Plan;
  
  // Global Mock DB
  jobs: any[];
  savedJobs: number[]; // jobIds
  applications: any[];
  resumes: any[];
  messages: any[]; // { id, jobId, candidateId, companyId, sender, text, timestamp }
}

interface UserContextType extends UserState {
  login: (role: Role) => void;
  logout: () => void;
  setProfileComplete: (status: boolean) => void;
  setCompanyProfileComplete: (status: boolean) => void;
  switchRole: (role: Role) => void;
  setPlan: (plan: Plan) => void;
  
  addJob: (job: any) => void;
  updateJob: (job: any) => void;
  toggleSavedJob: (jobId: number) => void;
  applyToJob: (application: any) => void;
  addResume: (resume: any) => void;
  addMessage: (message: any) => void;
}

const UserContext = createContext<UserContextType | undefined>(undefined);

export function UserProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<UserState>({
    isAuthenticated: false,
    role: null,
    profileComplete: false,
    companyProfileComplete: false,
    plan: 'free',
    
    // Seed initial jobs
    jobs: [
      { 
        id: 1, 
        companyId: 1, 
        companyName: 'TechCorp Inc.', 
        title: 'Senior Frontend Engineer', 
        vertical: 'Frontend', 
        location: 'Bengaluru', 
        employmentType: 'Full-time', 
        salaryMin: '2500000', 
        salaryMax: '3500000', 
        salaryUndisclosed: false,
        experience: '3-5 Years', 
        skills: ['React', 'TypeScript', 'Next.js'], 
        description: 'Looking for a Senior Frontend Engineer to lead our core product team.', 
        status: 'Live', 
        matched: 24, 
        shortlisted: 3, 
        date: '2026-07-15' 
      },
      { 
        id: 2, 
        companyId: 2, 
        companyName: 'Startup LLC', 
        title: 'Backend Developer', 
        vertical: 'Backend', 
        location: 'Remote', 
        employmentType: 'Contract', 
        salaryMin: '', 
        salaryMax: '', 
        salaryUndisclosed: true,
        experience: '1-3 Years', 
        skills: ['Node.js', 'PostgreSQL', 'AWS'], 
        description: 'Join our fast-paced backend team to build scalable APIs.', 
        status: 'Live', 
        matched: 12, 
        shortlisted: 1, 
        date: '2026-07-18' 
      }
    ],
    savedJobs: [],
    applications: [],
    resumes: [],
    messages: []
  });

  const login = (role: Role) => setState(prev => ({ ...prev, isAuthenticated: true, role, profileComplete: false, companyProfileComplete: false, plan: 'free' }));
  const logout = () => setState(prev => ({ ...prev, isAuthenticated: false, role: null, profileComplete: false, companyProfileComplete: false, plan: 'free', savedJobs: [], applications: [], resumes: [], messages: [] }));
  const setProfileComplete = (status: boolean) => setState(prev => ({ ...prev, profileComplete: status }));
  const setCompanyProfileComplete = (status: boolean) => setState(prev => ({ ...prev, companyProfileComplete: status }));
  const switchRole = (role: Role) => setState(prev => ({ ...prev, role }));
  const setPlan = (plan: Plan) => setState(prev => ({ ...prev, plan }));

  const addJob = (job: any) => setState(prev => ({ ...prev, jobs: [job, ...prev.jobs] }));
  const updateJob = (job: any) => setState(prev => ({ ...prev, jobs: prev.jobs.map(j => j.id === job.id ? job : j) }));
  
  const toggleSavedJob = (jobId: number) => setState(prev => {
    const isSaved = prev.savedJobs.includes(jobId);
    return {
      ...prev,
      savedJobs: isSaved ? prev.savedJobs.filter(id => id !== jobId) : [...prev.savedJobs, jobId]
    };
  });
  
  const applyToJob = (application: any) => setState(prev => ({ ...prev, applications: [application, ...prev.applications] }));
  const addResume = (resume: any) => setState(prev => ({ ...prev, resumes: [resume, ...prev.resumes] }));
  const addMessage = (message: any) => setState(prev => ({ ...prev, messages: [...prev.messages, message] }));

  return (
    <UserContext.Provider value={{ 
      ...state, 
      login, logout, setProfileComplete, setCompanyProfileComplete, switchRole, setPlan,
      addJob, updateJob, toggleSavedJob, applyToJob, addResume, addMessage 
    }}>
      {children}
    </UserContext.Provider>
  );
}

export function useUser() {
  const context = useContext(UserContext);
  if (context === undefined) {
    throw new Error('useUser must be used within a UserProvider');
  }
  return context;
}
