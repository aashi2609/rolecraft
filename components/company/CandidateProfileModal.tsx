"use client";

import React from 'react';
import { Button } from '@/components/ui/Button';
import { X, TrendingUp, Download, Briefcase, GraduationCap, Award } from 'lucide-react';

interface CandidateProfileModalProps {
  candidate: any;
  isOpen: boolean;
  onClose: () => void;
}

export function CandidateProfileModal({ candidate, isOpen, onClose }: CandidateProfileModalProps) {
  if (!isOpen || !candidate) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        
        {/* Header */}
        <div className="px-8 py-6 border-b border-slate-100 flex justify-between items-center sticky top-0 bg-white z-10">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 bg-slate-200 rounded-full flex items-center justify-center text-xl font-bold text-slate-500">
              {candidate.name.charAt(0)}
            </div>
            <div>
              <h2 className="text-2xl font-bold text-slate-900">{candidate.name}</h2>
              <p className="text-slate-500">{candidate.vertical} • Mid Career</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="outline" className="gap-2">
              <Download className="w-4 h-4" /> Tailored PDF
            </Button>
            <button onClick={onClose} className="p-2 text-slate-400 hover:text-slate-600 rounded-full hover:bg-slate-100">
              <X className="w-6 h-6" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-8 bg-slate-50">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            
            {/* Main Column */}
            <div className="md:col-span-2 space-y-6">
              
              <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
                <div className="flex items-center gap-2 mb-4 text-primary font-bold">
                  <TrendingUp className="w-5 h-5" /> AI Fitment Rationale
                </div>
                <p className="text-slate-700 leading-relaxed">
                  {candidate.rationale}
                </p>
              </div>

              <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
                <h3 className="font-bold text-slate-900 text-lg mb-4 flex items-center gap-2">
                  <Briefcase className="w-5 h-5 text-slate-400" /> Experience
                </h3>
                <div className="border-l-2 border-slate-100 pl-4 space-y-6">
                  <div>
                    <h4 className="font-bold text-slate-900">Senior {candidate.vertical} Engineer</h4>
                    <p className="text-slate-500 text-sm mb-2">TechCorp Inc. • 2021 - Present</p>
                    <p className="text-slate-600 text-sm">Led the development of scalable microservices, mentored junior developers, and reduced latency by 30% across core APIs.</p>
                  </div>
                  <div>
                    <h4 className="font-bold text-slate-900">{candidate.vertical} Engineer</h4>
                    <p className="text-slate-500 text-sm mb-2">Startup LLC • 2018 - 2021</p>
                    <p className="text-slate-600 text-sm">Developed and maintained customer-facing applications and dashboards.</p>
                  </div>
                </div>
              </div>

              <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
                <h3 className="font-bold text-slate-900 text-lg mb-4 flex items-center gap-2">
                  <GraduationCap className="w-5 h-5 text-slate-400" /> Education
                </h3>
                <div>
                  <h4 className="font-bold text-slate-900">B.Tech in Computer Science</h4>
                  <p className="text-slate-500 text-sm">Top University • 2014 - 2018</p>
                  <p className="text-slate-600 text-sm mt-1">CGPA: 8.5/10</p>
                </div>
              </div>
              
            </div>

            {/* Sidebar */}
            <div className="space-y-6">
              <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
                <h3 className="font-bold text-slate-900 mb-4">Skills</h3>
                <div className="flex flex-wrap gap-2">
                  {['React', 'TypeScript', 'Node.js', 'AWS', 'System Design', 'Agile'].map(skill => (
                    <span key={skill} className="bg-slate-100 text-slate-700 px-2.5 py-1 rounded-md text-xs font-medium">
                      {skill}
                    </span>
                  ))}
                </div>
              </div>

              <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
                <h3 className="font-bold text-slate-900 mb-4 flex items-center gap-2">
                  <Award className="w-5 h-5 text-slate-400" /> Certifications
                </h3>
                <ul className="space-y-3">
                  <li className="text-sm">
                    <div className="font-bold text-slate-800">AWS Solutions Architect</div>
                    <div className="text-slate-500 text-xs">Amazon Web Services</div>
                  </li>
                  <li className="text-sm">
                    <div className="font-bold text-slate-800">Certified Scrum Master</div>
                    <div className="text-slate-500 text-xs">Scrum Alliance</div>
                  </li>
                </ul>
              </div>
            </div>

          </div>
        </div>

      </div>
    </div>
  );
}
