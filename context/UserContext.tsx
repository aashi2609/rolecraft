"use client";

import React, { createContext, useContext, useState, ReactNode } from 'react';
import type { PlanId } from '@/lib/plans';
import { isFreePlan } from '@/lib/plans';

type Role = 'candidate' | 'company' | null;

interface UserState {
  isAuthenticated: boolean;
  role: Role;
  profileComplete: boolean;
  companyProfileComplete: boolean;
  plan: PlanId;
  planValidTill: string;
  pendingPlan: PlanId | null;
  candidateProfile: Record<string, unknown>;

  jobs: any[];
  savedJobs: number[];
  applications: any[];
  resumes: any[];
  messages: any[];
  hiddenJobIds: number[];
  savedCandidateIds: number[];
}

interface UserContextType extends UserState {
  login: (role: Role, plan?: PlanId) => void;
  logout: () => void;
  setProfileComplete: (status: boolean) => void;
  setCompanyProfileComplete: (status: boolean) => void;
  switchRole: (role: Role) => void;
  setPlan: (plan: PlanId) => void;
  setPendingPlan: (plan: PlanId | null) => void;
  setCandidateProfile: (profile: Record<string, unknown>) => void;

  addJob: (job: any) => void;
  updateJob: (job: any) => void;
  toggleSavedJob: (jobId: number) => void;
  applyToJob: (application: any) => void;
  addResume: (resume: any) => void;
  addMessage: (message: any) => void;
  hideJob: (jobId: number) => void;
  toggleSavedCandidate: (id: number) => void;
}

const UserContext = createContext<UserContextType | undefined>(undefined);

const SEED_JOBS = [
  {
    id: 1,
    companyId: 1,
    companyName: 'TechCorp Inc.',
    title: 'Senior Frontend Engineer',
    vertical: 'Frontend',
    department: 'Engineering',
    location: 'Bangalore, Karnataka',
    employmentType: 'Full-time',
    jobType: 'Hybrid',
    salaryMin: '2500000',
    salaryMax: '3500000',
    salaryUnit: 'Per annum',
    salaryUndisclosed: false,
    experience: '3-5 Years',
    skills: ['React', 'TypeScript', 'Next.js', 'Tailwind CSS'],
    description: 'Looking for a Senior Frontend Engineer to lead our core product team.',
    responsibilities: 'Lead UI architecture\nMentor juniors\nShip high-quality features',
    requirements: '3+ years React\nStrong TypeScript\nProduct mindset',
    benefits: 'Health insurance\nFlexible WFH\nLearning budget',
    openings: 2,
    deadline: '2026-08-30',
    status: 'Live',
    matched: 24,
    shortlisted: 3,
    date: '2026-07-15',
  },
  {
    id: 2,
    companyId: 2,
    companyName: 'Startup LLC',
    title: 'Backend Developer',
    vertical: 'Backend',
    department: 'Engineering',
    location: 'Remote',
    employmentType: 'Contract',
    jobType: 'Remote',
    salaryMin: '',
    salaryMax: '',
    salaryUnit: 'Per annum',
    salaryUndisclosed: true,
    experience: '1-3 Years',
    skills: ['Node.js', 'PostgreSQL', 'AWS'],
    description: 'Join our fast-paced backend team to build scalable APIs.',
    responsibilities: '',
    requirements: '',
    benefits: '',
    openings: 1,
    deadline: '2026-08-15',
    status: 'Live',
    matched: 12,
    shortlisted: 1,
    date: '2026-07-18',
  },
  {
    id: 3,
    companyId: 3,
    companyName: 'DesignStudio',
    title: 'Senior UI/UX Designer',
    vertical: 'UI/UX Designer',
    department: 'Design',
    location: 'Bangalore, Karnataka',
    employmentType: 'Full-time',
    jobType: 'On-site',
    salaryMin: '1200000',
    salaryMax: '1800000',
    salaryUnit: 'Per annum',
    salaryUndisclosed: false,
    experience: '3-5 Years',
    skills: ['Figma', 'UI Design', 'Prototyping', 'Photoshop', 'User Research'],
    description: 'Craft delightful product experiences across web and mobile.',
    responsibilities: 'Own end-to-end design\nRun research sessions\nBuild design systems',
    requirements: 'Portfolio required\n3+ years product design',
    benefits: 'Creative days\nLatest tools\nWellness allowance',
    openings: 3,
    deadline: '2026-09-01',
    status: 'Live',
    matched: 18,
    shortlisted: 2,
    date: '2026-07-20',
  },
  {
    id: 4,
    companyId: 4,
    companyName: 'GrowthLabs',
    title: 'Marketing Specialist',
    vertical: 'Marketing',
    department: 'Marketing',
    location: 'Mumbai',
    employmentType: 'Full-time',
    jobType: 'Hybrid',
    salaryMin: '800000',
    salaryMax: '1200000',
    salaryUnit: 'Per annum',
    salaryUndisclosed: false,
    experience: '1-3 Years',
    skills: ['Content Marketing', 'SEO', 'Google Analytics', 'Social Media'],
    description: 'Drive brand growth through content and performance marketing.',
    responsibilities: '',
    requirements: '',
    benefits: '',
    openings: 1,
    deadline: '2026-08-20',
    status: 'Live',
    matched: 9,
    shortlisted: 0,
    date: '2026-07-21',
  },
];

