"use client";

import React, { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import {
  Search,
  MapPin,
  Briefcase,
  Bookmark,
  BookmarkCheck,
  EyeOff,
  ChevronLeft,
  ChevronRight,
  SlidersHorizontal,
} from 'lucide-react';
import { useUser } from '@/context/UserContext';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/FormField';
import { SearchableCombobox } from '@/components/ui/SearchableCombobox';
import { UpsellPrompt } from '@/components/UpsellPrompt';
import { CITIES, COUNTRIES, EMPLOYMENT_TYPES, JOB_LEVELS, JOB_ROLES, JOB_TYPES, STATES_INDIA } from '@/lib/constants';
import { hasFullFilters } from '@/lib/plans';
import { jobsApi } from '@/lib/api';

const PAGE_SIZE = 5;
const EXPERIENCE_OPTIONS = ['0-1 Years', '1-3 Years', '3-5 Years', '5+ Years'];

function mapJobFromApi(j: any) {
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
    // Backend uses snake_case (job_role / job_level); this mapper is the camelCase boundary.
    // Candidate filters read jobRole — keep in sync with UserContext.mapJob.
    jobRole: j.job_role,
    jobLevel: j.job_level,
    salaryMin: j.min_salary != null ? String(j.min_salary) : '',
    salaryMax: j.max_salary != null ? String(j.max_salary) : '',
    salaryUnit: j.salary_unit || 'Per annum',
    salaryUndisclosed: !j.min_salary && !j.max_salary,
    experience: j.experience_range,
    skills: j.required_skills || [],
    description: j.description,
    status: j.status ? String(j.status).charAt(0).toUpperCase() + String(j.status).slice(1) : 'Draft',
    date: j.created_at?.slice?.(0, 10) || j.created_at,
    // Additional location fields for advanced filtering
    country: j.country,
    state: j.state,
    city: j.city,
  };
}

function daysAgo(dateStr?: string): string {
  if (!dateStr) return 'Recently';
  const d = new Date(dateStr);
  const diff = Math.max(0, Math.floor((Date.now() - d.getTime()) / (1000 * 60 * 60 * 24)));
  if (diff === 0) return 'Posted today';
  if (diff === 1) return 'Posted 1 day ago';
  return `Posted ${diff} days ago`;
}

function formatSalary(job: {
  salaryMin?: string;
  salaryMax?: string;
  salaryUnit?: string;
  salaryUndisclosed?: boolean;
}): string {
  if (job.salaryUndisclosed || (!job.salaryMin && !job.salaryMax)) return 'Salary undisclosed';
  const unit = job.salaryUnit === 'Per month' ? '/mo' : '/yr';
  const fmt = (n: string) => {
    const num = Number(n);
    if (!num) return n;
    if (num >= 100000) return `₹${(num / 100000).toFixed(num % 100000 === 0 ? 0 : 1)}L`;
    return `₹${num.toLocaleString('en-IN')}`;
  };
  if (job.salaryMin && job.salaryMax) return `${fmt(job.salaryMin)} – ${fmt(job.salaryMax)}${unit}`;
  if (job.salaryMin) return `From ${fmt(job.salaryMin)}${unit}`;
  return `Up to ${fmt(job.salaryMax!)}${unit}`;
}

