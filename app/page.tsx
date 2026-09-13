"use client";

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  FileText,
  Gauge,
  Sparkles,
  Users,
  ClipboardList,
  BadgeCheck,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { RoleSelectModal } from '@/components/RoleSelectModal';
import { DashboardMockup } from '@/components/landing/DashboardMockup';
import Link from 'next/link';

const JOB_SEEKER_FEATURES = [
  {
    icon: FileText,
    title: 'Tailored Resumes',
    body: 'Generate a separate ATS-ready resume for each target vertical — Core Electronics, IT, Marketing — from one profile.',
  },
  {
    icon: Gauge,
    title: 'ATS Score & Auto-Fix',
    body: 'See a live ATS score per version and surface the gaps that keep you out of recruiter shortlists.',
  },
  {
    icon: Sparkles,
    title: 'Smart Job Matching',
    body: 'Rank openings by skill overlap, experience band, and salary so you apply where you actually fit.',
  },
];

const COMPANY_FEATURES = [
  {
    icon: Users,
    title: 'Ranked Candidate Search',
    body: 'Hiring teams get a scored shortlist with fitment rationale — not a flat pile of applications.',
  },
  {
    icon: BadgeCheck,
    title: 'AI Fitment Rationales',
    body: 'Instantly understand exactly why a candidate matches your role with AI-generated reasoning.',
  },
  {
    icon: ClipboardList,
    title: 'Streamlined Hiring Pipeline',
    body: 'Manage inbound applications and track candidate progress from submitted to shortlisted in one dashboard.',
  },
];

