/**
 * RoleCraft API client — JWT in localStorage, Bearer on every request.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
const TOKEN_KEY = 'rolecraft_token';

// Request cancellation manager
class RequestManager {
  private controllers = new Map<string, AbortController>();

  createKey(path: string, method: string = 'GET'): string {
    return `${method}:${path}`;
  }

  cancel(path: string, method: string = 'GET'): void {
    const key = this.createKey(path, method);
    const controller = this.controllers.get(key);
    if (controller) {
      controller.abort();
      this.controllers.delete(key);
    }
  }

  createSignal(path: string, method: string = 'GET'): AbortSignal {
    const key = this.createKey(path, method);
    const controller = new AbortController();
    this.controllers.set(key, controller);
    return controller.signal;
  }

  cleanup(path: string, method: string = 'GET'): void {
    const key = this.createKey(path, method);
    this.controllers.delete(key);
  }
}

export const requestManager = new RequestManager();

export function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (typeof window === 'undefined') return;
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  detail: string;
  type: 'network' | 'validation' | 'server' | 'auth' | 'unknown';
  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
    this.type = this.classifyError(status);
  }

  private classifyError(status: number): 'network' | 'validation' | 'server' | 'auth' | 'unknown' {
    if (status === 0 || status >= 500) return 'network';
    if (status === 401 || status === 403) return 'auth';
    if (status >= 400 && status < 500) return 'validation';
    if (status >= 500) return 'server';
    return 'unknown';
  }
}

type Opts = RequestInit & { auth?: boolean; formData?: FormData; retries?: number; signal?: AbortSignal };

const MAX_RETRIES = 3;
const BASE_DELAY_MS = 1_000;
const MAX_DELAY_MS = 10_000;

function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function calculateDelay(attempt: number): number {
  return Math.min(BASE_DELAY_MS * 2 ** attempt, MAX_DELAY_MS);
}

export async function api<T = unknown>(path: string, opts: Opts = {}): Promise<T> {
  const headers = new Headers(opts.headers || {});
  if (!opts.formData && !headers.has('Content-Type') && opts.body) {
    headers.set('Content-Type', 'application/json');
  }
  if (opts.auth !== false) {
    const token = getToken();
    if (token) headers.set('Authorization', `Bearer ${token}`);
  }

  const maxRetries = opts.retries ?? MAX_RETRIES;
  let lastError: Error | null = null;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const res = await fetch(`${API_URL}${path}`, {
        ...opts,
        headers,
        body: opts.formData ?? opts.body,
        signal: opts.signal,
      });

      if (!res.ok) {
        let detail = res.statusText;
        try {
          const data = await res.json();
          detail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
        } catch {
          /* ignore */
        }
        throw new ApiError(res.status, detail);
      }

      if (res.status === 204) return undefined as T;
      return res.json() as Promise<T>;
    } catch (error) {
      lastError = error as Error;

      // Don't retry on auth errors or 4xx errors (except 429)
      if (error instanceof ApiError) {
        if (error.type === 'auth' || (error.type === 'validation' && error.status !== 429)) {
          throw error;
        }
      }

      // Don't retry if request was aborted
      if (error instanceof DOMException && error.name === 'AbortError') {
        throw error;
      }

      // Don't retry on last attempt
      if (attempt === maxRetries) {
        throw lastError;
      }

      // Wait before retrying with exponential backoff
      const delayMs = calculateDelay(attempt);
      await delay(delayMs);
    }
  }

  throw lastError;
}

export const authApi = {
  signup: (body: {
    email: string;
    password: string;
    role: string;
    name?: string;
    industry?: string;
    plan?: string;
  }) =>
    api<{ access_token: string; user_id: string; role: string; plan?: string }>('/auth/signup', {
      method: 'POST',
      body: JSON.stringify(body),
      auth: false,
    }),
  signin: (body: { email: string; password: string }) =>
    api<{ access_token: string; user_id: string; role: string; plan?: string }>('/auth/signin', {
      method: 'POST',
      body: JSON.stringify(body),
      auth: false,
    }),
  forgotPassword: (email: string) =>
    api('/auth/forgot-password', {
      method: 'POST',
      body: JSON.stringify({ email }),
      auth: false,
    }),
  changePassword: (body: { current_password: string; new_password: string }) =>
    api('/auth/change-password', { method: 'POST', body: JSON.stringify(body) }),
  deleteAccount: () => api('/auth/me', { method: 'DELETE' }),
};

