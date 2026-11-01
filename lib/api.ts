/**
 * RoleCraft API client — JWT in localStorage, Bearer on every request.
 *
 * Browser default: same-origin `/backend` (Next.js rewrite → FastAPI) to avoid
 * CORS / Chrome local-network blocks on 127.0.0.1 cross-origin calls.
 * Override with NEXT_PUBLIC_API_URL for production or direct API access.
 */

function resolveApiUrl(): string {
  const configured = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (configured) return configured.replace(/\/$/, "");
  if (typeof window !== "undefined") return "/backend";
  // Server-side: no fallback; will error if NEXT_PUBLIC_API_URL not set at build time
  throw new Error(
    "API URL not configured. Set NEXT_PUBLIC_API_URL environment variable."
  );
}

const API_URL = resolveApiUrl();

// Build-time validation: DISABLED locally, will be checked in CI on Linux with proper production env
// In CI/production, ensure API URL is configured and not localhost
if (process.env.NODE_ENV === "production" && process.env.CI === "true") {
  const url = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (!url) {
    throw new Error(
      "Production build failed: NEXT_PUBLIC_API_URL must be set to a non-localhost URL."
    );
  }
  if (url.includes("localhost") || url.includes("127.0.0.1")) {
    throw new Error(
      `Production build failed: NEXT_PUBLIC_API_URL must not point to localhost. Got: ${url}`
    );
  }
}
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
  type: 'network' | 'validation' | 'server' | 'auth' | 'rate_limit' | 'unknown';
  errorCode?: string;
  retryAfter?: number;

  constructor(status: number, detail: string, errorCode?: string, retryAfter?: number) {
    super(detail);
    this.status = status;
    this.detail = detail;
    this.errorCode = errorCode;
    this.retryAfter = retryAfter;
    this.type = this.classifyError(status);
  }

  private classifyError(status: number): 'network' | 'validation' | 'server' | 'auth' | 'rate_limit' | 'unknown' {
    if (status === 429) return 'rate_limit';
    if (status === 0 || status >= 500) return 'network';
    if (status === 401 || status === 403) return 'auth';
    if (status >= 400 && status < 500) return 'validation';
    if (status >= 500) return 'server';
    return 'unknown';
  }

  // User-friendly message mapping
  getUserMessage(): string {
    if (this.errorCode === 'ai_unavailable') {
      return 'AI service is temporarily unavailable. Please try again in a moment.';
    }
    if (this.errorCode === 'ai_rate_limited') {
      return 'AI service rate limit reached. Please try again in a few minutes.';
    }
    if (this.errorCode === 'ai_timeout') {
      return 'AI request took too long. Please try again with a simpler request.';
    }
    if (this.errorCode === 'plan_required') {
      return 'This feature requires an active subscription. Please upgrade your plan.';
    }
    if (this.errorCode === 'quota_exceeded') {
      return 'You have reached your usage quota. Please upgrade for more.';
    }
    if (this.errorCode === 'plan_expired') {
      return 'Your subscription has expired. Please renew to continue.';
    }
    if (this.type === 'rate_limit') {
      return `Too many requests. Please try again in ${this.retryAfter || 60} seconds.`;
    }
    if (this.type === 'auth' && this.status === 401) {
      return 'Your session has expired. Please sign in again.';
    }
    if (this.type === 'auth' && this.status === 403) {
      return 'You do not have permission to perform this action.';
    }
    if (this.type === 'network') {
      return 'Network error. Please check your connection and try again.';
    }
    return this.detail || 'An error occurred. Please try again.';
  }
}

type Opts = RequestInit & { auth?: boolean; formData?: FormData; retries?: number; signal?: AbortSignal; timeout?: number };

const MAX_RETRIES = 3;
const BASE_DELAY_MS = 1_000;
const MAX_DELAY_MS = 10_000;
const DEFAULT_TIMEOUT_MS = 30_000; // 30 seconds
const AI_TIMEOUT_MS = 90_000; // 90 seconds for AI actions

