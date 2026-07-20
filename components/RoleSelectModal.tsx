"use client";

import React from 'react';
import { Dialog, DialogContent } from '@/components/ui/dialog';
import { Briefcase, Building2 } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import Link from 'next/link';

interface RoleSelectModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function RoleSelectModal({ open, onOpenChange }: RoleSelectModalProps) {
  const router = useRouter();

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl rounded-2xl border-none shadow-dashboard bg-background/95 backdrop-blur overflow-hidden p-0">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3 }}
          className="p-8 md:p-12 text-center"
        >
          <h2 className="font-display text-4xl mb-3 text-foreground">Welcome to RoleCraft</h2>
          <p className="text-muted-foreground mb-10 text-lg">Tell us who you are so we can set things up right.</p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8 text-left">
            
            {/* Candidate Card */}
            <div 
              onClick={() => router.push('/signup?role=candidate')}
              className="group cursor-pointer rounded-2xl border border-border p-6 hover:border-accent hover:shadow-md transition-all bg-background"
            >
              <div className="w-12 h-12 rounded-full bg-secondary text-foreground flex items-center justify-center mb-4 group-hover:bg-accent group-hover:text-accent-foreground transition-colors">
                <Briefcase className="w-6 h-6" />
              </div>
              <h3 className="font-semibold text-xl mb-2 text-foreground">I'm looking for a job</h3>
              <p className="text-muted-foreground text-sm leading-relaxed">
                Build a tailored resume and get matched with roles that fit.
              </p>
            </div>

            {/* Company Card */}
            <div 
              onClick={() => router.push('/signup?role=company')}
              className="group cursor-pointer rounded-2xl border border-border p-6 hover:border-accent hover:shadow-md transition-all bg-background"
            >
              <div className="w-12 h-12 rounded-full bg-secondary text-foreground flex items-center justify-center mb-4 group-hover:bg-accent group-hover:text-accent-foreground transition-colors">
                <Building2 className="w-6 h-6" />
              </div>
              <h3 className="font-semibold text-xl mb-2 text-foreground">I'm hiring</h3>
              <p className="text-muted-foreground text-sm leading-relaxed">
                Post roles and get a ranked shortlist of candidates who actually fit.
              </p>
            </div>

          </div>

          <div className="text-center text-sm text-muted-foreground">
            Already have an account?{' '}
            <Link href="/signin" className="text-foreground font-medium hover:underline">
              Sign In
            </Link>
          </div>
        </motion.div>
      </DialogContent>
    </Dialog>
  );
}
