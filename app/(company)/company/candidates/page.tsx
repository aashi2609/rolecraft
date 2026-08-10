"use client";

import React, { useMemo, useState } from 'react';
import Link from 'next/link';
import {
  Search,
  MapPin,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  SlidersHorizontal,
  MoreHorizontal,
  X,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/FormField';
import { SearchableCombobox } from '@/components/ui/SearchableCombobox';
import { RangeSlider } from '@/components/ui/RangeSlider';
import { UpsellPrompt } from '@/components/UpsellPrompt';
import { CandidateProfileModal } from '@/components/company/CandidateProfileModal';
import { MessageModal } from '@/components/company/MessageModal';
import { useUser } from '@/context/UserContext';
import { useToast } from '@/components/ui/Toast';
import { useOffline } from '@/hooks/useOffline';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { CANDIDATE_LOCATIONS, SKILLS, VERTICALS, EDUCATION_LEVELS } from '@/lib/constants';
import { matchLabel, SEED_CANDIDATES } from '@/lib/candidates';
import { hasFullFilters } from '@/lib/plans';
import { candidateApi, ApiError } from '@/lib/api';

const PAGE_SIZE = 5;

export default function SearchCandidatesPage() {
  const { plan } = useUser();
  const { showToast } = useToast();
  const isOffline = useOffline();
  const fullFilters = true; // Temporary: enable all filters for testing regardless of plan

  const [search, setSearch] = useState('');
  const [locationQuery, setLocationQuery] = useState('');
  const [view, setView] = useState<'candidates' | 'saved'>('candidates');
  const [sort, setSort] = useState('match');
  const [page, setPage] = useState(1);
  const [showMobileFilters, setShowMobileFilters] = useState(false);
  const [loading, setLoading] = useState(false);
  const [candidates, setCandidates] = useState<any[]>([]);

  // Warn user if offline
  React.useEffect(() => {
    if (isOffline) {
      showToast('warning', 'You are offline. Some features may not work properly.');
    }
  }, [isOffline, showToast]);

  // Applied filters (committed on Apply Filters)
  const [locations, setLocations] = useState<string[]>([]);
  const [jobTitle, setJobTitle] = useState('');
  const [expRange, setExpRange] = useState<[number, number]>([0, 10]);
  const [skills, setSkills] = useState<string[]>([]);
  const [salaryRange, setSalaryRange] = useState<[number, number]>([4, 30]);
  const [education, setEducation] = useState<string[]>([]);
  const [noticeDate, setNoticeDate] = useState('');

  // Draft filters in sidebar
  const [draftLocations, setDraftLocations] = useState<string[]>([]);
  const [draftTitle, setDraftTitle] = useState('');
  const [draftExp, setDraftExp] = useState<[number, number]>([0, 10]);
  const [draftSkills, setDraftSkills] = useState<string[]>([]);
  const [draftSalary, setDraftSalary] = useState<[number, number]>([4, 30]);
  const [draftEducation, setDraftEducation] = useState<string[]>([]);
  const [draftNotice, setDraftNotice] = useState('');

  const [openSections, setOpenSections] = useState<Record<string, boolean>>({
    location: true,
    title: true,
    experience: true,
    skills: true,
    salary: true,
    education: false,
    notice: false,
  });

  const [selectedCandidate, setSelectedCandidate] = useState<(typeof candidates)[0] | null>(null);
  const [profileOpen, setProfileOpen] = useState(false);
  const [messageOpen, setMessageOpen] = useState(false);
  const [messageName, setMessageName] = useState('');
  const [menuOpenId, setMenuOpenId] = useState<string | number | null>(null);
  const [shortlisted, setShortlisted] = useState<(string | number)[]>([]);
  const [hidden, setHidden] = useState<(string | number)[]>([]);
  const [savedIds, setSavedIds] = useState<(string | number)[]>([]);

  // Fetch candidates from API
  const fetchCandidates = async () => {
    setLoading(true);
    try {
      const params: Record<string, string | number | undefined> = {
        page,
        page_size: PAGE_SIZE,
      };
      
      if (search.trim()) params.q = search.trim();
      if (locationQuery) params.location = locationQuery;
      if (skills.length) params.skills = skills.join(',');
      if (jobTitle) params.title = jobTitle;
      if (expRange[0] > 0) params.experience_min = expRange[0];
      if (expRange[1] < 10) params.experience_max = expRange[1];
      if (salaryRange[0] > 4) params.salary_min = salaryRange[0];
      if (salaryRange[1] < 30) params.salary_max = salaryRange[1];
      if (education.length) params.education = education.join(',');
      
      const data = await candidateApi.search(params);
      
      const transformed = data.map((c: any) => ({
        id: c.id,
        name: c.name || 'Candidate',
        title: c.title || 'Professional',
        experienceYears: c.experience_years || 0,
        location: c.location || 'Remote',
        skills: c.skills || [],
        matchPercent: c.match_percent || 70,
        education: c.education || 'Bachelor\'s',
        expectedSalaryLpa: c.expected_salary_lpa || 10,
        noticePeriodDays: c.notice_period_days || 30,
      }));
      
      setCandidates(transformed);
    } catch (err: any) {
      console.error('Failed to fetch candidates:', err);
      
      if (err instanceof ApiError) {
        switch (err.type) {
          case 'network':
            showToast('error', 'Network error. Using offline data.');
            break;
          case 'auth':
            showToast('error', 'Authentication failed. Please sign in again.');
            break;
          case 'validation':
            showToast('warning', 'Invalid search parameters.');
            break;
          default:
            showToast('error', 'Failed to load candidates. Using offline data.');
        }
      } else {
        showToast('error', 'Unexpected error occurred.');
      }
      
      // Fallback gracefully to seed data on connection or backend error
      setCandidates(SEED_CANDIDATES);
    } finally {
      setLoading(false);
    }
  };

  // Fetch candidates on mount and when filters change
  React.useEffect(() => {
    fetchCandidates();
  }, [
    page,
    search,
    locationQuery,
    skills.join(','),
    jobTitle,
    expRange.join(','),
    salaryRange.join(','),
    education.join(','),
    locations.join(','),
  ]);

  const applyFilters = () => {
    if (!fullFilters) return;
    setLocations(draftLocations);
    setJobTitle(draftTitle);
    setExpRange(draftExp);
    setSkills(draftSkills);
    setSalaryRange(draftSalary);
    setEducation(draftEducation);
    setNoticeDate(draftNotice);
    setPage(1);
    setShowMobileFilters(false);
  };

  const clearAll = () => {
    setLocations([]);
    setJobTitle('');
    setExpRange([0, 10]);
    setSkills([]);
    setSalaryRange([4, 30]);
    setEducation([]);
    setNoticeDate('');
    setDraftLocations([]);
    setDraftTitle('');
    setDraftExp([0, 10]);
    setDraftSkills([]);
    setDraftSalary([4, 30]);
    setDraftEducation([]);
    setDraftNotice('');
    setSearch('');
    setLocationQuery('');
    setPage(1);
  };

  const filtered = useMemo(() => {
    let list = candidates.filter((c) => !hidden.includes(c.id));

    if (view === 'saved') {
      list = list.filter((c) => savedIds.includes(c.id));
    }

    if (sort === 'match') list = [...list].sort((a, b) => b.matchPercent - a.matchPercent);
    if (sort === 'exp') list = [...list].sort((a, b) => b.experienceYears - a.experienceYears);
    return list;
  }, [
    candidates,
    hidden,
    view,
    savedIds,
    sort,
  ]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const pageSafe = Math.min(page, totalPages);
  const pageItems = filtered;

  const FilterPanel = (
    <div className="space-y-1">
      <h2 className="text-base font-bold text-foreground mb-4">Filter Result</h2>

      {!fullFilters && (
        <UpsellPrompt
          compact
          className="mb-4"
          title="Limited filters on free plan"
          description="Upgrade to use location, salary, education, and notice period filters."
        />
      )}

      {/* Location */}
      <FilterSection
        title="Desired Location"
        open={openSections.location}
        onToggle={() => setOpenSections((s) => ({ ...s, location: !s.location }))}
      >
        <div className="space-y-2">
          {CANDIDATE_LOCATIONS.map((loc) => (
            <label key={loc} className={`flex items-center gap-2 text-sm ${!fullFilters ? 'opacity-50' : ''}`}>
              <input
                type="checkbox"
                disabled={!fullFilters}
                checked={draftLocations.includes(loc)}
                onChange={() =>
                  setDraftLocations((prev) =>
                    prev.includes(loc) ? prev.filter((x) => x !== loc) : [...prev, loc]
                  )
                }
                className="accent-primary"
              />
              {loc}
            </label>
          ))}
        </div>
      </FilterSection>

      <FilterSection
        title="Job Title"
        open={openSections.title}
        onToggle={() => setOpenSections((s) => ({ ...s, title: !s.title }))}
      >
        <SearchableCombobox
          options={[...VERTICALS]}
          value={draftTitle}
          onChange={setDraftTitle}
          placeholder="e.g. UI/UX Designer"
        />
      </FilterSection>

      <FilterSection
        title="Experience"
        open={openSections.experience}
        onToggle={() => setOpenSections((s) => ({ ...s, experience: !s.experience }))}
      >
        <RangeSlider
          min={0}
          max={15}
          value={draftExp}
          onChange={setDraftExp}
          formatLabel={(n) => `${n} yrs`}
        />
      </FilterSection>

      <FilterSection
        title="Skills"
        open={openSections.skills}
        onToggle={() => setOpenSections((s) => ({ ...s, skills: !s.skills }))}
      >
        <SearchableCombobox
          multiSelect
          options={[...SKILLS]}
          value={draftSkills}
          onChange={setDraftSkills}
          placeholder="Add skills"
        />
      </FilterSection>

      <FilterSection
        title="Expected Salary"
        open={openSections.salary}
        onToggle={() => setOpenSections((s) => ({ ...s, salary: !s.salary }))}
      >
        <div className={!fullFilters ? 'opacity-50 pointer-events-none' : ''}>
          <RangeSlider
            min={2}
            max={40}
            value={draftSalary}
            onChange={setDraftSalary}
            formatLabel={(n) => `₹${n}L`}
          />
          <p className="text-xs text-muted-foreground mt-1">per annum</p>
        </div>
      </FilterSection>

      <FilterSection
        title="Education"
        open={openSections.education}
        onToggle={() => setOpenSections((s) => ({ ...s, education: !s.education }))}
      >
        <div className="space-y-2">
          {EDUCATION_LEVELS.filter((e) => e === 'Bachelors' || e === 'Masters').map((ed) => (
            <label key={ed} className={`flex items-center gap-2 text-sm ${!fullFilters ? 'opacity-50' : ''}`}>
              <input
                type="checkbox"
                disabled={!fullFilters}
                checked={draftEducation.includes(ed)}
                onChange={() =>
                  setDraftEducation((prev) =>
                    prev.includes(ed) ? prev.filter((x) => x !== ed) : [...prev, ed]
                  )
                }
                className="accent-primary"
              />
              {ed}
            </label>
          ))}
        </div>
      </FilterSection>

      <FilterSection
        title="Notice Period"
        open={openSections.notice}
        onToggle={() => setOpenSections((s) => ({ ...s, notice: !s.notice }))}
      >
        <Input
          type="date"
          disabled={!fullFilters}
          value={draftNotice}
          onChange={(e) => setDraftNotice(e.target.value)}
        />
      </FilterSection>

      <Button className="w-full mt-4" onClick={applyFilters} disabled={!fullFilters && false}>
        Apply Filters
      </Button>
      {!fullFilters && (
        <p className="text-xs text-muted-foreground mt-2 text-center">
          Basic search works free — advanced sidebar filters need a paid plan.
        </p>
      )}
    </div>
  );

  return (
    <div className="py-6 px-4 md:px-8 max-w-7xl mx-auto h-[calc(100vh-56px)] overflow-hidden">
      <div className="flex flex-col lg:flex-row gap-6 h-full">
        {/* Desktop filter sidebar */}
        <aside className="hidden lg:block w-72 shrink-0 h-full pb-8">
          <Card className="p-5 h-full overflow-y-auto scrollbar-none hover:scrollbar-thin transition-colors">
            {FilterPanel}
          </Card>
        </aside>

        <div className="flex-1 min-w-0 h-full overflow-y-auto pb-8 pr-2 scrollbar-none hover:scrollbar-thin transition-colors">
          <h1 className="text-2xl md:text-3xl font-bold text-foreground mb-1">Search Candidate</h1>
          <p className="text-sm text-muted-foreground mb-5">
            Browse and filter candidates across all roles — not scoped to a single job.
          </p>

          <Card className="p-4 mb-4">
            <div className="flex flex-col md:flex-row gap-3">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  className="pl-9"
                  placeholder="Search by name, title, or skill"
                  value={search}
                  onChange={(e) => {
                    setSearch(e.target.value);
                    setPage(1);
                  }}
                />
              </div>
              <div className="relative md:w-56">
                <MapPin className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  className="pl-9"
                  placeholder="Location"
                  value={locationQuery}
                  onChange={(e) => {
                    setLocationQuery(e.target.value);
                    setPage(1);
                  }}
                />
              </div>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant={view === 'candidates' ? 'primary' : 'outline'}
                  onClick={() => setView('candidates')}
                >
                  Candidates
                </Button>
                <Button
                  size="sm"
                  variant={view === 'saved' ? 'primary' : 'outline'}
                  onClick={() => setView('saved')}
                >
                  Saved Searches
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  className="lg:hidden gap-1"
                  onClick={() => setShowMobileFilters(true)}
                >
                  <SlidersHorizontal className="w-3.5 h-3.5" /> More Filters
                </Button>
              </div>
            </div>
          </Card>

          <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
            <p className="text-sm text-muted-foreground">
              Found <span className="font-semibold text-foreground">{filtered.length}</span> Candidates
            </p>
            <div className="flex items-center gap-2">
              <select
                className="h-9 px-3 bg-white border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                value={sort}
                onChange={(e) => setSort(e.target.value)}
              >
                <option value="match">Sort by Match</option>
                <option value="exp">Sort by Experience</option>
              </select>
              <Button variant="ghost" size="sm" onClick={clearAll} className="gap-1">
                <X className="w-3.5 h-3.5" /> Clear All
              </Button>
            </div>
          </div>

          {loading ? (
            <Card className="text-center py-16">
              <LoadingSpinner size="lg" className="mx-auto mb-3" />
              <p className="text-muted-foreground text-sm">Loading candidates...</p>
            </Card>
          ) : pageItems.length === 0 ? (
            <Card className="text-center py-16">
              <h3 className="text-lg font-bold text-foreground mb-2">No candidates found</h3>
              <p className="text-muted-foreground text-sm">Try adjusting filters or clearing all.</p>
            </Card>
          ) : (
            <div className="space-y-4">
              {pageItems.map((c) => {
                const shown = c.skills.slice(0, 3);
                const overflow = c.skills.length - shown.length;
                const match = matchLabel(c.matchPercent);
                return (
                  <Card key={c.id} className="p-5 relative">
                    <div className="flex gap-4">
                      <div className="h-12 w-12 rounded-full bg-primary/10 text-primary font-bold flex items-center justify-center shrink-0">
                        {c.name
                          .split(' ')
                          .map((n: string) => n[0])
                          .join('')
                          .slice(0, 2)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-3">
                          <div>
                            <h3 className="text-lg font-bold text-foreground">{c.name}</h3>
                            <p className="text-sm text-muted-foreground">{c.title}</p>
                            <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                              <span>{c.experienceYears} years experience</span>
                              <span className="inline-flex items-center gap-1">
                                <MapPin className="w-3 h-3" /> {c.location}
                              </span>
                            </div>
                            <div className="mt-3 flex flex-wrap gap-1.5">
                              {shown.map((s: string) => (
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
                          </div>
                          <div className="flex flex-col items-end gap-3 shrink-0">
                            <div
                              className={`h-16 w-16 rounded-full border-2 flex flex-col items-center justify-center text-center ${match.tone}`}
                            >
                              <span className="text-sm font-bold leading-none">{c.matchPercent}%</span>
                              <span className="text-[9px] font-medium leading-tight mt-0.5 px-1">
                                {match.label}
                              </span>
                            </div>
                            <div className="flex items-center gap-2">
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => {
                                  setSelectedCandidate(c);
                                  setProfileOpen(true);
                                }}
                              >
                                View Profile
                              </Button>
                              <Button size="sm" variant="outline">
                                View Resume
                              </Button>
                              <div className="relative">
                                <button
                                  type="button"
                                  className="h-9 w-9 inline-flex items-center justify-center rounded-lg border border-border"
                                  onClick={() =>
                                    setMenuOpenId(menuOpenId === c.id ? null : c.id)
                                  }
                                >
                                  <MoreHorizontal className="w-4 h-4" />
                                </button>
                                {menuOpenId === c.id && (
                                  <div className="absolute right-0 top-10 z-20 w-40 rounded-lg border border-border bg-white shadow-md py-1">
                                    <button
                                      type="button"
                                      className="w-full text-left px-3 py-2 text-sm hover:bg-secondary"
                                      onClick={() => {
                                        setShortlisted((prev) =>
                                          prev.includes(c.id)
                                            ? prev.filter((x) => x !== c.id)
                                            : [...prev, c.id]
                                        );
                                        setSavedIds((prev) =>
                                          prev.includes(c.id) ? prev : [...prev, c.id]
                                        );
                                        setMenuOpenId(null);
                                      }}
                                    >
                                      {shortlisted.includes(c.id) ? 'Shortlisted' : 'Shortlist'}
                                    </button>
                                    <button
                                      type="button"
                                      className="w-full text-left px-3 py-2 text-sm hover:bg-secondary"
                                      onClick={() => {
                                        setMessageName(c.name);
                                        setMessageOpen(true);
                                        setMenuOpenId(null);
                                      }}
                                    >
                                      Message
                                    </button>
                                    <button
                                      type="button"
                                      className="w-full text-left px-3 py-2 text-sm hover:bg-secondary text-red-600"
                                      onClick={() => {
                                        setHidden((prev) => [...prev, c.id]);
                                        setMenuOpenId(null);
                                      }}
                                    >
                                      Hide
                                    </button>
                                  </div>
                                )}
                              </div>
                            </div>
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
      </div>

      {/* Mobile filters drawer */}
      {showMobileFilters && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="absolute inset-0 bg-black/40"
            onClick={() => setShowMobileFilters(false)}
          />
          <div className="absolute right-0 top-0 bottom-0 w-full max-w-sm bg-white p-5 overflow-y-auto shadow-xl">
            <div className="flex justify-between items-center mb-4">
              <h2 className="font-bold">Filters</h2>
              <button type="button" onClick={() => setShowMobileFilters(false)}>
                <X className="w-5 h-5" />
              </button>
            </div>
            {FilterPanel}
          </div>
        </div>
      )}

      <CandidateProfileModal
        isOpen={profileOpen}
        onClose={() => setProfileOpen(false)}
        candidate={
          selectedCandidate
            ? {
                id: selectedCandidate.id,
                name: selectedCandidate.name,
                fitment: `${selectedCandidate.matchPercent}%`,
                rationale: `Strong overlap on ${selectedCandidate.skills.slice(0, 2).join(', ')} for ${selectedCandidate.title} roles.`,
                vertical: selectedCandidate.title,
                badgeColor: 'bg-green-100 text-green-700',
                isShortlisted: shortlisted.includes(selectedCandidate.id),
              }
            : null
        }
      />
      <MessageModal
        isOpen={messageOpen}
        onClose={() => setMessageOpen(false)}
        candidateName={messageName}
      />
    </div>
  );
}

function FilterSection({
  title,
  open,
  onToggle,
  children,
}: {
  title: string;
  open: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="border-b border-border py-3">
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center justify-between text-sm font-semibold text-foreground"
      >
        {title}
        <ChevronDown className={`w-4 h-4 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && <div className="mt-3">{children}</div>}
    </div>
  );
}
