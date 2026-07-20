"use client";

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Play } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { RoleSelectModal } from '@/components/RoleSelectModal';

export default function LandingPage() {
  const [roleModalOpen, setRoleModalOpen] = useState(false);

  return (
    <div className="h-screen flex flex-col bg-background overflow-hidden relative">
      
      {/* Background Video */}
      <div className="absolute inset-0 z-0">
        <video 
          autoPlay 
          loop 
          muted 
          playsInline 
          className="w-full h-full object-cover opacity-20"
        >
          <source src="https://cdn.pixabay.com/video/2020/05/25/40156-425268482_large.mp4" type="video/mp4" />
        </video>
        <div className="absolute inset-0 bg-background/80" />
      </div>

      {/* Navbar */}
      <nav className="relative z-20 flex items-center justify-between px-6 md:px-12 lg:px-20 py-5 font-body">
        <div className="text-xl font-semibold tracking-tight text-foreground">
          ✦ RoleCraft
        </div>
        
        <div className="hidden md:flex items-center gap-8">
          <a href="#" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Home</a>
          <a href="/pricing" className="text-sm text-muted-foreground hover:text-foreground transition-colors">Pricing</a>
          <a href="#" className="text-sm text-muted-foreground hover:text-foreground transition-colors">For Companies</a>
          <a href="#" className="text-sm text-muted-foreground hover:text-foreground transition-colors">About</a>
        </div>

        <div className="flex items-center gap-4">
          <Button variant="ghost" className="text-sm font-medium px-4" onClick={() => setRoleModalOpen(true)}>
            Sign In
          </Button>
          <Button className="rounded-full px-5 text-sm font-medium" onClick={() => setRoleModalOpen(true)}>
            Get Started
          </Button>
        </div>
      </nav>

      {/* Hero Content */}
      <div className="relative z-10 flex-1 flex flex-col items-center justify-start pt-16 md:pt-24 px-4">
        
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="inline-flex items-center gap-1.5 rounded-full border border-border bg-background px-4 py-1.5 text-sm text-muted-foreground font-body mb-6 shadow-sm"
        >
          Now with AI-tailored resumes ✨
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="text-center font-display text-5xl md:text-6xl lg:text-[5rem] leading-[0.95] tracking-tight text-foreground max-w-2xl"
        >
          The Future of <span className="italic">Smarter</span> Career Fit
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="mt-4 text-center text-base md:text-lg text-muted-foreground max-w-[650px] leading-relaxed font-body"
        >
          One profile, tailored resumes for every role, and AI-matched candidates for every job — so job seekers get seen and companies find the right fit, faster.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="mt-8 flex items-center gap-3"
        >
          <Button className="rounded-full px-6 py-5 text-sm font-medium font-body h-auto" onClick={() => setRoleModalOpen(true)}>
            Get Started Free
          </Button>
          <Button variant="outline" className="rounded-full px-6 py-5 text-sm font-medium font-body h-auto bg-background/50 backdrop-blur-sm hover:bg-background/80 border-border">
            See How It Works
          </Button>
          <button className="h-11 w-11 flex items-center justify-center rounded-full bg-background shadow-[0_2px_12px_rgba(0,0,0,0.08)] hover:bg-background/80 transition-colors">
            <Play className="h-4 w-4 fill-foreground text-foreground ml-0.5" />
          </button>
        </motion.div>

        {/* Dashboard Preview Overlay */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.5 }}
          className="mt-12 w-full max-w-5xl"
        >
          <div 
            className="rounded-2xl overflow-hidden p-3 md:p-4 w-full"
            style={{
              background: 'rgba(255, 255, 255, 0.4)',
              border: '1px solid rgba(255, 255, 255, 0.5)',
              boxShadow: 'var(--shadow-dashboard)',
              backdropFilter: 'blur(12px)'
            }}
          >
            {/* Dashboard Mock */}
            <div className="bg-background rounded-xl border border-border overflow-hidden flex flex-col h-[600px] select-none pointer-events-none">
              
              {/* Top Bar */}
              <div className="h-12 border-b border-border flex items-center justify-between px-4 bg-background">
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 rounded bg-primary text-primary-foreground flex items-center justify-center text-[10px] font-bold">R</div>
                  <span className="font-semibold text-xs">RoleCraft</span>
                  <svg className="w-3 h-3 text-muted-foreground ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg>
                </div>
                <div className="flex-1 max-w-md mx-4">
                  <div className="h-7 rounded-md bg-muted flex items-center px-3 text-[10px] text-muted-foreground justify-between">
                    <span>Search...</span>
                    <span className="bg-background border border-border px-1.5 py-0.5 rounded text-[8px]">⌘K</span>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <button className="bg-primary text-primary-foreground px-3 py-1 rounded text-[10px] font-medium">New Application</button>
                  <div className="w-5 h-5 rounded-full bg-muted flex items-center justify-center">
                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" /></svg>
                  </div>
                  <div className="w-6 h-6 rounded-full bg-secondary border border-border flex items-center justify-center text-[10px] font-semibold text-foreground">JB</div>
                </div>
              </div>

              {/* Main Area */}
              <div className="flex flex-1 overflow-hidden">
                {/* Sidebar */}
                <div className="w-40 border-r border-border bg-background p-3 flex flex-col gap-6">
                  <div>
                    <div className="flex items-center justify-between px-2 py-1.5 bg-muted rounded-md text-foreground text-[11px] font-medium mb-1">
                      <span>Home</span>
                    </div>
                    <div className="flex items-center justify-between px-2 py-1.5 text-muted-foreground hover:text-foreground text-[11px] mb-1">
                      <span>Applications</span>
                      <span className="bg-primary text-primary-foreground text-[8px] px-1.5 py-0.5 rounded-full">12</span>
                    </div>
                    <div className="flex items-center px-2 py-1.5 text-muted-foreground hover:text-foreground text-[11px] mb-1">Resumes</div>
                    <div className="flex items-center px-2 py-1.5 text-muted-foreground hover:text-foreground text-[11px] mb-1">Saved Jobs</div>
                    <div className="flex items-center px-2 py-1.5 text-muted-foreground hover:text-foreground text-[11px] mb-1">Messages</div>
                    <div className="flex items-center justify-between px-2 py-1.5 text-muted-foreground hover:text-foreground text-[11px]">
                      <span>Companies</span>
                      <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
                    </div>
                  </div>
                  <div>
                    <div className="px-2 text-[9px] font-semibold text-muted-foreground uppercase tracking-wider mb-2">Tools</div>
                    <div className="flex items-center px-2 py-1.5 text-muted-foreground text-[11px] mb-1">Resume Builder</div>
                    <div className="flex items-center px-2 py-1.5 text-muted-foreground text-[11px] mb-1">Job Matches</div>
                    <div className="flex items-center px-2 py-1.5 text-muted-foreground text-[11px] mb-1">Interview Prep</div>
                    <div className="flex items-center px-2 py-1.5 text-muted-foreground text-[11px]">Settings</div>
                  </div>
                </div>

                {/* Content */}
                <div className="flex-1 bg-secondary/30 p-6 flex flex-col gap-6 overflow-hidden">
                  <div>
                    <h2 className="text-sm font-semibold text-foreground">Welcome, Jane</h2>
                    <div className="flex items-center gap-2 mt-3">
                      <div className="px-3 py-1 bg-accent text-accent-foreground rounded-full text-[10px] font-medium">Build Resume</div>
                      <div className="px-3 py-1 bg-background border border-border text-foreground rounded-full text-[10px] font-medium">Apply</div>
                      <div className="px-3 py-1 bg-background border border-border text-foreground rounded-full text-[10px] font-medium">Save Job</div>
                      <div className="px-3 py-1 bg-background border border-border text-foreground rounded-full text-[10px] font-medium">Message</div>
                      <div className="px-3 py-1 bg-background border border-border text-foreground rounded-full text-[10px] font-medium">Schedule Interview</div>
                      <div className="px-3 py-1 bg-background border border-border text-foreground rounded-full text-[10px] font-medium">Track Application</div>
                      <div className="text-[10px] text-muted-foreground ml-2">+ Customize</div>
                    </div>
                  </div>

                  <div className="flex gap-4">
                    {/* Score Card */}
                    <div className="flex-1 bg-background border border-border rounded-xl p-4 shadow-sm flex flex-col justify-between">
                      <div className="flex justify-between items-start mb-2">
                        <span className="text-[11px] font-medium text-muted-foreground">Profile Fitment Score</span>
                        <div className="w-4 h-4 rounded-full bg-green-100 flex items-center justify-center">
                          <svg className="w-2.5 h-2.5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg>
                        </div>
                      </div>
                      <div className="text-3xl font-bold text-foreground">92%</div>
                      <div className="flex justify-between items-end mt-4">
                        <div>
                          <div className="text-[9px] text-muted-foreground">Last 30 Days</div>
                          <div className="text-[10px] text-green-600 font-medium">+8 pts</div>
                        </div>
                        <div className="text-right">
                          <div className="text-[9px] text-muted-foreground">Applications sent this week</div>
                          <div className="text-[10px] font-medium">4</div>
                        </div>
                      </div>
                      <div className="h-20 mt-4 relative w-full">
                        <svg className="w-full h-full overflow-visible" preserveAspectRatio="none" viewBox="0 0 100 100">
                          <defs>
                            <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="0%" stopColor="hsl(var(--accent))" stopOpacity="0.15" />
                              <stop offset="100%" stopColor="hsl(var(--accent))" stopOpacity="0" />
                            </linearGradient>
                          </defs>
                          <path d="M0,100 L0,60 C20,60 30,20 50,40 C70,60 80,10 100,20 L100,100 Z" fill="url(#grad)" />
                          <path d="M0,60 C20,60 30,20 50,40 C70,60 80,10 100,20" fill="none" stroke="hsl(var(--accent))" strokeWidth="1.5" />
                        </svg>
                      </div>
                    </div>

                    {/* Top Matches Card */}
                    <div className="flex-1 bg-background border border-border rounded-xl p-4 shadow-sm">
                      <div className="flex justify-between items-center mb-4">
                        <span className="text-[11px] font-semibold text-foreground">Top Matches</span>
                        <div className="flex gap-2 text-muted-foreground">
                          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
                          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" /></svg>
                        </div>
                      </div>
                      <div className="flex flex-col">
                        <div className="flex justify-between items-center py-3">
                          <div>
                            <div className="text-[11px] font-medium text-foreground">Backend Engineer <span className="text-muted-foreground">· Razorpay</span></div>
                          </div>
                          <div className="text-[10px] font-medium text-green-600 bg-green-50 px-2 py-0.5 rounded">94% Fit</div>
                        </div>
                        <div className="flex justify-between items-center py-3">
                          <div>
                            <div className="text-[11px] font-medium text-foreground">Data Analyst <span className="text-muted-foreground">· Swiggy</span></div>
                          </div>
                          <div className="text-[10px] font-medium text-green-600 bg-green-50 px-2 py-0.5 rounded">89% Fit</div>
                        </div>
                        <div className="flex justify-between items-center py-3">
                          <div>
                            <div className="text-[11px] font-medium text-foreground">Product Manager <span className="text-muted-foreground">· CRED</span></div>
                          </div>
                          <div className="text-[10px] font-medium text-green-600 bg-green-50 px-2 py-0.5 rounded">85% Fit</div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Table */}
                  <div className="bg-background border border-border rounded-xl shadow-sm flex-1">
                    <div className="px-4 py-3 border-b border-border">
                      <span className="text-[11px] font-semibold text-foreground">Recent Applications</span>
                    </div>
                    <table className="w-full text-left">
                      <thead className="bg-muted/50 text-[10px] text-muted-foreground font-medium">
                        <tr>
                          <th className="px-4 py-2 font-medium">Date</th>
                          <th className="px-4 py-2 font-medium">Company</th>
                          <th className="px-4 py-2 font-medium">Role</th>
                          <th className="px-4 py-2 font-medium">Status</th>
                        </tr>
                      </thead>
                      <tbody className="text-[11px]">
                        <tr className="border-b border-border/50">
                          <td className="px-4 py-2 text-muted-foreground">Jul 18</td>
                          <td className="px-4 py-2 font-medium text-foreground">Groww</td>
                          <td className="px-4 py-2 text-muted-foreground">SDE II</td>
                          <td className="px-4 py-2"><span className="text-[9px] text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded-full">Interview</span></td>
                        </tr>
                        <tr className="border-b border-border/50">
                          <td className="px-4 py-2 text-muted-foreground">Jul 15</td>
                          <td className="px-4 py-2 font-medium text-foreground">Meesho</td>
                          <td className="px-4 py-2 text-muted-foreground">Backend Engineer</td>
                          <td className="px-4 py-2"><span className="text-[9px] text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded-full">Applied</span></td>
                        </tr>
                        <tr className="border-b border-border/50">
                          <td className="px-4 py-2 text-muted-foreground">Jul 10</td>
                          <td className="px-4 py-2 font-medium text-foreground">PhonePe</td>
                          <td className="px-4 py-2 text-muted-foreground">Data Analyst</td>
                          <td className="px-4 py-2"><span className="text-[9px] text-green-600 bg-green-50 px-1.5 py-0.5 rounded-full">Shortlisted</span></td>
                        </tr>
                        <tr>
                          <td className="px-4 py-2 text-muted-foreground">Jul 5</td>
                          <td className="px-4 py-2 font-medium text-foreground">CRED</td>
                          <td className="px-4 py-2 text-muted-foreground">Product Analyst</td>
                          <td className="px-4 py-2"><span className="text-[9px] text-slate-600 bg-slate-100 px-1.5 py-0.5 rounded-full">Rejected</span></td>
                        </tr>
                      </tbody>
                    </table>
                  </div>

                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>

      <RoleSelectModal open={roleModalOpen} onOpenChange={setRoleModalOpen} />
    </div>
  );
}
