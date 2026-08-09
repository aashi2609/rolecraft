"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from 'react';
import type { PlanId } from '@/lib/plans';
import { isFreePlan } from '@/lib/plans';
import { useApplicationSocket } from '@/hooks/useApplicationSocket';
import {
  applicationsApi,
  authApi,
  candidateApi,
  companyApi,
  getToken,
  jobsApi,
  resumesApi,
  savedJobsApi,
  setToken,
  subscriptionsApi,
} from '@/lib/api';

type Role = 'candidate' | 'company' | null;

interface UserState {
  isAuthenticated: boolean;
  role: Role;
  userId: string | null;
  profileComplete: boolean;
  companyProfileComplete: boolean;
  plan: PlanId;
  planValidTill: string;
  pendingPlan: PlanId | null;
  candidateProfile: Record<string, unknown>;
  companyProfile: Record<string, unknown>;
  jobs: any[];
  savedJobs: string[];
  applications: any[];
  resumes: any[];
  messages: any[];
  hiddenJobIds: string[];
  savedCandidateIds: string[];
  loading: boolean;
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
  refreshSession: () => Promise<void>;
  refreshJobs: () => Promise<void>;
  refreshResumes: () => Promise<void>;
  refreshApplications: () => Promise<void>;
  addJob: (job: any) => void;
  updateJob: (job: any) => void;
  toggleSavedJob: (jobId: string | number) => Promise<void>;
  applyToJob: (application: any) => Promise<void>;
  addResume: (resume: any) => void;
  addMessage: (message: any) => void;
  hideJob: (jobId: string | number) => void;
  toggleSavedCandidate: (id: string | number) => void;
  /** Real auth helpers used by signin/signup pages */
  signInWithApi: (email: string, password: string) => Promise<{ role: string; plan?: string; profileComplete: boolean; companyProfileComplete: boolean }>;
  signUpWithApi: (payload: {
    email: string;
    password: string;
    role: 'candidate' | 'company';
    name?: string;
    industry?: string;
    plan?: string;
  }) => Promise<{ role: string; plan?: string }>;
}

const UserContext = createContext<UserContextType | undefined>(undefined);

function defaultValidTill(): string {
  const d = new Date();
  d.setMonth(d.getMonth() + 1);
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
}

function mapResume(r: any) {
  return {
    id: r.id,
    vertical: r.target_vertical,
    score: r.ats_score,
    date: r.created_at?.slice?.(0, 10) || r.created_at,
    summary: r.content?.summary,
    mappingNotes: r.content?.mappingNotes,
    highlightedSkills: r.content?.highlightedSkills,
    emphasis: r.content?.emphasis,
    content: r.content,
    atsBreakdown: r.ats_breakdown,
    version: r.version || 1,
    generationMethod: r.generation_metadata?.method || 'deterministic',
  };
}

function mapJob(j: any) {
  return {
    id: j.id,
    companyId: j.company_id,
    companyName: j.company_name,
    title: j.title,
    vertical: j.department,
    department: j.department,
    location: j.location,
    employmentType: j.employment_type,
    jobType: j.job_type
      ? String(j.job_type).charAt(0).toUpperCase() + String(j.job_type).slice(1)
      : undefined,
    salaryMin: j.min_salary != null ? String(j.min_salary) : '',
    salaryMax: j.max_salary != null ? String(j.max_salary) : '',
    salaryUnit: j.salary_unit || 'Per annum',
    salaryUndisclosed: !j.min_salary && !j.max_salary,
    experience: j.experience_range,
    skills: j.required_skills || [],
    description: j.description,
    responsibilities: j.responsibilities,
    requirements: j.requirements,
    benefits: j.benefits,
    openings: j.num_openings,
    deadline: j.application_deadline,
    status: j.status ? String(j.status).charAt(0).toUpperCase() + String(j.status).slice(1) : 'Draft',
    matched: j.matched ?? 0,
    shortlisted: j.shortlisted ?? 0,
    date: j.created_at?.slice?.(0, 10) || j.created_at,
  };
}

function mapApplication(a: any) {
  return {
    id: a.id,
    jobId: a.job_id,
    jobTitle: a.job_title,
    companyName: a.company_name,
    status: a.status ? String(a.status).charAt(0).toUpperCase() + String(a.status).slice(1) : 'Applied',
    date: a.applied_at?.slice?.(0, 10) || a.applied_at,
    resumeId: a.resume_id,
  };
}

const initialState: UserState = {
  isAuthenticated: false,
  role: null,
  userId: null,
  profileComplete: false,
  companyProfileComplete: false,
  plan: 'basic',
  planValidTill: defaultValidTill(),
  pendingPlan: null,
  candidateProfile: {},
  companyProfile: {},
  jobs: [],
  savedJobs: [],
  applications: [],
  resumes: [],
  messages: [],
  hiddenJobIds: [],
  savedCandidateIds: [],
  loading: true,
};

