"use client";

import React, { useEffect, useState } from 'react';
import { Button } from '@/components/ui/Button';
import { X, TrendingUp, Download, Briefcase, GraduationCap, Award, FolderGit2, Loader2 } from 'lucide-react';
import { candidateApi } from '@/lib/api';

interface CandidateProfileModalProps {
  candidate: any;
  isOpen: boolean;
  onClose: () => void;
  onDownloadResume?: (candidateId: string) => void;
}

function formatDate(d?: string | null) {
  if (!d) return '';
  try {
    return new Date(d).toLocaleDateString('en-US', { year: 'numeric', month: 'short' });
  } catch {
    return String(d).slice(0, 10);
  }
}

function expRange(exp: any) {
  const from = formatDate(exp.from_date);
  const to = exp.is_current ? 'Present' : formatDate(exp.to_date) || 'Present';
  if (!from && !to) return '';
  return `${from || '—'} – ${to}`;
}

export function CandidateProfileModal({
  candidate,
  isOpen,
  onClose,
  onDownloadResume,
}: CandidateProfileModalProps) {
  const [profile, setProfile] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    if (!isOpen || !candidate?.id) {
      setProfile(null);
      setError('');
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError('');
    candidateApi
      .getPublicProfile(String(candidate.id))
      .then((data) => {
        if (!cancelled) setProfile(data);
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load profile');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [isOpen, candidate?.id]);

  if (!isOpen || !candidate) return null;

  const displayName =
    profile?.full_name || candidate.name || 'Candidate';
  const title =
    profile?.experience?.[0]?.role ||
    profile?.experience?.[0]?.designation ||
    candidate.vertical ||
    candidate.title ||
    'Candidate';
  const careerLevel = profile?.career_level;
  const skills: string[] = profile?.skills?.length
    ? profile.skills
    : candidate.skills || [];
  const experience = profile?.experience || [];
  const education = profile?.education || [];
  const certifications = profile?.certifications || [];
  const projects = profile?.projects || [];

  const handleDownload = async () => {
    if (!onDownloadResume || !candidate.id) return;
    setDownloading(true);
    try {
      await onDownloadResume(String(candidate.id));
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-ink/50 backdrop-blur-sm">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        <div className="px-8 py-6 border-b border-border-soft flex justify-between items-center sticky top-0 bg-white z-10">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 bg-border-soft rounded-full flex items-center justify-center text-xl font-bold text-ink-muted">
              {String(displayName).charAt(0).toUpperCase()}
            </div>
            <div>
              <h2 className="text-2xl font-bold text-ink">{displayName}</h2>
              <p className="text-ink-muted">
                {title}
                {careerLevel ? ` • ${careerLevel}` : ''}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {onDownloadResume && (
              <Button
                variant="outline"
                className="gap-2"
                onClick={handleDownload}
                disabled={downloading}
              >
                {downloading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Download className="w-4 h-4" />
                )}
                Tailored PDF
              </Button>
            )}
            <button
              onClick={onClose}
              className="p-2 text-ink-muted hover:text-ink-muted rounded-full hover:bg-surface-soft"
            >
              <X className="w-6 h-6" />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-8 bg-surface-soft">
          {loading && (
            <div className="flex items-center justify-center py-16 text-ink-muted gap-2">
              <Loader2 className="w-5 h-5 animate-spin" /> Loading profile…
            </div>
          )}
          {error && !loading && (
            <div className="text-center py-12 text-red-600 text-sm">{error}</div>
          )}
          {!loading && !error && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              <div className="md:col-span-2 space-y-6">
                <div className="bg-white p-6 rounded-xl border border-border-soft shadow-sm">
                  <div className="flex items-center gap-2 mb-4 text-primary font-bold">
                    <TrendingUp className="w-5 h-5" /> Fitment Rationale
                  </div>
                  <p className="text-ink leading-relaxed">
                    {candidate.rationale?.trim()
                      ? candidate.rationale
                      : 'No fitment rationale available for this candidate.'}
                  </p>
                  <p className="mt-2 text-xs text-ink-muted">
                    {candidate.rationaleSource === 'llm'
                      ? 'AI-generated match summary (Groq).'
                      : 'Template-based match summary (deterministic fallback).'}
                  </p>
                </div>

                <div className="bg-white p-6 rounded-xl border border-border-soft shadow-sm">
                  <h3 className="font-bold text-ink text-lg mb-4 flex items-center gap-2">
                    <Briefcase className="w-5 h-5 text-ink-muted" /> Experience
                  </h3>
                  {experience.length === 0 ? (
                    <p className="text-sm text-ink-muted">No experience listed.</p>
                  ) : (
                    <div className="border-l-2 border-border-soft pl-4 space-y-6">
                      {experience.map((exp: any) => (
                        <div key={exp.id || `${exp.company_name}-${exp.role}`}>
                          <h4 className="font-bold text-ink">
                            {exp.role || exp.designation || 'Role'}
                          </h4>
                          <p className="text-ink-muted text-sm mb-2">
                            {[exp.company_name, expRange(exp)].filter(Boolean).join(' • ')}
                          </p>
                          {exp.responsibilities && (
                            <p className="text-ink-muted text-sm whitespace-pre-line">
                              {exp.responsibilities}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div className="bg-white p-6 rounded-xl border border-border-soft shadow-sm">
                  <h3 className="font-bold text-ink text-lg mb-4 flex items-center gap-2">
                    <GraduationCap className="w-5 h-5 text-ink-muted" /> Education
                  </h3>
                  {education.length === 0 ? (
                    <p className="text-sm text-ink-muted">No education listed.</p>
                  ) : (
                    <div className="space-y-4">
                      {education.map((ed: any) => (
                        <div key={ed.id || `${ed.institute}-${ed.degree}`}>
                          <h4 className="font-bold text-ink">
                            {[ed.degree, ed.field_of_study].filter(Boolean).join(' in ') ||
                              ed.qualification_level ||
                              'Degree'}
                          </h4>
                          <p className="text-ink-muted text-sm">
                            {[ed.institute, ed.passing_year].filter(Boolean).join(' • ')}
                          </p>
                          {ed.cgpa && (
                            <p className="text-ink-muted text-sm mt-1">CGPA: {ed.cgpa}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {projects.length > 0 && (
                  <div className="bg-white p-6 rounded-xl border border-border-soft shadow-sm">
                    <h3 className="font-bold text-ink text-lg mb-4 flex items-center gap-2">
                      <FolderGit2 className="w-5 h-5 text-ink-muted" /> Projects
                    </h3>
                    <div className="space-y-4">
                      {projects.map((p: any) => (
                        <div key={p.id || p.project_name}>
                          <h4 className="font-bold text-ink">{p.project_name || 'Project'}</h4>
                          {p.tools_used && (
                            <p className="text-xs text-ink-muted italic mb-1">{p.tools_used}</p>
                          )}
                          {(p.responsibilities || p.achievements) && (
                            <p className="text-ink-muted text-sm whitespace-pre-line">
                              {p.responsibilities || p.achievements}
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              <div className="space-y-6">
                <div className="bg-white p-6 rounded-xl border border-border-soft shadow-sm">
                  <h3 className="font-bold text-ink mb-4">Skills</h3>
                  {skills.length === 0 ? (
                    <p className="text-sm text-ink-muted">No skills listed.</p>
                  ) : (
                    <div className="flex flex-wrap gap-2">
                      {skills.map((skill: string) => (
                        <span
                          key={skill}
                          className="bg-surface-soft text-ink px-2.5 py-1 rounded-md text-xs font-medium"
                        >
                          {skill}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                <div className="bg-white p-6 rounded-xl border border-border-soft shadow-sm">
                  <h3 className="font-bold text-ink mb-4 flex items-center gap-2">
                    <Award className="w-5 h-5 text-ink-muted" /> Certifications
                  </h3>
                  {certifications.length === 0 ? (
                    <p className="text-sm text-ink-muted">No certifications listed.</p>
                  ) : (
                    <ul className="space-y-3">
                      {certifications.map((c: any) => (
                        <li key={c.id || c.name} className="text-sm">
                          <div className="font-bold text-ink">{c.name}</div>
                          {c.issuing_org && (
                            <div className="text-ink-muted text-xs">{c.issuing_org}</div>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