export default function LandingPage() {
  const [roleModalOpen, setRoleModalOpen] = useState(false);

  return (
    <div className="min-h-screen flex flex-col bg-surface-white">
      {/* Navbar */}
      <nav className="sticky top-0 z-30 border-b border-border-soft bg-surface-white/95 backdrop-blur-sm">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-5 md:px-8 py-4">
          <Link
            href="/"
            className="font-display text-xl font-bold tracking-tight text-ink"
          >
            RoleCraft
          </Link>

          <div className="hidden md:flex items-center gap-8">
            <a
              href="#job-seekers"
              className="text-sm text-ink-muted hover:text-ink transition-colors"
            >
              For Job Seekers
            </a>
            <a
              href="#companies"
              className="text-sm text-ink-muted hover:text-ink transition-colors"
            >
              For Companies
            </a>
            <Link
              href="/pricing"
              className="text-sm text-ink-muted hover:text-ink transition-colors"
            >
              Pricing
            </Link>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              className="text-sm font-medium text-ink-muted hover:text-ink rounded-full px-4"
              onClick={() => setRoleModalOpen(true)}
            >
              Sign In
            </Button>
            <Button
              className="rounded-full px-5 text-sm font-semibold shadow-[0_4px_14px_rgba(37,99,235,0.25)] hover:shadow-[0_6px_20px_rgba(37,99,235,0.35)] transition-shadow bg-brand-blue hover:bg-brand-blue-deep text-white"
              onClick={() => setRoleModalOpen(true)}
            >
              Get Started
            </Button>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative flex flex-col items-center px-4 pt-16 md:pt-24 pb-8 md:pb-12 overflow-x-clip">
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="inline-flex items-center rounded-full border border-border-soft bg-surface-white px-4 py-1.5 text-sm text-ink-muted shadow-soft mb-7"
        >
          AI-tailored resumes, real fitment scoring 
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.05 }}
          className="text-hero text-center text-ink max-w-4xl px-2"
        >
          The Future of{' '}
          <span className="text-brand-blue">Smarter</span> Career Fit
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, delay: 0.12 }}
          className="mt-5 text-center text-base md:text-[17px] text-ink-muted max-w-[600px] leading-relaxed"
        >
          One profile, tailored resumes for every role — and AI-ranked candidates for every job. Built for job seekers and hiring teams alike.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, delay: 0.2 }}
          className="mt-8 flex flex-wrap items-center justify-center gap-3"
        >
          <Button
            className="rounded-full px-8 h-12 text-[15px] font-semibold bg-brand-blue hover:bg-brand-blue-deep text-white shadow-[0_4px_14px_rgba(37,99,235,0.25)] hover:shadow-[0_6px_20px_rgba(37,99,235,0.35)] transition-shadow"
            onClick={() => setRoleModalOpen(true)}
          >
            Get Started Free
          </Button>
          <Button
            variant="outline"
            className="rounded-full px-8 h-12 text-[15px] font-semibold bg-surface-white border-border-soft text-ink hover:bg-surface-soft"
            onClick={() =>
              document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' })
            }
          >
            See How It Works
          </Button>
        </motion.div>

        {/* Product mockup + glow */}
        <div className="relative w-full max-w-5xl mt-14 md:mt-20 px-2 md:px-6">
          {/* Radial Glow */}
          <div
            className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-[42%] w-[800px] h-[800px] rounded-full pointer-events-none z-0"
            style={{
              background: 'radial-gradient(circle, rgba(96, 165, 250, 0.18) 0%, transparent 65%)',
              filter: 'blur(60px)',
            }}
            aria-hidden
          />

          <motion.div
            initial={{ opacity: 0, y: 36 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.25 }}
            transition={{ duration: 0.65, ease: [0.22, 1, 0.36, 1] }}
            className="relative z-10 drop-shadow-[0_16px_40px_rgba(37,99,235,0.12)]"
          >
            {/* Floating stat chips */}
            <motion.div
              initial={{ opacity: 0, x: -12, y: 8 }}
              whileInView={{ opacity: 1, x: 0, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.35, duration: 0.45 }}
              className="absolute -left-1 md:-left-4 top-[18%] z-20 hidden sm:flex items-center gap-2 rounded-xl border border-border-soft bg-surface-white px-3.5 py-2.5 shadow-soft"
            >
              <span className="flex h-7 w-7 items-center justify-center rounded-full bg-brand-blue/10 text-brand-blue text-xs font-bold">
                ✓
              </span>
              <div>
                <p className="text-caption text-ink font-semibold">92% Fitment Score</p>
                <p className="text-[11px] text-ink-muted">ATS ready</p>
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: 12, y: 8 }}
              whileInView={{ opacity: 1, x: 0, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.45, duration: 0.45 }}
              className="absolute -right-1 md:-right-2 top-[8%] z-20 hidden sm:block rounded-xl border border-border-soft bg-surface-white px-3.5 py-2.5 shadow-soft"
            >
              <p className="text-caption text-brand-blue font-semibold">3 New Matches</p>
              <p className="text-[11px] text-ink-muted mt-0.5">Updated just now</p>
            </motion.div>

            <DashboardMockup />
          </motion.div>
        </div>
      </section>

      {/* Stats Strip */}
      <section className="relative z-10 bg-surface-soft py-12 px-4 border-t border-border-soft shadow-[inset_0_1px_0_rgba(255,255,255,0.6)]">
        <div className="max-w-5xl mx-auto flex flex-col md:flex-row items-center justify-between gap-8 md:gap-4 text-center">
          {[
            { value: "1,200+", label: "Tailored resumes generated" },
            { value: "300+", label: "Verified companies" },
            { value: "92%", label: "Average match accuracy" },
            { value: "4.8/5", label: "Candidate rating" }
          ].map((stat, idx) => (
            <motion.div 
              key={idx}
              initial={{ opacity: 0, scale: 0.9, y: 10 }}
              whileInView={{ opacity: 1, scale: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: idx * 0.1, duration: 0.5 }}
              className="flex-1"
            >
              <div className="text-4xl md:text-5xl font-display font-bold text-brand-blue mb-1 tracking-tight">{stat.value}</div>
              <div className="text-[13px] text-ink-muted font-semibold uppercase tracking-wide">{stat.label}</div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section id="features" className="relative z-10 bg-surface-soft py-16 md:py-24 px-4 border-t border-border-soft shadow-[inset_0_1px_0_rgba(255,255,255,0.5)]">
        <div className="max-w-6xl mx-auto">
          <motion.h2
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-section text-center text-ink max-w-2xl mx-auto mb-4"
          >
            AI-Powered Features, Effortless Career Growth
          </motion.h2>
          <p className="text-center text-ink-muted text-body max-w-xl mx-auto mb-14">
            Concrete tools for job seekers and hiring teams — not another generic career board.
          </p>

          <div id="job-seekers" className="mb-16 pt-8">
            <h3 className="text-2xl font-bold text-ink mb-8 text-center">For Job Seekers</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5 md:gap-6">
              {JOB_SEEKER_FEATURES.map((f, i) => (
                <motion.div
                  key={f.title}
                  initial={{ opacity: 0, y: 24 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, amount: 0.15 }}
                  transition={{ delay: i * 0.08, duration: 0.5 }}
                  className="feature-card rounded-2xl bg-surface-white p-6 border border-border-soft shadow-[0_4px_16px_rgba(37,99,235,0.03)]"
                >
                  <div className="icon-chip mb-4 flex h-11 w-11 items-center justify-center rounded-lg bg-brand-blue/10 text-brand-blue">
                    <f.icon className="h-5 w-5" />
                  </div>
                  <h3 className="text-card-title text-ink mb-2 flex items-center gap-2">
                    {f.title}
                  </h3>
                  <p className="text-sm text-ink-muted leading-relaxed">{f.body}</p>
                </motion.div>
              ))}
            </div>
          </div>

          <div id="companies" className="pt-8">
            <h3 className="text-2xl font-bold text-ink mb-8 text-center">For Companies</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5 md:gap-6">
              {COMPANY_FEATURES.map((f, i) => (
                <motion.div
                  key={f.title}
                  initial={{ opacity: 0, y: 24 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, amount: 0.15 }}
                  transition={{ delay: i * 0.08, duration: 0.5 }}
                  className="feature-card rounded-2xl bg-surface-white p-6 border border-border-soft shadow-[0_4px_16px_rgba(37,99,235,0.03)]"
                >
                  <div className="icon-chip mb-4 flex h-11 w-11 items-center justify-center rounded-lg bg-indigo-500/10 text-indigo-500">
                    <f.icon className="h-5 w-5" />
                  </div>
                  <h3 className="text-card-title text-ink mb-2 flex items-center gap-2">
                    {f.title}
                  </h3>
                  <p className="text-sm text-ink-muted leading-relaxed">{f.body}</p>
                </motion.div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Companies CTA */}
      <section id="companies-cta" className="border-t border-border-soft bg-surface-soft py-16 md:py-20 px-4">
        <div className="max-w-2xl mx-auto text-center">
          <h2 className="text-section text-ink mb-3">Built for seekers and hiring teams</h2>
          <p className="text-ink-muted text-body mb-8">
            Start free. Upgrade when you need unlimited roles, postings, and full search filters.
          </p>
          <Button
            className="rounded-full px-8 h-12 text-[15px] font-semibold bg-brand-blue hover:bg-brand-blue-deep text-white"
            onClick={() => setRoleModalOpen(true)}
          >
            Choose your path
          </Button>
        </div>
      </section>

      <RoleSelectModal open={roleModalOpen} onOpenChange={setRoleModalOpen} />
    </div>
  );
}