export default function JobSearchPage() {
  const { jobs, savedJobs, toggleSavedJob, hideJob, hiddenJobIds, plan, applyToJob } = useUser();
  const fullFilters = hasFullFilters(plan);

  const [listedJobs, setListedJobs] = useState<any[]>(jobs);
  const [searchTerm, setSearchTerm] = useState('');
  const [applyingId, setApplyingId] = useState<string | null>(null);
  const [location, setLocation] = useState('');
  const [experience, setExperience] = useState('');
  const [jobType, setJobType] = useState('');
  const [salaryBand, setSalaryBand] = useState('');
  const [showMoreFilters, setShowMoreFilters] = useState(false);
  const [employmentType, setEmploymentType] = useState('');
  const [jobRole, setJobRole] = useState('');
  const [jobLevel, setJobLevel] = useState('');
  const [country, setCountry] = useState('');
  const [state, setStateLoc] = useState('');
  const [excludeLocation, setExcludeLocation] = useState('');
  const [sort, setSort] = useState('relevant');
  const [page, setPage] = useState(1);
  const [savedSearchToast, setSavedSearchToast] = useState(false);

  useEffect(() => {
    const params: Record<string, string> = { status: 'live' };
    if (searchTerm.trim()) params.title = searchTerm.trim();
    if (location.trim()) params.location = location.trim();
    if (experience) params.experience_range = experience;
    if (salaryBand && fullFilters) {
      const minLpa =
        salaryBand === '0-8' ? 0 : salaryBand === '8-15' ? 8 : salaryBand === '15-25' ? 15 : 25;
      if (minLpa > 0) params.salary_min = String(minLpa * 100000);
    }
    jobsApi
      .list(params)
      .then((raw) => setListedJobs((raw || []).map(mapJobFromApi)))
      .catch(() => setListedJobs(jobs));
  }, [searchTerm, location, experience, salaryBand, fullFilters, jobs]);

  const filtered = useMemo(() => {
    let list = listedJobs.filter(
      (job) => job.status === 'Live' && !hiddenJobIds.includes(String(job.id))
    );

    const q = searchTerm.trim().toLowerCase();
    if (q) {
      list = list.filter(
        (j) =>
          j.title.toLowerCase().includes(q) ||
          j.companyName.toLowerCase().includes(q) ||
          (j.skills || []).some((s: string) => s.toLowerCase().includes(q))
      );
    }
    if (location) {
      list = list.filter((j) =>
        String(j.location).toLowerCase().includes(location.toLowerCase().split(',')[0])
      );
    }
    if (experience) {
      list = list.filter((j) => String(j.experience || '').includes(experience.split(' ')[0]));
    }
    if (jobType && fullFilters) {
      list = list.filter((j) => j.jobType === jobType || j.employmentType === jobType);
    }
    if (employmentType && fullFilters) {
      list = list.filter((j) => j.employmentType === employmentType);
    }
    if (salaryBand && fullFilters) {
      // Soft filter by min salary bands in LPA (approx)
      const minLpa =
        salaryBand === '0-8' ? 0 : salaryBand === '8-15' ? 8 : salaryBand === '15-25' ? 15 : 25;
      list = list.filter((j) => {
        const max = Number(j.salaryMax || j.salaryMin || 0) / 100000;
        return max === 0 || max >= minLpa;
      });
    }
    if (jobRole && fullFilters) {
      list = list.filter((j) => String(j.jobRole || '').toLowerCase() === jobRole.toLowerCase() || String(j.title).toLowerCase().includes(jobRole.toLowerCase()));
    }
    if (jobLevel && fullFilters) {
      list = list.filter((j) => String(j.jobLevel || '').toLowerCase() === jobLevel.toLowerCase());
    }
    if (country) {
      list = list.filter((j) => String(j.country || j.location || '').toLowerCase().includes(country.toLowerCase()));
    }
    if (state) {
      list = list.filter((j) => String(j.state || j.location || '').toLowerCase().includes(state.toLowerCase()));
    }
    if (excludeLocation && fullFilters) {
      const excludes = excludeLocation.toLowerCase().split(',').map(s => s.trim()).filter(Boolean);
      list = list.filter((j) => {
        const locStr = String(j.location || '') + ' ' + String(j.city || '') + ' ' + String(j.state || '') + ' ' + String(j.country || '');
        return !excludes.some(ex => locStr.toLowerCase().includes(ex));
      });
    }

    if (sort === 'recent') {
      list = [...list].sort((a, b) => String(b.date).localeCompare(String(a.date)));
    }
    return list;
  }, [
    listedJobs,
    hiddenJobIds,
    searchTerm,
    location,
    experience,
    jobType,
    employmentType,
    jobRole,
    jobLevel,
    country,
    state,
    excludeLocation,
    salaryBand,
    sort,
    fullFilters,
  ]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const pageSafe = Math.min(page, totalPages);
  const pageItems = filtered.slice((pageSafe - 1) * PAGE_SIZE, pageSafe * PAGE_SIZE);

  const handleApply = async (job: (typeof jobs)[0]) => {
    setApplyingId(job.id);
    try {
      await applyToJob({
        jobId: job.id,
        jobTitle: job.title,
        companyName: job.companyName,
        status: 'Applied',
        date: new Date().toISOString().split('T')[0],
      });
    } catch {
      alert('You have already applied for this job.');
    } finally {
      setApplyingId(null);
    }
  };

  return (
    <div className="py-8 px-4 md:px-8 max-w-6xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl md:text-3xl font-bold text-foreground">Job Search</h1>
        <p className="text-muted-foreground text-sm mt-1 max-w-2xl">
          Fill in the right opportunities that match your skills and career goals.
        </p>
      </div>

      <Card className="p-4 mb-4 space-y-3">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-3">
          <div className="md:col-span-4 relative">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              className="pl-9"
              placeholder="Search by Job Title, Skill, or Company"
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setPage(1);
              }}
            />
          </div>
          <div className="md:col-span-3 relative">
            <MapPin className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground z-10" />
            <div className="pl-6">
              <SearchableCombobox
                options={[...CITIES]}
                value={location}
                onChange={(v) => {
                  setLocation(v);
                  setPage(1);
                }}
                placeholder="Enter Location"
              />
            </div>
          </div>
          <div className="md:col-span-2">
            <select
              className="w-full h-10 px-3 bg-white border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              value={experience}
              onChange={(e) => {
                setExperience(e.target.value);
                setPage(1);
              }}
            >
              <option value="">Experience</option>
              {EXPERIENCE_OPTIONS.map((o) => (
                <option key={o} value={o}>
                  {o}
                </option>
              ))}
            </select>
          </div>
          <div className="md:col-span-3 flex gap-2">
            <select
              className={`flex-1 h-10 px-3 bg-white border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary ${
                !fullFilters ? 'opacity-60' : ''
              }`}
              value={jobType}
              disabled={!fullFilters}
              onChange={(e) => {
                setJobType(e.target.value);
                setPage(1);
              }}
              title={!fullFilters ? 'Upgrade for full filters' : undefined}
            >
              <option value="">Job Type</option>
              {[...JOB_TYPES, ...EMPLOYMENT_TYPES].map((o) => (
                <option key={o} value={o}>
                  {o}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <select
            className={`h-10 px-3 bg-white border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary ${
              !fullFilters ? 'opacity-60' : ''
            }`}
            value={salaryBand}
            disabled={!fullFilters}
            onChange={(e) => {
              setSalaryBand(e.target.value);
              setPage(1);
            }}
          >
            <option value="">Salary Range</option>
            <option value="0-8">Under ₹8L</option>
            <option value="8-15">₹8L – ₹15L</option>
            <option value="15-25">₹15L – ₹25L</option>
            <option value="25+">₹25L+</option>
          </select>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setSavedSearchToast(true);
              setTimeout(() => setSavedSearchToast(false), 2000);
            }}
          >
            Save Search
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setSearchTerm('');
              setLocation('');
              setExperience('');
              setJobType('');
              setSalaryBand('');
              setEmploymentType('');
              setJobRole('');
              setJobLevel('');
              setCountry('');
              setStateLoc('');
              setExcludeLocation('');
              setPage(1);
            }}
          >
            Clear Filters
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="gap-1.5"
            onClick={() => setShowMoreFilters((s) => !s)}
            disabled={!fullFilters}
          >
            <SlidersHorizontal className="w-3.5 h-3.5" /> More Filters
          </Button>
          {!fullFilters && (
            <span className="text-xs text-muted-foreground">
              Salary & more filters require a paid plan
            </span>
          )}
          <div className="ml-auto text-sm text-primary font-medium opacity-0 transition-opacity duration-300" style={{ opacity: savedSearchToast ? 1 : 0 }}>
            Search criteria saved
          </div>
        </div>

        {showMoreFilters && fullFilters && (
          <div className="pt-3 pb-1 border-t border-border grid grid-cols-1 md:grid-cols-4 gap-3">
            <select
              className="h-10 px-3 bg-white border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              value={employmentType}
              onChange={(e) => {
                setEmploymentType(e.target.value);
                setPage(1);
              }}
            >
              <option value="">Employment Type</option>
              {EMPLOYMENT_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
            <select
              className="h-10 px-3 bg-white border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              value={jobRole}
              onChange={(e) => {
                setJobRole(e.target.value);
                setPage(1);
              }}
            >
              <option value="">Job Role</option>
              {JOB_ROLES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
            <select
              className="h-10 px-3 bg-white border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              value={jobLevel}
              onChange={(e) => {
                setJobLevel(e.target.value);
                setPage(1);
              }}
            >
              <option value="">Job Level</option>
              {JOB_LEVELS.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
            <select
              className="h-10 px-3 bg-white border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              value={country}
              onChange={(e) => {
                setCountry(e.target.value);
                setPage(1);
              }}
            >
              <option value="">Country</option>
              {COUNTRIES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
            <select
              className="h-10 px-3 bg-white border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary"
              value={state}
              onChange={(e) => {
                setStateLoc(e.target.value);
                setPage(1);
              }}
            >
              <option value="">State / Province</option>
              {STATES_INDIA.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
            <div className="md:col-span-2 relative">
              <Input
                className="h-10 text-sm"
                placeholder="Exclude Locations (e.g. Remote, Mumbai)"
                title="-ve Filter: Hide jobs in these locations"
                value={excludeLocation}
                onChange={(e) => {
                  setExcludeLocation(e.target.value);
                  setPage(1);
                }}
              />
            </div>
          </div>
        )}
      </Card>

      {!fullFilters && (
        <UpsellPrompt
          compact
          className="mb-4"
          title="Unlock full search filters"
          description="Upgrade to filter by salary, job type, and more advanced criteria."
        />
      )}

      <div className="flex items-center justify-between mb-4 gap-3">
        <p className="text-sm text-muted-foreground">
          Showing <span className="font-semibold text-foreground">{filtered.length}</span> jobs
        </p>
        <select
          className="h-9 px-3 bg-white border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          value={sort}
          onChange={(e) => setSort(e.target.value)}
        >
          <option value="relevant">Most Relevant</option>
          <option value="recent">Most Recent</option>
        </select>
      </div>

      {pageItems.length === 0 ? (
        <Card className="text-center py-16">
          <Briefcase className="w-12 h-12 text-muted-foreground/40 mx-auto mb-4" />
          <h3 className="text-lg font-bold text-foreground mb-2">No jobs found</h3>
          <p className="text-muted-foreground text-sm">Try broadening your search filters.</p>
        </Card>
      ) : (
        <div className="space-y-4">
          {pageItems.map((job) => {
            const skills: string[] = job.skills || [];
            const shown = skills.slice(0, 3);
            const overflow = skills.length - shown.length;
            const isApplying = applyingId === job.id;
            return (
              <Card key={job.id} className="p-5">
                <div className="flex gap-4">
                  <div className="h-12 w-12 rounded-xl bg-secondary flex items-center justify-center font-bold text-primary shrink-0">
                    {String(job.companyName || '?').charAt(0)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-3">
                      <div>
                        <Link
                          href={`/jobs/${job.id}`}
                          className="text-lg font-bold text-foreground hover:text-primary"
                        >
                          {job.title}
                        </Link>
                        <p className="text-sm text-muted-foreground mt-0.5">{job.companyName}</p>
                        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                          <span>{job.experience || 'Experience flexible'}</span>
                          <span className="inline-flex items-center gap-1">
                            <MapPin className="w-3 h-3" /> {job.location}
                          </span>
                          <span>{job.employmentType}</span>
                          <span className="font-medium text-foreground/80">{formatSalary(job)}</span>
                        </div>
                        <div className="mt-3 flex flex-wrap gap-1.5">
                          {shown.map((s) => (
                            <span
                              key={s}
                              className="text-xs px-2 py-0.5 rounded-md bg-secondary text-foreground/80"
                            >
                              {s}
                            </span>
                          ))}
                          {overflow > 0 && (
                            <span className="text-xs px-2 py-0.5 rounded-md bg-secondary text-muted-foreground">
                              +{overflow}
                            </span>
                          )}
                        </div>
                        <p className="mt-2 text-xs text-muted-foreground">{daysAgo(job.date)}</p>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <button
                          type="button"
                          className="h-9 w-9 inline-flex items-center justify-center rounded-lg border border-border text-muted-foreground hover:text-primary hover:border-primary/40"
                          onClick={() => toggleSavedJob(job.id)}
                          aria-label="Save job"
                        >
                          {savedJobs.includes(String(job.id)) ? (
                            <BookmarkCheck className="w-4 h-4 text-primary" />
                          ) : (
                            <Bookmark className="w-4 h-4" />
                          )}
                        </button>
                        <button
                          type="button"
                          className="h-9 w-9 inline-flex items-center justify-center rounded-lg border border-border text-muted-foreground hover:text-red-500 hover:border-red-300"
                          onClick={() => hideJob(job.id)}
                          aria-label="Hide job"
                          title="Hide this job from search"
                        >
                          <EyeOff className="w-4 h-4" />
                        </button>
                        <Button size="sm" onClick={() => handleApply(job)} disabled={isApplying}>
                          {isApplying ? (
                            <><span className="w-4 h-4 mr-2 border-2 border-white/30 border-t-white rounded-full animate-spin inline-block" /> Tailoring Resume...</>
                          ) : 'Apply Now'}
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {filtered.length > 0 && (
        <div className="mt-8 flex items-center justify-center gap-2">
          <button
            type="button"
            disabled={pageSafe <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            className="h-9 w-9 inline-flex items-center justify-center rounded-lg border border-border disabled:opacity-40"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          {Array.from({ length: totalPages }, (_, i) => i + 1).map((n) => (
            <button
              key={n}
              type="button"
              onClick={() => setPage(n)}
              className={`h-9 w-9 rounded-lg text-sm font-medium ${
                n === pageSafe
                  ? 'bg-primary text-primary-foreground'
                  : 'border border-border text-foreground hover:bg-secondary'
              }`}
            >
              {n}
            </button>
          ))}
          <button
            type="button"
            disabled={pageSafe >= totalPages}
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            className="h-9 w-9 inline-flex items-center justify-center rounded-lg border border-border disabled:opacity-40"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
}
