"use client";

import React from 'react';
import { Dialog, DialogContent } from '@/components/ui/dialog';
import { Briefcase, Building2 } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import Link from 'next/link';
import { Logo } from '@/components/Logo';

interface RoleSelectModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function RoleSelectModal({ open, onOpenChange }: RoleSelectModalProps) {
  const router = useRouter();

  const go = (role: 'candidate' | 'company') => {
    onOpenChange(false);
    router.push(`/subscribe?role=${role}`);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl rounded-2xl border border-border shadow-dashboard bg-white overflow-hidden p-0">
        <motion.div
          initial={{ opacity: 0, scale: 0.97 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.25 }}
          className="p-8 md:p-12 text-center"
        >
          <div className="flex justify-center mb-6">
            <Logo href={null} />
          </div>
          <h2 className="text-3xl font-bold mb-3 text-foreground">Welcome to RoleCraft</h2>
          <p className="text-muted-foreground mb-10 text-base">
            Tell us who you are so we can set up the right plan.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-8 text-left">
            <button
              type="button"
              onClick={() => go('candidate')}
              className="group cursor-pointer rounded-2xl border border-border p-6 hover:border-primary hover:shadow-md transition-all bg-white text-left"
            >
              <div className="w-12 h-12 rounded-full bg-primary/10 text-primary flex items-center justify-center mb-4 group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
                <Briefcase className="w-6 h-6" />
              </div>
              <h3 className="font-semibold text-xl mb-2 text-foreground">I&apos;m looking for a job</h3>
              <p className="text-muted-foreground text-sm leading-relaxed">
                Build tailored resumes and get matched with roles that fit.
              </p>
            </button>

            <button
              type="button"
              onClick={() => go('company')}
              className="group cursor-pointer rounded-2xl border border-border p-6 hover:border-primary hover:shadow-md transition-all bg-white text-left"
            >
              <div className="w-12 h-12 rounded-full bg-primary/10 text-primary flex items-center justify-center mb-4 group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
                <Building2 className="w-6 h-6" />
              </div>
              <h3 className="font-semibold text-xl mb-2 text-foreground">I&apos;m hiring</h3>
              <p className="text-muted-foreground text-sm leading-relaxed">
                Post roles and get a ranked shortlist of candidates who actually fit.
              </p>
            </button>
          </div>

          <div className="text-center text-sm text-muted-foreground">
            Already have an account?{' '}
            <Link href="/signin" className="text-primary font-medium hover:underline">
              Sign In
            </Link>
          </div>
        </motion.div>
      </DialogContent>
    </Dialog>
  );
}
