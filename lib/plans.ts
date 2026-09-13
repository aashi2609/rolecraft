export type PlanId =
  | 'resume_builder'
  | 'job_search'
  | 'complete'
  | 'corporate_annual'
  | 'corporate_lifetime';

export type Role = 'candidate' | 'company';

export interface PlanDefinition {
  id: PlanId;
  name: string;
  description: string;
  priceMonthly: number;
  priceAnnual: number;
  currency: 'INR';
  features: string[];
  popular?: boolean;
  isFree: boolean;
  role: Role;
  billingText?: {
    monthly: string;
    annual: string;
  };
}

export const CANDIDATE_PLANS: PlanDefinition[] = [
  {
    id: 'resume_builder',
    name: 'Resume Builder',
    description: 'AI resume generation & tailoring for job seekers with existing job avenues.',
    priceMonthly: 499,
    priceAnnual: 399,
    currency: 'INR',
    features: [
      'Profile onboarding & management',
      'AI-tailored resume generation across verticals',
      'ATS score optimization & breakdown',
      'Instant PDF export & downloads',
      'No job application features',
    ],
    isFree: false,
    role: 'candidate',
  },
  {
    id: 'job_search',
    name: 'Job Search',
    description: 'Job application & AI matching for candidates with a ready resume.',
    priceMonthly: 399,
    priceAnnual: 299,
    currency: 'INR',
    features: [
      'Browse & search all active job postings',
      'AI job matches & fitment rationales',
      'One-click job applications (using uploaded resume)',
      'Saved jobs & application status tracking',
      'Direct messaging with hiring teams',
    ],
    isFree: false,
    role: 'candidate',
  },
  {
    id: 'complete',
    name: 'Complete',
    description: 'Full access to both AI resume generation and job application/matching.',
    priceMonthly: 799,
    priceAnnual: 599,
    currency: 'INR',
    features: [
      'All Resume Builder features',
      'All Job Search features',
      'Unlimited AI resume tailoring per application',
      'Priority recruiter visibility & badge',
      'Full search filters & interview prep insights',
    ],
    popular: true,
    isFree: false,
    role: 'candidate',
  },
];

export const COMPANY_PLANS: PlanDefinition[] = [
  {
    id: 'corporate_annual',
    name: 'Corporate Annual',
    description: 'Complete recruitment suite billed annually.',
    priceMonthly: 29999, // displayed as Annual ₹29,999/yr
    priceAnnual: 29999,
    currency: 'INR',
    features: [
      'Unlimited job postings',
      'AI candidate search & smart matching',
      'Full candidate profile viewing',
      'Direct candidate messaging',
      'Standard support',
    ],
    isFree: false,
    role: 'company',
  },
  {
    id: 'corporate_lifetime',
    name: 'Corporate Lifetime',
    description: 'Lifetime unlimited recruitment access — pay once, use forever.',
    priceMonthly: 79999, // displayed as Lifetime ₹79,999
    priceAnnual: 79999,
    currency: 'INR',
    features: [
      'Everything in Corporate Annual',
      'Lifetime unlimited job postings & search',
      'Zero recurring monthly or annual fees',
      'Featured employer branding & placement',
      'Dedicated account support',
    ],
    popular: true,
    isFree: false,
    role: 'company',
  },
];

export function getPlansForRole(role: Role): PlanDefinition[] {
  return role === 'company' ? COMPANY_PLANS : CANDIDATE_PLANS;
}

export function getPlanById(id: string | null | undefined): PlanDefinition | undefined {
  if (!id) return undefined;
  // Normalize legacy plan names if any exist
  let normalized = id;
  if (id === 'free' || id === 'basic') normalized = 'complete';
  if (id === 'starter' || id === 'growth' || id === 'scale') normalized = 'corporate_annual';
  return [...CANDIDATE_PLANS, ...COMPANY_PLANS].find((p) => p.id === normalized);
}

export function isFreePlan(_plan: PlanId | string | null | undefined): boolean {
  return false;
}

export function isPaidPlan(_plan: PlanId | string | null | undefined): boolean {
  return true;
}

export function planDisplayName(plan: PlanId | string | null | undefined): string {
  const def = getPlanById(plan);
  if (def) return def.name;
  return String(plan || 'Complete').replace('_', ' ').replace(/\b\w/g, (l) => l.toUpperCase());
}

export function maxTargetRoles(_plan: PlanId | string | null | undefined): number {
  return Number.POSITIVE_INFINITY;
}

export function maxJobPostings(_plan: PlanId | string | null | undefined): number {
  return Number.POSITIVE_INFINITY;
}

export function hasFullFilters(_plan: PlanId | string | null | undefined): boolean {
  return true;
}

export function formatPlanPrice(plan: PlanDefinition, annual: boolean): string {
  if (plan.role === 'company') {
    const amount = plan.id === 'corporate_lifetime' ? plan.priceAnnual : annual ? plan.priceAnnual : plan.priceMonthly;
    return `₹${amount.toLocaleString('en-IN')}`;
  }
  const amount = annual ? plan.priceAnnual : plan.priceMonthly;
  return `₹${amount.toLocaleString('en-IN')}`;
}

