"use client";

import React from 'react';
import { CheckCircle2, LayoutDashboard, Briefcase, FileText, MessageSquare } from 'lucide-react';

/** Static candidate-dashboard product preview for the landing hero. */
export function DashboardMockup() {
  return (
    <div className="w-full overflow-hidden rounded-2xl border border-border-soft bg-surface-white shadow-dashboard">
      <div className="flex min-h-[320px] md:min-h-[420px]">
        {/* Sidebar */}
        <aside className="hidden sm:flex w-[140px] md:w-[168px] shrink-0 flex-col border-r border-border-soft bg-surface-white p-3 md:p-4">
          <div className="font-display text-[13px] font-bold tracking-tight text-ink mb-5 px-1">
            RoleCraft
          </div>
          <p className="text-[10px] font-semibold uppercase tracking-wider text-ink-muted px-2 mb-2">
            Dashboard
          </p>
          <nav className="space-y-0.5 flex-1">
            {[
              { label: 'Dashboard', icon: LayoutDashboard, active: true },
              { label: 'Jobs', icon: Briefcase },
              { label: 'Resumes', icon: FileText },
              { label: 'Messages', icon: MessageSquare },
            ].map((item) => (
              <div
                key={item.label}
                className={`flex items-center gap-2 rounded-lg px-2 py-1.5 text-[11px] font-medium ${
                  item.active
                    ? 'bg-brand-blue text-white'
                    : 'text-ink-muted'
                }`}
              >
                <item.icon className="h-3 w-3 shrink-0" />
                {item.label}
              </div>
            ))}
          </nav>
          <div className="mt-auto rounded-lg border border-border-soft bg-surface-soft p-2.5">
            <p className="text-[9px] font-semibold uppercase text-ink-muted">Your Plan</p>
            <p className="text-[11px] font-bold text-ink mt-0.5">Premium</p>
          </div>
        </aside>

        {/* Main */}
        <div className="flex-1 min-w-0 bg-surface-soft/60 p-3 md:p-5">
          <div className="rounded-xl bg-brand-blue text-white px-4 py-3 md:px-5 md:py-4 mb-3 md:mb-4">
            <p className="text-[10px] md:text-xs text-white/80 font-medium">Welcome back</p>
            <p className="font-display text-sm md:text-lg font-bold tracking-tight mt-0.5">
              Your profile is 92% match-ready
            </p>
          </div>

          <div className="grid grid-cols-2 gap-2 md:gap-3 mb-3 md:mb-4">
            <div className="rounded-xl border border-border-soft bg-surface-white p-3 md:p-4">
              <p className="text-[10px] md:text-xs text-ink-muted font-medium">Fitment Score</p>
              <p className="font-display text-xl md:text-2xl font-bold text-brand-blue mt-1">92%</p>
              <div className="mt-2 h-1.5 rounded-full bg-surface-soft overflow-hidden">
                <div className="h-full w-[92%] rounded-full bg-brand-blue" />
              </div>
            </div>
            <div className="rounded-xl border border-border-soft bg-surface-white p-3 md:p-4">
              <p className="text-[10px] md:text-xs text-ink-muted font-medium">Top Matches</p>
              <p className="font-display text-xl md:text-2xl font-bold text-ink mt-1">3 new</p>
              <p className="text-[10px] text-ink-muted mt-1">Frontend · Product · Design</p>
            </div>
          </div>

          <div className="rounded-xl border border-border-soft bg-surface-white overflow-hidden">
            <div className="px-3 md:px-4 py-2.5 border-b border-border-soft flex items-center justify-between">
              <p className="text-[11px] md:text-xs font-semibold text-ink">Recent Applications</p>
              <span className="text-[10px] text-brand-blue font-medium">View all</span>
            </div>
            <div className="divide-y divide-border-soft">
              {[
                { role: 'Senior Frontend Engineer', co: 'TechCorp', status: 'In review' },
                { role: 'UI/UX Designer', co: 'DesignStudio', status: 'Shortlisted' },
                { role: 'Product Designer', co: 'GrowthLabs', status: 'Applied' },
              ].map((row) => (
                <div
                  key={row.role}
                  className="px-3 md:px-4 py-2.5 flex items-center justify-between gap-2"
                >
                  <div className="min-w-0">
                    <p className="text-[11px] md:text-xs font-semibold text-ink truncate">{row.role}</p>
                    <p className="text-[10px] text-ink-muted">{row.co}</p>
                  </div>
                  <span className="shrink-0 inline-flex items-center gap-1 text-[9px] md:text-[10px] font-medium text-brand-blue bg-surface-soft px-2 py-0.5 rounded-full">
                    {row.status === 'Shortlisted' && <CheckCircle2 className="h-2.5 w-2.5" />}
                    {row.status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
