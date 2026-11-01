/**
 * Type definitions for API responses.
 * These are temporary until OpenAPI types are generated.
 */

export interface ResumeData {
  id: string;
  target_vertical?: string;
  ats_score?: number | null;
  created_at?: string;
  content?: {
    summary?: string;
    mappingNotes?: string;
    highlightedSkills?: string[];
    emphasis?: string;
  };
  ats_breakdown?: Record<string, unknown>;
  version?: number;
  generation_metadata?: {
    method?: string;
  };
  is_stale?: boolean;
  generated_from_profile_at?: string | null;
}

export interface JobData {
  id: string;
  company_id: string;
  company_name?: string;
  title: string;
  department?: string;
  location?: string;
  country?: string;
  state?: string;
  city?: string;
  employment_type?: string;
  job_type?: string;
  job_role?: string | null;
  job_level?: string | null;
  min_salary?: number | null;
  max_salary?: number | null;
  salary_unit?: string;
  experience_range?: string;
  required_skills?: string[];
  description?: string;
  responsibilities?: string;
  requirements?: string;
  benefits?: string;
  num_openings?: number;
  application_deadline?: string;
  status?: string;
  matched?: number;
  shortlisted?: number;
  created_at?: string;
}

export interface ApplicationData {
  id: string;
  job_id: string;
  job_title?: string;
  company_name?: string;
  status?: string;
  applied_at?: string;
  resume_id?: string;
}

export interface CandidateProfileData {
  user_id: string;
  full_name?: string;
  email?: string;
  career_level?: string;
  skills?: Array<{
    id: string;
    name: string;
  }>;
  [key: string]: unknown;
}

export interface CompanyProfileData {
  user_id: string;
  name?: string;
  [key: string]: unknown;
}

export interface MessageThreadData {
  thread_id: string;
  participant_label?: string;
  last_body?: string;
  last_sent_at?: string;
  other_user_id?: string;
}

export interface SubscriptionData {
  plan_tier?: string;
  [key: string]: unknown;
}