export function UserProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<UserState>(initialState);

  const refreshJobs = useCallback(async () => {
    try {
      const role = state.role;
      const raw =
        role === 'company' && getToken()
          ? await jobsApi.mine().catch(() => jobsApi.list({ status: 'live' }))
          : await jobsApi.list({ status: 'live' });
      setState((prev) => ({ ...prev, jobs: (raw || []).map(mapJob) }));
    } catch {
      /* API may be offline during Stage 0 UI work */
    }
  }, [state.role]);

  const refreshResumes = useCallback(async () => {
    if (!getToken()) return;
    try {
      const raw = await resumesApi.list();
      setState((prev) => ({ ...prev, resumes: (raw || []).map(mapResume) }));
    } catch {
      /* ignore */
    }
  }, []);

  const refreshApplications = useCallback(async () => {
    if (!getToken()) return;
    try {
      const raw = await applicationsApi.mine();
      setState((prev) => ({ ...prev, applications: (raw || []).map(mapApplication) }));
    } catch {
      /* ignore */
    }
  }, []);

  const refreshSession = useCallback(async () => {
    const token = getToken();
    if (!token) {
      setState((prev) => ({ ...prev, ...initialState, loading: false, jobs: prev.jobs }));
      try {
        const raw = await jobsApi.list({ status: 'live' });
        setState((prev) => ({ ...prev, jobs: (raw || []).map(mapJob), loading: false }));
      } catch {
        setState((prev) => ({ ...prev, loading: false }));
      }
      return;
    }

    try {
      // Probe role via candidate/me or company/me
      let role: Role = null;
      let plan: PlanId = 'basic';
      let userId: string | null = null;
      let candidateProfile: Record<string, unknown> = {};
      let companyProfile: Record<string, unknown> = {};
      let profileComplete = false;
      let companyProfileComplete = false;

      try {
        const me: any = await candidateApi.me();
        role = 'candidate';
        userId = me.user_id;
        candidateProfile = me;
        profileComplete = Boolean(
          me.career_level && String(me.career_level).trim().length > 0 &&
          me.skills && Array.isArray(me.skills) && me.skills.length > 0
        );
      } catch {
        try {
          const me: any = await companyApi.me();
          role = 'company';
          userId = me.user_id;
          companyProfile = me;
          companyProfileComplete = Boolean(me.name);
        } catch {
          setToken(null);
          setState((prev) => ({ ...prev, ...initialState, loading: false }));
          return;
        }
      }

      try {
        const sub: any = await subscriptionsApi.me();
        plan = (sub.plan_tier as PlanId) || plan;
      } catch {
        /* keep default */
      }

      let jobs: any[] = [];
      let resumes: any[] = [];
      let applications: any[] = [];
      let savedJobs: string[] = [];

      if (role === 'company') {
        jobs = ((await jobsApi.mine().catch(() => [])) as any[]).map(mapJob);
      } else {
        jobs = ((await jobsApi.list({ status: 'live' }).catch(() => [])) as any[]).map(mapJob);
        resumes = ((await resumesApi.list().catch(() => [])) as any[]).map(mapResume);
        applications = ((await applicationsApi.mine().catch(() => [])) as any[]).map(mapApplication);
        const saved = await savedJobsApi.list().catch(() => ({ job_ids: [] as string[] }));
        savedJobs = saved.job_ids || [];
      }

      setState((prev) => ({
        ...prev,
        isAuthenticated: true,
        role,
        userId,
        plan,
        planValidTill: defaultValidTill(),
        candidateProfile,
        companyProfile,
        profileComplete,
        companyProfileComplete,
        jobs,
        resumes,
        applications,
        savedJobs,
        loading: false,
      }));
    } catch {
      setState((prev) => ({ ...prev, loading: false }));
    }
  }, []);

  useEffect(() => {
    refreshSession();
  }, [refreshSession]);

  // ── Real-time application status updates via WebSocket ──────────────
  const handleWsEvent = useCallback(
    (event: { type: string; payload: Record<string, unknown> }) => {
      if (event.type === 'application_status_updated' && event.payload) {
        setState((prev) => ({
          ...prev,
          applications: prev.applications.map((app) =>
            String(app.id) === String(event.payload.id)
              ? {
                  ...app,
                  status: event.payload.status
                    ? String(event.payload.status).charAt(0).toUpperCase() +
                      String(event.payload.status).slice(1)
                    : app.status,
                }
              : app
          ),
        }));
      }
    },
    []
  );

  useApplicationSocket({
    onEvent: handleWsEvent,
    onPollFallback: refreshApplications,
    enabled: state.isAuthenticated && state.role === 'candidate',
  });

  const signInWithApi = async (email: string, password: string) => {
    const res = await authApi.signin({ email, password });
    setToken(res.access_token);
    await refreshSession();

    // Determine profile completeness from fresh backend data
    let isProfileComplete = false;
    let isCompanyProfileComplete = false;
    try {
      if (res.role === 'candidate') {
        const me: any = await candidateApi.me();
        isProfileComplete = Boolean(
          me.career_level && String(me.career_level).trim().length > 0 &&
          me.skills && Array.isArray(me.skills) && me.skills.length > 0
        );
      } else if (res.role === 'company') {
        const me: any = await companyApi.me();
        isCompanyProfileComplete = Boolean(me.name);
      }
    } catch {
      /* profile probe failed — treat as incomplete */
    }

    return { role: res.role, plan: res.plan, profileComplete: isProfileComplete, companyProfileComplete: isCompanyProfileComplete };
  };

  const signUpWithApi = async (payload: {
    email: string;
    password: string;
    role: 'candidate' | 'company';
    name?: string;
    industry?: string;
    plan?: string;
  }) => {
    const res = await authApi.signup(payload);
    setToken(res.access_token);
    setState((prev) => ({
      ...prev,
      isAuthenticated: true,
      role: res.role as Role,
      userId: res.user_id,
      plan: (isFreePlan(res.plan) ? res.plan : 'basic') as PlanId,
      pendingPlan: isFreePlan(res.plan) ? null : ((res.plan as PlanId) || null),
    }));
    await refreshSession();
    return { role: res.role, plan: res.plan };
  };

  /** Legacy stub login kept for any remaining callers — prefers clearing to API auth */
  const login = (role: Role, plan: PlanId = 'basic') =>
    setState((prev) => ({
      ...prev,
      isAuthenticated: true,
      role,
      plan: isFreePlan(plan) ? plan : 'basic',
      pendingPlan: isFreePlan(plan) ? null : plan,
      planValidTill: defaultValidTill(),
    }));

  const logout = () => {
    setToken(null);
    setState({ ...initialState, loading: false });
  };

  const setProfileComplete = (status: boolean) =>
    setState((prev) => ({ ...prev, profileComplete: status }));
  const setCompanyProfileComplete = (status: boolean) =>
    setState((prev) => ({ ...prev, companyProfileComplete: status }));
  const switchRole = (role: Role) => setState((prev) => ({ ...prev, role }));
  const setPlan = async (plan: PlanId) => {
    try {
      await subscriptionsApi.set(plan);
      setState((prev) => ({
        ...prev,
        plan,
        pendingPlan: null,
        planValidTill: defaultValidTill(),
      }));
    } catch (error) {
      console.error('Failed to update subscription:', error);
      // Still update local state for UX, API call might be optional during checkout
      setState((prev) => ({
        ...prev,
        plan,
        pendingPlan: null,
        planValidTill: defaultValidTill(),
      }));
    }
  };
  const setPendingPlan = (plan: PlanId | null) =>
    setState((prev) => ({ ...prev, pendingPlan: plan }));
  const setCandidateProfile = (profile: Record<string, unknown>) =>
    setState((prev) => ({ ...prev, candidateProfile: { ...prev.candidateProfile, ...profile } }));

  const addJob = (job: any) => setState((prev) => ({ ...prev, jobs: [job, ...prev.jobs] }));
  const updateJob = (job: any) =>
    setState((prev) => ({
      ...prev,
      jobs: prev.jobs.map((j) => (String(j.id) === String(job.id) ? { ...j, ...job } : j)),
    }));

  const toggleSavedJob = async (jobId: string | number) => {
    const id = String(jobId);
    const isSaved = state.savedJobs.includes(id);
    setState((prev) => ({
      ...prev,
      savedJobs: isSaved ? prev.savedJobs.filter((x) => x !== id) : [...prev.savedJobs, id],
    }));
    try {
      if (isSaved) await savedJobsApi.unsave(id);
      else await savedJobsApi.save(id);
    } catch {
      /* revert on failure */
      setState((prev) => ({
        ...prev,
        savedJobs: isSaved ? [...prev.savedJobs, id] : prev.savedJobs.filter((x) => x !== id),
      }));
    }
  };

  const applyToJob = async (application: any) => {
    const jobId = String(application.jobId || application.job_id);
    try {
      const created = await applicationsApi.apply(jobId, application.resumeId);
      setState((prev) => ({
        ...prev,
        applications: [mapApplication(created), ...prev.applications],
      }));
    } catch (err: any) {
      // Don't add a local copy on failure — it creates duplicates in state.
      // Re-throw so callers can handle UI feedback (e.g. "Already applied" toast).
      throw err;
    }
  };

  const addResume = (resume: any) =>
    setState((prev) => ({ ...prev, resumes: [resume, ...prev.resumes] }));
  const addMessage = (message: any) =>
    setState((prev) => ({ ...prev, messages: [...prev.messages, message] }));
  const hideJob = (jobId: string | number) =>
    setState((prev) => ({
      ...prev,
      hiddenJobIds: prev.hiddenJobIds.includes(String(jobId))
        ? prev.hiddenJobIds
        : [...prev.hiddenJobIds, String(jobId)],
    }));
  const toggleSavedCandidate = (id: string | number) =>
    setState((prev) => {
      const sid = String(id);
      const has = prev.savedCandidateIds.includes(sid);
      return {
        ...prev,
        savedCandidateIds: has
          ? prev.savedCandidateIds.filter((x) => x !== sid)
          : [...prev.savedCandidateIds, sid],
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
        refreshSession,
        refreshJobs,
        refreshResumes,
        refreshApplications,
        addJob,
        updateJob,
        toggleSavedJob,
        applyToJob,
        addResume,
        addMessage,
        hideJob,
        toggleSavedCandidate,
        signInWithApi,
        signUpWithApi,
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