export const candidateApi = {
  me: () => api('/candidates/me'),
  updateMe: (body: Record<string, unknown>) =>
    api('/candidates/me', { method: 'PUT', body: JSON.stringify(body) }),
  putSkills: (skills: string[]) =>
    api('/candidates/me/skills', { method: 'PUT', body: JSON.stringify({ skills }) }),
  addEducation: (body: Record<string, unknown>) =>
    api('/candidates/me/education', { method: 'POST', body: JSON.stringify(body) }),
  updateEducation: (id: string, body: Record<string, unknown>) =>
    api(`/candidates/me/education/${id}`, { method: 'PUT', body: JSON.stringify(body) }),
  deleteEducation: (id: string) =>
    api(`/candidates/me/education/${id}`, { method: 'DELETE' }),

  addExperience: (body: Record<string, unknown>) =>
    api('/candidates/me/experience', { method: 'POST', body: JSON.stringify(body) }),
  updateExperience: (id: string, body: Record<string, unknown>) =>
    api(`/candidates/me/experience/${id}`, { method: 'PUT', body: JSON.stringify(body) }),
  deleteExperience: (id: string) =>
    api(`/candidates/me/experience/${id}`, { method: 'DELETE' }),

  addProject: (body: Record<string, unknown>) =>
    api('/candidates/me/projects', { method: 'POST', body: JSON.stringify(body) }),
  updateProject: (id: string, body: Record<string, unknown>) =>
    api(`/candidates/me/projects/${id}`, { method: 'PUT', body: JSON.stringify(body) }),
  deleteProject: (id: string) =>
    api(`/candidates/me/projects/${id}`, { method: 'DELETE' }),

  addCertification: (body: Record<string, unknown>) =>
    api('/candidates/me/certifications', { method: 'POST', body: JSON.stringify(body) }),
  updateCertification: (id: string, body: Record<string, unknown>) =>
    api(`/candidates/me/certifications/${id}`, { method: 'PUT', body: JSON.stringify(body) }),
  deleteCertification: (id: string) =>
    api(`/candidates/me/certifications/${id}`, { method: 'DELETE' }),
  get: (id: string) => api(`/candidates/${id}`),
  getPublicProfile: (id: string) => api(`/candidates/${id}/public-profile`),
  downloadResumePdf: async (id: string, filename?: string) => {
    const headers = new Headers();
    const token = getToken();
    if (token) headers.set('Authorization', `Bearer ${token}`);

    const res = await fetch(`${API_URL}/candidates/${id}/resume.pdf`, { headers });
    if (!res.ok) {
      let detail = res.statusText;
      try {
        const data = await res.json();
        detail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
      } catch {
        /* ignore */
      }
      throw new ApiError(res.status, detail);
    }

    const blob = await res.blob();
    const cd = res.headers.get('Content-Disposition') || '';
    const match = /filename="?([^"]+)"?/i.exec(cd);
    const downloadName = match?.[1] || filename || 'resume.pdf';
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = downloadName;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  },
  search: (params?: Record<string, string | number | undefined>) => {
    const q = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') q.set(k, String(v));
      });
    }
    const qs = q.toString();
    return api<any[]>(`/candidates/search${qs ? `?${qs}` : ''}`, { auth: false });
  },
};

export const companyApi = {
  me: () => api('/companies/me'),
  updateMe: (body: Record<string, unknown>) =>
    api('/companies/me', { method: 'PUT', body: JSON.stringify(body) }),
  get: (id: string) => api(`/companies/${id}`),
};

