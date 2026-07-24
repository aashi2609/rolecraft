"use client";

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, CheckCircle2, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { RoleSelectModal } from '@/components/RoleSelectModal';
import { Logo } from '@/components/Logo';
import Link from 'next/link';

export default function LandingPage() {
  const [roleModalOpen, setRoleModalOpen] = useState(false);

  return (
    <div className="min-h-screen flex flex-col bg-app-surface">
      <nav className="relative z-20 flex items-center justify-between px-6 md:px-12 lg:px-20 py-5">
        <Logo />

        <div className="hidden md:flex items-center gap-8">
          <a href="#features" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
            Features
          </a>
          <Link href="/pricing" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
            Pricing
          </Link>
          <a href="#companies" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
            For Companies
          </a>
        </div>

        <div className="flex items-center gap-3">
          <Button variant="ghost" className="text-sm font-medium" onClick={() => setRoleModalOpen(true)}>
            Sign In
          </Button>
          <Button className="rounded-lg px-5 text-sm font-medium" onClick={() => setRoleModalOpen(true)}>
            Get Started
          </Button>
        </div>
      </nav>

      <section className="relative flex-1 flex flex-col items-center justify-center px-4 pt-16 pb-24 md:pt-24">
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="inline-flex items-center gap-2 rounded-full border border-primary/15 bg-primary/5 px-4 py-1.5 text-sm text-primary font-medium mb-6"
        >
          <Sparkles className="h-3.5 w-3.5" />
          AI-tailored resumes across domains
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, delay: 0.05 }}
          className="text-center text-4xl md:text-5xl lg:text-6xl font-extrabold tracking-tight text-foreground max-w-3xl leading-[1.1]"
        >
          Match talent to roles with{' '}
          <span className="text-primary">smarter career fit</span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, delay: 0.12 }}
          className="mt-5 text-center text-base md:text-lg text-muted-foreground max-w-xl leading-relaxed"
        >
          One profile, tailored resumes for every vertical, and ranked candidates for every job —
          so seekers get seen and companies hire faster.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, delay: 0.2 }}
          className="mt-8 flex flex-wrap items-center justify-center gap-3"
        >
          <Button
            className="rounded-lg px-7 py-5 text-sm font-semibold h-auto gap-2"
            onClick={() => setRoleModalOpen(true)}
          >
            Get Started <ArrowRight className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            className="rounded-lg px-7 py-5 text-sm font-semibold h-auto"
            onClick={() => document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' })}
          >
            See How It Works
          </Button>
        </motion.div>

        <motion.ul
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.35 }}
          className="mt-10 flex flex-wrap justify-center gap-x-8 gap-y-3 text-sm text-muted-foreground"
        >
          {['Cross-domain resume tailoring', 'Ranked candidate shortlists', 'Plan that grows with you'].map(
            (item) => (
              <li key={item} className="inline-flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-primary" />
                {item}
              </li>
            )
          )}
        </motion.ul>
      </section>

      <section id="features" className="border-t border-border bg-white py-20 px-4">
        <div className="max-w-5xl mx-auto grid md:grid-cols-3 gap-10">
          {[
            {
              title: 'Multi-vertical resumes',
              body: 'Generate separate ATS-ready resumes for Core Electronics, IT, Marketing, and more — from one profile.',
            },
            {
              title: 'Smarter job search',
              body: 'Filter by skills, location, experience, and salary to find roles that actually fit your goals.',
            },
            {
              title: 'Hiring that ranks',
              body: 'Post jobs in minutes and get a ranked shortlist of candidates matched to your requirements.',
            },
          ].map((f, i) => (
            <motion.div
              key={f.title}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.08 }}
            >
              <div className="h-10 w-10 rounded-lg bg-primary/10 text-primary flex items-center justify-center font-bold mb-4">
                {i + 1}
              </div>
              <h3 className="text-lg font-bold text-foreground mb-2">{f.title}</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">{f.body}</p>
            </motion.div>
          ))}
        </div>
      </section>

      <section id="companies" className="border-t border-border py-16 px-4 bg-secondary/40">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-2xl md:text-3xl font-bold text-foreground mb-3">Built for seekers and hiring teams</h2>
          <p className="text-muted-foreground mb-8">
            Start free, upgrade when you need unlimited roles, postings, and full search filters.
          </p>
          <Button className="rounded-lg px-6" onClick={() => setRoleModalOpen(true)}>
            Choose your path
          </Button>
        </div>
      </section>

      <RoleSelectModal open={roleModalOpen} onOpenChange={setRoleModalOpen} />
    </div>
  );
}