function defaultValidTill(): string {
  const d = new Date();
  d.setMonth(d.getMonth() + 1);
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
}

export function UserProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<UserState>({
    isAuthenticated: false,
    role: null,
    profileComplete: false,
    companyProfileComplete: false,
    plan: 'basic',
    planValidTill: defaultValidTill(),
    pendingPlan: null,
    candidateProfile: {},
    jobs: SEED_JOBS,
    savedJobs: [],
    applications: [],
    resumes: [],
    messages: [],
    hiddenJobIds: [],
    savedCandidateIds: [],
  });

  const login = (role: Role, plan: PlanId = 'basic') =>
    setState((prev) => ({
      ...prev,
      isAuthenticated: true,
      role,
      profileComplete: false,
      companyProfileComplete: false,
      plan: isFreePlan(plan) ? plan : 'basic',
      pendingPlan: isFreePlan(plan) ? null : plan,
      planValidTill: defaultValidTill(),
    }));

  const logout = () =>
    setState((prev) => ({
      ...prev,
      isAuthenticated: false,
      role: null,
      profileComplete: false,
      companyProfileComplete: false,
      plan: 'basic',
      pendingPlan: null,
      candidateProfile: {},
      savedJobs: [],
      applications: [],
      resumes: [],
      messages: [],
      hiddenJobIds: [],
      savedCandidateIds: [],
    }));

  const setProfileComplete = (status: boolean) =>
    setState((prev) => ({ ...prev, profileComplete: status }));
  const setCompanyProfileComplete = (status: boolean) =>
    setState((prev) => ({ ...prev, companyProfileComplete: status }));
  const switchRole = (role: Role) => setState((prev) => ({ ...prev, role }));
  const setPlan = (plan: PlanId) =>
    setState((prev) => ({
      ...prev,
      plan,
      pendingPlan: null,
      planValidTill: defaultValidTill(),
    }));
  const setPendingPlan = (plan: PlanId | null) =>
    setState((prev) => ({ ...prev, pendingPlan: plan }));
  const setCandidateProfile = (profile: Record<string, unknown>) =>
    setState((prev) => ({ ...prev, candidateProfile: { ...prev.candidateProfile, ...profile } }));

  const addJob = (job: any) => setState((prev) => ({ ...prev, jobs: [job, ...prev.jobs] }));
  const updateJob = (job: any) =>
    setState((prev) => ({
      ...prev,
      jobs: prev.jobs.map((j) => (j.id === job.id ? job : j)),
    }));

  const toggleSavedJob = (jobId: number) =>
    setState((prev) => {
      const isSaved = prev.savedJobs.includes(jobId);
      return {
        ...prev,
        savedJobs: isSaved
          ? prev.savedJobs.filter((id) => id !== jobId)
          : [...prev.savedJobs, jobId],
      };
    });

  const applyToJob = (application: any) =>
    setState((prev) => ({ ...prev, applications: [application, ...prev.applications] }));
  const addResume = (resume: any) =>
    setState((prev) => ({ ...prev, resumes: [resume, ...prev.resumes] }));
  const addMessage = (message: any) =>
    setState((prev) => ({ ...prev, messages: [...prev.messages, message] }));
  const hideJob = (jobId: number) =>
    setState((prev) => ({
      ...prev,
      hiddenJobIds: prev.hiddenJobIds.includes(jobId)
        ? prev.hiddenJobIds
        : [...prev.hiddenJobIds, jobId],
    }));
  const toggleSavedCandidate = (id: number) =>
    setState((prev) => {
      const has = prev.savedCandidateIds.includes(id);
      return {
        ...prev,
        savedCandidateIds: has
          ? prev.savedCandidateIds.filter((x) => x !== id)
          : [...prev.savedCandidateIds, id],
      };
    });

  return (
    <UserContext.Provider
      value={{
        ...state,
        login,
        logout,
        setProfileComplete,
        setCompanyProfileComplete,
        switchRole,
        setPlan,
        setPendingPlan,
        setCandidateProfile,
        addJob,
        updateJob,
        toggleSavedJob,
        applyToJob,
        addResume,
        addMessage,
        hideJob,
        toggleSavedCandidate,
      }}
    >
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
