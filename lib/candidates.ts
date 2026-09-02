export interface SearchCandidate {
  id: string | number;
  name: string;
  title: string;
  experienceYears: number;
  location: string;
  skills: string[];
  matchPercent: number;
  education: string;
  expectedSalaryLpa: number;
  noticePeriodDays: number;
  /** Same shape as API template rationale (not LLM-generated). */
  rationale?: string | null;
}

/** Mirrors apps/api candidate_search_service / fitment_service template strings. */
export function templateFitmentRationale(skills: string[]): string {
  const top = skills.slice(0, 3);
  return top.length
    ? `Strong skills overlap in ${top.join(', ')}.`
    : 'Profile match based on experience and vertical alignment.';
}

export const SEED_CANDIDATES: SearchCandidate[] = [
  {
    id: 201,
    name: 'Ananya Reddy',
    title: 'Senior UX Designer',
    experienceYears: 5,
    location: 'Bangalore',
    skills: ['Figma', 'UI Design', 'Prototyping', 'User Research', 'Design Systems'],
    matchPercent: 92,
    education: 'Masters',
    expectedSalaryLpa: 18,
    noticePeriodDays: 30,
    rationale: templateFitmentRationale(['Figma', 'UI Design', 'Prototyping']),
  },
  {
    id: 202,
    name: 'Rahul Mehta',
    title: 'Frontend Engineer',
    experienceYears: 4,
    location: 'Bangalore',
    skills: ['React', 'TypeScript', 'Next.js', 'Tailwind CSS', 'Git'],
    matchPercent: 88,
    education: 'Bachelors',
    expectedSalaryLpa: 22,
    noticePeriodDays: 60,
    rationale: templateFitmentRationale(['React', 'TypeScript', 'Next.js']),
  },
  {
    id: 203,
    name: 'Priya Sharma',
    title: 'Marketing Specialist',
    experienceYears: 3,
    location: 'Mumbai',
    skills: ['Content Marketing', 'SEO', 'Google Analytics', 'Social Media', 'Copywriting'],
    matchPercent: 81,
    education: 'Bachelors',
    expectedSalaryLpa: 10,
    noticePeriodDays: 15,
    rationale: templateFitmentRationale(['Content Marketing', 'SEO', 'Google Analytics']),
  },
  {
    id: 204,
    name: 'Karthik Iyer',
    title: 'Electronics Design Engineer',
    experienceYears: 2,
    location: 'Hyderabad',
    skills: ['Circuit Design', 'Embedded C', 'MATLAB', 'PCB Design', 'Python'],
    matchPercent: 76,
    education: 'Bachelors',
    expectedSalaryLpa: 8,
    noticePeriodDays: 45,
    rationale: templateFitmentRationale(['Circuit Design', 'Embedded C', 'MATLAB']),
  },
  {
    id: 205,
    name: 'Sneha Kapoor',
    title: 'Product Designer',
    experienceYears: 6,
    location: 'Remote',
    skills: ['Figma', 'UX Design', 'Wireframing', 'User Research', 'Photoshop'],
    matchPercent: 95,
    education: 'Masters',
    expectedSalaryLpa: 24,
    noticePeriodDays: 30,
    rationale: templateFitmentRationale(['Figma', 'UX Design', 'Wireframing']),
  },
  {
    id: 206,
    name: 'Amit Patel',
    title: 'Backend Developer',
    experienceYears: 3,
    location: 'Pune',
    skills: ['Node.js', 'PostgreSQL', 'AWS', 'Docker', 'Python'],
    matchPercent: 72,
    education: 'Bachelors',
    expectedSalaryLpa: 14,
    noticePeriodDays: 90,
    rationale: templateFitmentRationale(['Node.js', 'PostgreSQL', 'AWS']),
  },
  {
    id: 207,
    name: 'Neha Gupta',
    title: 'Sales Executive',
    experienceYears: 4,
    location: 'Delhi NCR',
    skills: ['Salesforce', 'Lead Generation', 'Negotiation', 'CRM', 'Client Relations'],
    matchPercent: 68,
    education: 'Bachelors',
    expectedSalaryLpa: 12,
    noticePeriodDays: 30,
    rationale: templateFitmentRationale(['Salesforce', 'Lead Generation', 'Negotiation']),
  },
  {
    id: 208,
    name: 'Vikram Singh',
    title: 'Data Analyst',
    experienceYears: 2,
    location: 'Bangalore',
    skills: ['SQL', 'Python', 'Google Analytics', 'Excel', 'Communication'],
    matchPercent: 84,
    education: 'Masters',
    expectedSalaryLpa: 11,
    noticePeriodDays: 0,
    rationale: templateFitmentRationale(['SQL', 'Python', 'Google Analytics']),
  },
];
export function matchLabel(pct: number): { label: string; tone: string } {
  if (pct >= 85) return { label: 'Excellent Match', tone: 'text-green-700 bg-green-50 border-green-200' };
  if (pct >= 70) return { label: 'Good Match', tone: 'text-emerald-700 bg-emerald-50 border-emerald-200' };
  if (pct >= 50) return { label: 'Fair Match', tone: 'text-amber-700 bg-amber-50 border-amber-200' };
  return { label: 'Low Match', tone: 'text-ink-muted bg-surface-soft border-border-soft' };
}