function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function calculateDelay(attempt: number): number {
  return Math.min(BASE_DELAY_MS * 2 ** attempt, MAX_DELAY_MS);
}

function createTimeoutSignal(timeoutMs: number): AbortSignal {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  
  // Clean up timeout if request completes before timeout
  controller.signal.addEventListener('abort', () => clearTimeout(timeoutId), { once: true });
  
  return controller.signal;
}

export async function api<T = unknown>(path: string, opts: Opts = {}): Promise<T> {
  const { auth, formData, retries, signal, body, headers: optHeaders, timeout, ...fetchInit } = opts;
  const headers = new Headers(optHeaders || {});
  if (!formData && !headers.has('Content-Type') && body) {
    headers.set('Content-Type', 'application/json');
  }
  if (auth !== false) {
    const token = getToken();
    if (token) headers.set('Authorization', `Bearer ${token}`);
  }

  const maxRetries = retries ?? MAX_RETRIES;
  const timeoutMs = timeout ?? (path.includes('/resumes/') || path.includes('/jobs/parse') ? AI_TIMEOUT_MS : DEFAULT_TIMEOUT_MS);
  const finalSignal = signal || createTimeoutSignal(timeoutMs);
  let lastError: Error | null = null;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const res = await fetch(`${API_URL}${path}`, {
        ...fetchInit,
        headers,
        body: formData ?? body,
        signal: finalSignal,
      });

      if (!res.ok) {
        let detail = res.statusText;
        let errorCode: string | undefined;
        let retryAfter: number | undefined;

        // Parse Retry-After header for rate limits
        const retryAfterHeader = res.headers.get('Retry-After');
        if (retryAfterHeader) {
          retryAfter = parseInt(retryAfterHeader, 10);
        }

        try {
          const data = await res.json();
          detail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
          errorCode = data.error_code || data.code;
        } catch {
          /* ignore */
        }
        throw new ApiError(res.status, detail, errorCode, retryAfter);
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

      // Don't retry if request was aborted or timed out
      if (error instanceof DOMException && (error.name === 'AbortError' || error.message.includes('timeout'))) {
        throw new ApiError(0, 'Request timed out. Please try again.');
      }

      // Don't retry on last attempt
      if (attempt === maxRetries) {
        // Surface a clearer message for browser network/CORS failures
        if (!(lastError instanceof ApiError) && /failed to fetch|networkerror|load failed/i.test(lastError.message)) {
          throw new ApiError(
            0,
            `Cannot reach API at ${API_URL}. Is the backend running, and is CORS allowing this origin?`,
          );
        }
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
  resetPassword: (token: string, new_password: string) =>
    api('/auth/reset-password', {
      method: 'POST',
      body: JSON.stringify({ token, new_password }),
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
    return api<any[]>(`/candidates/search${qs ? `?${qs}` : ''}`);
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
    api(`/jobs`, { method: 'POST', body: JSON.stringify(data) }),
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
  regenerate: (id: string) =>
    api(`/resumes/${id}/regenerate`, { method: 'POST', retries: 0 }),
  markCurrent: (id: string) =>
    api(`/resumes/${id}/mark-current`, { method: 'POST', retries: 0 }),
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
    api<any>('/messages/threads', {
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
  logo: (file: File) => {
    const fd = new FormData();
    fd.append('file', file);
    return api<{ url: string; path: string }>('/uploads/logo', { method: 'POST', formData: fd });
  },
  getFileBlob: async (fileUrl: string) => {
    const headers = new Headers();
    const token = getToken();
    if (token) headers.set('Authorization', `Bearer ${token}`);
    const fullUrl = fileUrl.startsWith('http') ? fileUrl : `${API_URL}${fileUrl}`;
    const res = await fetch(fullUrl, { headers });
    if (!res.ok) {
      throw new ApiError(res.status, res.statusText);
    }
    return await res.blob();
  },
};
