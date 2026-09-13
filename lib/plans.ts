export type PlanId =
  | 'basic'
  | 'premium'
  | 'elite'
  | 'starter'
  | 'growth'
  | 'scale'
  | 'free';

export type Role = 'candidate' | 'company';

export interface PlanDefinition {
  id: PlanId;
  name: string;
  description: string;
  priceMonthly: number;
  priceAnnual: number;
  currency: 'USD' | 'INR';
  features: string[];
  popular?: boolean;
  isFree: boolean;
  role: Role;
}

export const CANDIDATE_PLANS: PlanDefinition[] = [
  {
    id: 'basic',
    name: 'Basic',
    description: 'Essential tools for job seekers.',
    priceMonthly: 0,
    priceAnnual: 0,
    currency: 'INR',
    features: [
      'Basic profile creation',
      'Search and apply for jobs',
      '1 target role resume at a time',
      'Limited search filters',
    ],
    isFree: true,
    role: 'candidate',
  },
  {
    id: 'premium',
    name: 'Premium',
    description: 'Maximize your visibility.',
    priceMonthly: 999,
    priceAnnual: 799,
    currency: 'INR',
    features: [
      'Priority placement in search',
      'See who viewed your profile',
      'Multiple simultaneous target roles',
      'Unlimited resume generation',
      'Full job search filters',
      'Cover letter builder',
    ],
    popular: true,
    isFree: false,
    role: 'candidate',
  },
  {
    id: 'elite',
    name: 'Elite',
    description: 'Full access with AI tools.',
    priceMonthly: 1999,
    priceAnnual: 1499,
    currency: 'INR',
    features: [
      'All Premium features',
      'AI-powered cross-domain resume tailoring',
      'Direct messaging with recruiters',
      'Interview prep module',
    ],
    isFree: false,
    role: 'candidate',
  },
];

export const COMPANY_PLANS: PlanDefinition[] = [
  {
    id: 'starter',
    name: 'Starter',
    description: 'Perfect for small teams hiring occasionally.',
    priceMonthly: 0,
    priceAnnual: 0,
    currency: 'INR',
    features: [
      'Up to 2 active job postings',
      'Basic candidate ranking',
      'Limited candidate search filters',
      'Email support',
    ],
    isFree: true,
    role: 'company',
  },
  {
    id: 'growth',
    name: 'Growth',
    description: 'For growing companies with consistent hiring needs.',
    priceMonthly: 4999,
    priceAnnual: 3999,
    currency: 'INR',
    features: [
      'Unlimited job postings',
      'Priority ranking refresh',
      'Full candidate search filters',
      'See full candidate profiles',
      'Direct candidate messaging',
    ],
    popular: true,
    isFree: false,
    role: 'company',
  },
  {
    id: 'scale',
    name: 'Scale',
    description: 'Advanced tools for high-volume recruitment.',
    priceMonthly: 12999,
    priceAnnual: 9999,
    currency: 'INR',
    features: [
      'Everything in Growth',
      'Dedicated account support',
      'Bulk hiring tools',
      'Advanced analytics dashboard',
      'Custom integrations',
    ],
    isFree: false,
    role: 'company',
  },
];

export function getPlansForRole(role: Role): PlanDefinition[] {
  return role === 'company' ? COMPANY_PLANS : CANDIDATE_PLANS;
}

export function getPlanById(id: string | null | undefined): PlanDefinition | undefined {
  if (!id) return undefined;
  const normalized = id === 'free' ? 'basic' : id;
  return [...CANDIDATE_PLANS, ...COMPANY_PLANS].find((p) => p.id === normalized);
}

export function isFreePlan(plan: PlanId | string | null | undefined): boolean {
  if (!plan || plan === 'free' || plan === 'basic' || plan === 'starter') return true;
  const def = getPlanById(plan);
  return def?.isFree ?? true;
}

export function isPaidPlan(plan: PlanId | string | null | undefined): boolean {
  return !isFreePlan(plan);
}

export function planDisplayName(plan: PlanId | string | null | undefined): string {
  const def = getPlanById(plan);
  if (def) return def.name;
  if (!plan || plan === 'free') return 'Basic';
  return String(plan).charAt(0).toUpperCase() + String(plan).slice(1);
}

/** Free/basic: 1 target role at a time. Paid: unlimited. */
export function maxTargetRoles(plan: PlanId | string | null | undefined): number {
  return isFreePlan(plan) ? 1 : Number.POSITIVE_INFINITY;
}

/** Free/starter: 2 job postings. Paid: unlimited. */
export function maxJobPostings(plan: PlanId | string | null | undefined): number {
  return isFreePlan(plan) ? 2 : Number.POSITIVE_INFINITY;
}

/** Free tiers get limited filters on search pages. */
export function hasFullFilters(plan: PlanId | string | null | undefined): boolean {
  return isPaidPlan(plan);
}

export function formatPlanPrice(plan: PlanDefinition, annual: boolean): string {
  const amount = annual ? plan.priceAnnual : plan.priceMonthly;
  if (amount === 0) return plan.currency === 'INR' ? '₹0' : '$0';
  if (plan.currency === 'INR') {
    return `₹${amount.toLocaleString('en-IN')}`;
  }
  return `$${amount}`;
}