export const adminApi = {
  getMe: () => api('/admin/me'),
  getStats: () => api('/admin/stats'),
  getUsers: (params?: { search?: string, role?: string, skip?: number, limit?: number }) => {
    const q = new URLSearchParams();
    if (params) Object.entries(params).forEach(([k, v]) => v !== undefined && q.set(k, String(v)));
    return api(`/admin/users?${q.toString()}`);
  },
  createUser: (data: any) =>
    api(`/admin/users`, { method: 'POST', body: JSON.stringify(data) }),
  updateUser: (id: string, data: any) => 
    api(`/admin/users/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteUser: (id: string) =>
    api(`/admin/users/${id}`, { method: 'DELETE' }),
  
  getSubscriptions: (params?: { status?: string, plan?: string, skip?: number, limit?: number }) => {
    const q = new URLSearchParams();
    if (params) Object.entries(params).forEach(([k, v]) => v !== undefined && q.set(k, String(v)));
    return api(`/admin/subscriptions?${q.toString()}`);
  },
  createSubscription: (data: any) =>
    api(`/admin/subscriptions`, { method: 'POST', body: JSON.stringify(data) }),
  updateSubscription: (id: string, data: any) => 
    api(`/admin/subscriptions/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteSubscription: (id: string) =>
    api(`/admin/subscriptions/${id}`, { method: 'DELETE' }),
    
  getJobs: (params?: { search?: string, status?: string, skip?: number, limit?: number }) => {
    const q = new URLSearchParams();
    if (params) Object.entries(params).forEach(([k, v]) => v !== undefined && q.set(k, String(v)));
    return api(`/admin/jobs?${q.toString()}`);
  },
  createJob: (data: any) =>
    api(`/admin/jobs`, { method: 'POST', body: JSON.stringify(data) }),
  updateJob: (id: string, data: any) => 
    api(`/admin/jobs/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteJob: (id: string) =>
    api(`/admin/jobs/${id}`, { method: 'DELETE' }),
};

export const jobsApi = {
  list: (params?: Record<string, string | undefined>) => {
    const q = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v) q.set(k, v);
      });
    }
    const qs = q.toString();
    return api<any[]>(`/jobs${qs ? `?${qs}` : ''}`, { auth: false });
  },
  mine: () => api<any[]>('/jobs/mine'),
  get: (id: string) => api(`/jobs/${id}`, { auth: false }),
  create: (body: Record<string, unknown>) =>
    api('/jobs', { method: 'POST', body: JSON.stringify(body) }),
  update: (id: string, body: Record<string, unknown>) =>
    api(`/jobs/${id}`, { method: 'PUT', body: JSON.stringify(body) }),
  setStatus: (id: string, status: string) =>
    api(`/jobs/${id}/status`, { method: 'PATCH', body: JSON.stringify({ status }) }),
  candidates: (id: string) => api(`/jobs/${id}/candidates`),
  parseJd: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const headers = new Headers();
    const token = getToken();
    if (token) headers.set('Authorization', `Bearer ${token}`);
    const res = await fetch(`${API_URL}/jobs/parse-jd`, {
      method: 'POST',
      headers,
      body: formData,
    });
    if (!res.ok) {
      let detail = res.statusText;
      try {
        const body = await res.json();
        if (body.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail);
      } catch { /* ignore */ }
      throw new Error(detail);
    }
    return res.json() as Promise<{
      title?: string | null;
      job_role?: string | null;
      job_level?: string | null;
      experience_min?: number | null;
      experience_max?: number | null;
      experience_range?: string | null;
      min_salary?: number | null;
      max_salary?: number | null;
      salary_unit?: string | null;
      country?: string | null;
      state?: string | null;
      city?: string | null;
      location?: string | null;
      employment_type?: string | null;
      job_type?: string | null;
      department?: string | null;
      description?: string | null;
      responsibilities?: string | null;
      requirements?: string | null;
      benefits?: string | null;
      required_skills?: string[];
      parse_source?: string | null;
      parse_warning?: string | null;
    }>;
  },
};

export const resumesApi = {
  list: () => api<any[]>('/resumes'),
  parse: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    
    const headers = new Headers();
    const token = getToken();
    if (token) headers.set('Authorization', `Bearer ${token}`);
    
    const res = await fetch(`${API_URL}/resumes/parse`, {
      method: 'POST',
      headers,
      body: formData,
    });
    if (!res.ok) {
      let detail = res.statusText;
      try {
        const body = await res.json();
        if (body.detail) detail = body.detail;
      } catch {}
      throw new Error(detail);
    }
    return res.json();
  },
  generate: (target_verticals: string[]) =>
    api<any[]>('/resumes/generate', {
      method: 'POST',
      body: JSON.stringify({ target_verticals }),
    }),
  get: (id: string) => api(`/resumes/${id}`),
  regenerate: (id: string) => api(`/resumes/${id}/regenerate`, { method: 'POST' }),
  improve: (id: string) => api(`/resumes/${id}/improve`, { method: 'POST' }),
  downloadPdf: async (id: string, filename?: string) => {
    const headers = new Headers();
    const token = getToken();
    if (token) headers.set('Authorization', `Bearer ${token}`);

    const res = await fetch(`${API_URL}/resumes/${id}/pdf`, { headers });
    if (!res.ok) {
      let detail = res.statusText;
      try {
        const data = await res.json();
        detail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
      } catch { /* ignore */ }
      throw new ApiError(res.status, detail);
    }

    const blob = await res.blob();
    const cd = res.headers.get('Content-Disposition') || '';
    const match = /filename="?([^"]+)"?/i.exec(cd);
    const downloadName = match?.[1] || filename || 'resume.pdf';
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = downloadName;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  },
  downloadTailored: async (targetRole: string, filename?: string) => {
    const headers = new Headers();
    headers.set('Content-Type', 'application/json');
    const token = getToken();
    if (token) headers.set('Authorization', `Bearer ${token}`);

    const res = await fetch(`${API_URL}/resumes/download-tailored`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ target_role: targetRole })
    });
    if (!res.ok) {
      let detail = res.statusText;
      try {
        const body = await res.json();
        if (body.detail) detail = body.detail;
      } catch {}
      throw new Error(detail);
    }
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename || `resume_${targetRole.replace(/\s+/g, '_').toLowerCase()}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  },
};

export const applicationsApi = {
  apply: (job_id: string, resume_id?: string) =>
    api('/applications', {
      method: 'POST',
      body: JSON.stringify({ job_id, resume_id }),
    }),
  mine: () => api<any[]>('/applications/me'),
  forJob: (jobId: string) => api(`/jobs/${jobId}/applications`),
  setStatus: (id: string, status: string) =>
    api(`/applications/${id}/status`, { method: 'PATCH', body: JSON.stringify({ status }) }),
};

export const savedJobsApi = {
  list: () => api<{ job_ids: string[] }>('/saved-jobs/me'),
  save: (jobId: string) => api(`/saved-jobs/${jobId}`, { method: 'POST' }),
  unsave: (jobId: string) => api(`/saved-jobs/${jobId}`, { method: 'DELETE' }),
};

export const hiddenJobsApi = {
  list: () => api<{ job_ids: string[] }>('/jobs/hidden'),
  hide: (jobId: string) => api(`/jobs/${jobId}/hide`, { method: 'POST' }),
  unhide: (jobId: string) => api(`/jobs/${jobId}/hide`, { method: 'DELETE' }),
};

export const messagesApi = {
  threads: () => api<any[]>('/messages/threads'),
  getThread: (id: string) => api<any[]>(`/messages/threads/${id}`),
  send: (threadId: string, body: string, recipientId?: string) =>
    api(`/messages/threads/${threadId}`, {
      method: 'POST',
      body: JSON.stringify({ body, recipient_id: recipientId }),
    }),
  start: (body: string, recipientId: string) =>
    api('/messages/threads', {
      method: 'POST',
      body: JSON.stringify({ body, recipient_id: recipientId }),
    }),
};

export const notificationsApi = {
  mine: () => api('/notifications/me'),
  markRead: (id: string) => api(`/notifications/${id}/read`, { method: 'PATCH' }),
};

export const subscriptionsApi = {
  me: () => api('/subscriptions/me'),
  set: (plan_tier: string) =>
    api('/subscriptions', { method: 'POST', body: JSON.stringify({ plan_tier }) }),
};

export const analyticsApi = {
  candidate: (days: number = 30) =>
    api<import('@/lib/analytics').CandidateAnalytics>(`/analytics/candidate?days=${days}`),
  company: (days: number = 30) =>
    api<import('@/lib/analytics').CompanyAnalytics>(`/analytics/company?days=${days}`),
};

export const uploadsApi = {
  photo: (file: File) => {
    const fd = new FormData();
    fd.append('file', file);
    return api<{ url: string; path: string }>('/uploads/photo', { method: 'POST', formData: fd });
  },
  document: (file: File) => {
    const fd = new FormData();
    fd.append('file', file);
    return api<{ url: string; path: string }>('/uploads/document', { method: 'POST', formData: fd });
  },
};
