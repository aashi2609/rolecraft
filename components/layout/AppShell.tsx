"use client";

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import {
  LayoutDashboard,
  Briefcase,
  FileText,
  MessageSquare,
  User,
  BarChart3,
  Settings,
  ChevronDown,
  ChevronRight,
  PlusCircle,
  Users,
  ClipboardList,
  Bookmark,
  LogOut,
} from 'lucide-react';
import { Logo } from '@/components/Logo';
import { useUser } from '@/context/UserContext';
import { planDisplayName, isFreePlan } from '@/lib/plans';
import { Button } from '@/components/ui/Button';
import { NotificationsDropdown } from '@/components/ui/NotificationsDropdown';
import { cn } from '@/lib/utils';

type NavItem = {
  label: string;
  href?: string;
  icon: React.ElementType;
  children?: { label: string; href: string }[];
};

function buildCandidateNav(): NavItem[] {
  return [
    { label: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { label: 'Jobs', href: '/jobs', icon: Briefcase },
    { label: 'Applications', href: '/applications', icon: ClipboardList },
    { label: 'Resumes', href: '/resumes', icon: FileText },
    { label: 'Saved Jobs', href: '/saved-jobs', icon: Bookmark },
    { label: 'Messages', href: '/messages', icon: MessageSquare },
    { label: 'My Profile', href: '/profile/personal-details', icon: User },
    { label: 'Analytics', href: '/analytics', icon: BarChart3 },
    { label: 'Settings', href: '/settings', icon: Settings },
  ];
}

function buildCompanyNav(): NavItem[] {
  return [
    { label: 'Dashboard', href: '/company/dashboard', icon: LayoutDashboard },
    {
      label: 'Jobs',
      icon: Briefcase,
      children: [
        { label: 'My Jobs', href: '/company/jobs' },
        { label: 'Post a New Job', href: '/company/jobs/new' },
        { label: 'Applications', href: '/company/applications' },
        { label: 'Candidates', href: '/company/candidates' },
      ],
    },
    { label: 'Messages', href: '/company/messages', icon: MessageSquare },
    { label: 'Company Profile', href: '/company/profile', icon: User },
    { label: 'Analytics', href: '/company/analytics', icon: BarChart3 },
    { label: 'Settings', href: '/company/settings', icon: Settings },
  ];
}

function PlanCard({ role }: { role: 'candidate' | 'company' }) {
  const { plan, planValidTill } = useUser();
  const subscribeHref = `/subscribe?role=${role}`;
  return (
    <div className="mx-3 mb-4 rounded-xl border border-border-soft bg-surface-soft p-3.5">
      <p className="text-caption uppercase tracking-wider text-ink-muted">
        Your Plan
      </p>
      <p className="mt-1 text-sm font-bold font-display text-ink">{planDisplayName(plan)}</p>
      <p className="mt-0.5 text-xs text-ink-muted">
        {isFreePlan(plan) ? 'Free forever' : `Valid till ${planValidTill || '24 Aug'}`}
      </p>
      <Link href={subscribeHref} className="mt-3 block">
        <Button variant="outline" size="sm" className="w-full border-brand-blue/30 text-brand-blue hover:bg-brand-blue hover:text-white">
          View Plan
        </Button>
      </Link>
    </div>
  );
}

export function DashboardSidebar({ role }: { role: 'candidate' | 'company' }) {
  const pathname = usePathname();
  const items = role === 'company' ? buildCompanyNav() : buildCandidateNav();
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>({ Jobs: true });

  const isActive = (href?: string) => {
    if (!href) return false;
    if (href === '/dashboard' || href === '/company/dashboard') return pathname === href;
    return pathname === href || pathname.startsWith(href + '/');
  };

  return (
    <aside className="flex h-full w-64 shrink-0 flex-col border-r border-border-soft bg-surface-white">
      <div className="flex h-16 items-center px-5 border-b border-border-soft">
        <Logo href={role === 'company' ? '/company/dashboard' : '/dashboard'} />
      </div>

      <div className="px-4 pt-5 pb-2">
        <p className="text-caption uppercase tracking-wider text-ink-muted px-2">
          Dashboard
        </p>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 pb-4 space-y-0.5">
        {items.map((item) => {
          if (item.children) {
            const open = openGroups[item.label];
            const childActive = item.children.some((c) => isActive(c.href));
            return (
              <div key={item.label}>
                <button
                  type="button"
                  onClick={() => setOpenGroups((s) => ({ ...s, [item.label]: !s[item.label] }))}
                  className={cn(
                    'flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                    childActive ? 'text-primary bg-primary/5' : 'text-foreground/80 hover:bg-secondary'
                  )}
                >
                  <item.icon className="h-[18px] w-[18px] shrink-0" />
                  <span className="flex-1 text-left">{item.label}</span>
                  {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                </button>
                {open && (
                  <div className="ml-4 mt-0.5 space-y-0.5 border-l border-border pl-3">
                    {item.children.map((child) => (
                      <Link
                        key={child.href + child.label}
                        href={child.href}
                        className={cn(
                          'flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors',
                          isActive(child.href)
                            ? 'bg-primary text-primary-foreground font-medium'
                            : 'text-muted-foreground hover:bg-secondary hover:text-foreground'
                        )}
                      >
                        {child.label === 'Post a New Job' && <PlusCircle className="h-3.5 w-3.5" />}
                        {child.label === 'Candidates' && <Users className="h-3.5 w-3.5" />}
                        {child.label}
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            );
          }

          return (
            <Link
              key={item.label}
              href={item.href!}
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                isActive(item.href)
                  ? 'bg-primary text-primary-foreground'
                  : 'text-foreground/80 hover:bg-secondary'
              )}
            >
              <item.icon className="h-[18px] w-[18px] shrink-0" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <PlanCard role={role} />
    </aside>
  );
}

export function AppShell({
  role,
  children,
}: {
  role: 'candidate' | 'company';
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const { logout } = useUser();
  const isOnboarding =
    pathname.includes('/onboarding') || pathname.includes('/resume/download');

  if (isOnboarding) {
    return (
      <div className="min-h-screen flex flex-col bg-surface-soft">
        <header className="h-14 border-b border-border-soft bg-surface-white flex items-center px-6">
          <Logo href={role === 'company' ? '/company/dashboard' : '/dashboard'} />
        </header>
        <main className="flex-1">{children}</main>
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden bg-surface-soft">
      <div className="sticky top-0 h-screen hidden md:block">
        <DashboardSidebar role={role} />
      </div>
      <div className="flex min-w-0 flex-1 flex-col h-full overflow-hidden">
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-border-soft bg-surface-white/95 backdrop-blur px-4 md:px-8">
          <div className="md:hidden">
            <Logo href={role === 'company' ? '/company/dashboard' : '/dashboard'} />
          </div>
          <div className="flex-1" />
          <div className="flex items-center gap-2">
            <NotificationsDropdown />
            <button
              type="button"
              onClick={() => {
                logout();
                router.push('/');
              }}
              className="inline-flex h-9 w-9 items-center justify-center rounded-full text-ink-muted hover:bg-surface-soft hover:text-ink"
              aria-label="Sign out"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </header>
        <main className="flex-1 bg-surface-soft/40 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}
