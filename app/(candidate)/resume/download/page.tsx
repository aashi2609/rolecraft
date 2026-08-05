"use client";

import React, { useEffect, useState, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Download, Share2, Mail, Link as LinkIcon, Loader2, ArrowLeft, Sparkles } from 'lucide-react';
import { useUser } from '@/context/UserContext';
import { resumesApi } from '@/lib/api';
import { FitmentRing } from '@/components/ui/FitmentRing';

function DownloadContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const resumeId = searchParams.get('id');
  const { resumes } = useUser();
  const [downloading, setDownloading] = useState(false);
  const [resume, setResume] = useState<any>(null);

  useEffect(() => {
    // First try to find in context
    if (resumeId) {
      const found = resumes.find((r) => String(r.id) === resumeId);
      if (found) {
        setResume(found);
        return;
      }
      // Otherwise fetch from API
      resumesApi.get(resumeId).then((r: any) => {
        setResume({
          id: r.id,
          vertical: r.target_vertical,
          score: r.ats_score,
          content: r.content,
          atsBreakdown: r.ats_breakdown,
          version: r.version,
        });
      }).catch(() => {});
    } else if (resumes.length > 0) {
      setResume(resumes[0]);
    }
  }, [resumeId, resumes]);

  const handleDownload = async () => {
    if (!resume) return;
    setDownloading(true);
    try {
      const vertical = (resume.vertical || 'resume').replace(/\s+/g, '_').toLowerCase();
      await resumesApi.downloadPdf(String(resume.id), `resume_${vertical}.pdf`);
    } catch (err) {
      console.error('Download failed:', err);
    } finally {
      setDownloading(false);
    }
  };

  const content = resume?.content || {};
  const experience = content.experience || [];
  const education = content.education || [];
  const skills = content.skills || {};
  const projects = content.projects || [];
  const certifications = content.certifications || [];
  const summary = content.professional_summary || content.summary || '';
  const atsBreakdown = resume?.atsBreakdown || content.ats_breakdown;

  return (
    <div className="min-h-screen bg-surface-soft py-10">
      <div className="max-w-6xl mx-auto px-4">
        <button
          type="button"
          onClick={() => router.push('/resumes')}
          className="flex items-center gap-2 text-sm text-muted-foreground hover:text-primary mb-6 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Back to My Resumes
        </button>

        <div className="flex flex-col lg:flex-row gap-8">

          {/* Left Column: Live Preview */}
          <div className="flex-1 space-y-8">
            <section>
              <h2 className="text-xl font-bold text-ink mb-4 flex items-center gap-2">
                Resume Preview
                {resume?.version && resume.version > 1 && (
                  <span className="text-xs bg-primary/10 text-primary px-2 py-0.5 rounded-full font-medium">
                    v{resume.version}
                  </span>
                )}
              </h2>
              <div className="bg-white border border-border-soft shadow-sm p-8 min-h-[600px]">
                <div className="w-full h-full space-y-5 text-left" style={{ fontFamily: "'Georgia', 'Times New Roman', serif" }}>
                  {/* Header */}
                  <div className="text-center pb-3 border-b border-gray-300">
                    <h1 className="text-2xl font-bold text-ink tracking-wider uppercase"
                        style={{ fontFamily: "'Helvetica Neue', sans-serif" }}>
                      {resume?.vertical || 'Resume'}
                    </h1>
                  </div>

                  {/* Summary */}
                  {summary && (
                    <div>
                      <h3 className="text-[10px] font-bold text-ink uppercase tracking-widest mb-1 pb-1 border-b border-gray-200"
                          style={{ fontFamily: "'Helvetica Neue', sans-serif" }}>
                        Professional Summary
                      </h3>
                      <p className="text-sm text-gray-700 leading-relaxed" style={{ textAlign: 'justify' }}>{summary}</p>
                    </div>
                  )}

                  {/* Experience */}
                  {experience.length > 0 && (
                    <div>
                      <h3 className="text-[10px] font-bold text-ink uppercase tracking-widest mb-2 pb-1 border-b border-gray-200"
                          style={{ fontFamily: "'Helvetica Neue', sans-serif" }}>
                        Experience
                      </h3>
                      {experience.map((exp: any, i: number) => (
                        <div key={i} className="mb-3">
                          <div className="flex justify-between items-baseline">
                            <span className="font-semibold text-sm text-ink">{exp.title}</span>
                            <span className="text-xs text-gray-500 italic">{exp.dates}</span>
                          </div>
                          {exp.company && <div className="text-sm italic text-gray-600">{exp.company}</div>}
                          {exp.bullets && (
                            <ul className="mt-1 space-y-0.5">
                              {exp.bullets.map((b: string, j: number) => (
                                <li key={j} className="text-sm text-gray-700 pl-4 relative before:content-['–'] before:absolute before:left-0 before:text-gray-400">
                                  {b}
                                </li>
                              ))}
                            </ul>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Education */}
                  {education.length > 0 && (
                    <div>
                      <h3 className="text-[10px] font-bold text-ink uppercase tracking-widest mb-2 pb-1 border-b border-gray-200"
                          style={{ fontFamily: "'Helvetica Neue', sans-serif" }}>
                        Education
                      </h3>
                      {education.map((edu: any, i: number) => (
                        <div key={i} className="mb-2">
                          <div className="flex justify-between items-baseline">
                            <span className="font-semibold text-sm text-ink">{edu.degree}</span>
                            <span className="text-xs text-gray-500 italic">{edu.year}</span>
                          </div>
                          {edu.institution && <div className="text-sm italic text-gray-600">{edu.institution}</div>}
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Skills */}
                  {(skills.technical?.length > 0 || skills.soft?.length > 0) && (
                    <div>
                      <h3 className="text-[10px] font-bold text-ink uppercase tracking-widest mb-1 pb-1 border-b border-gray-200"
                          style={{ fontFamily: "'Helvetica Neue', sans-serif" }}>
                        Skills
                      </h3>
                      {skills.technical?.length > 0 && (
                        <p className="text-sm"><span className="font-semibold">Technical: </span>{skills.technical.join(', ')}</p>
                      )}
                      {skills.soft?.length > 0 && (
                        <p className="text-sm"><span className="font-semibold">Soft Skills: </span>{skills.soft.join(', ')}</p>
                      )}
                    </div>
                  )}

                  {/* Projects */}
                  {projects.length > 0 && (
                    <div>
                      <h3 className="text-[10px] font-bold text-ink uppercase tracking-widest mb-2 pb-1 border-b border-gray-200"
                          style={{ fontFamily: "'Helvetica Neue', sans-serif" }}>
                        Projects
                      </h3>
                      {projects.map((proj: any, i: number) => (
                        <div key={i} className="mb-2">
                          <div className="flex justify-between items-baseline">
                            <span className="font-semibold text-sm text-ink">{proj.name}</span>
                            {proj.technologies?.length > 0 && (
                              <span className="text-xs text-gray-500 italic">{proj.technologies.join(', ')}</span>
                            )}
                          </div>
                          {proj.description && <p className="text-sm text-gray-700">{proj.description}</p>}
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Certifications */}
                  {certifications.length > 0 && (
                    <div>
                      <h3 className="text-[10px] font-bold text-ink uppercase tracking-widest mb-1 pb-1 border-b border-gray-200"
                          style={{ fontFamily: "'Helvetica Neue', sans-serif" }}>
                        Certifications
                      </h3>
                      {certifications.map((cert: any, i: number) => (
                        <p key={i} className="text-sm">
                          <span className="font-semibold">{cert.name}</span>
                          {cert.issuer && <span className="italic text-gray-500"> — {cert.issuer}</span>}
                        </p>
                      ))}
                    </div>
                  )}

                  {/* Empty state */}
                  {!summary && experience.length === 0 && education.length === 0 && (
                    <div className="flex flex-col items-center justify-center py-20 text-gray-400">
                      <Sparkles className="w-10 h-10 mb-3" />
                      <p className="text-sm">Generate a resume to see the preview here.</p>
                    </div>
                  )}
                </div>
              </div>
            </section>
          </div>

          {/* Right Column: Actions */}
          <div className="w-full lg:w-96 space-y-6">
            <Card className="sticky top-10">
              <h3 className="text-lg font-bold text-ink mb-4">Download Resume</h3>

              {/* ATS Score */}
              {resume?.score && (
                <div className="bg-secondary/60 p-4 rounded-lg mb-4 border border-border">
                  <div className="flex items-center gap-4 mb-2">
                    <FitmentRing score={resume.score} size="small" />
                    <span className="text-sm font-medium text-foreground">ATS Score</span>
                  </div>
                  {atsBreakdown && (
                    <div className="space-y-1.5 mt-3 pt-3 border-t border-border">
                      {Object.entries(atsBreakdown).map(([key, val]) => (
                        <div key={key} className="flex items-center justify-between text-xs">
                          <span className="text-muted-foreground capitalize">{key.replace(/_/g, ' ')}</span>
                          <div className="flex items-center gap-2">
                            <div className="w-16 h-1.5 bg-border rounded-full overflow-hidden">
                              <div
                                className="h-full rounded-full"
                                style={{
                                  width: `${val}%`,
                                  backgroundColor: (val as number) >= 80 ? '#22c55e' : (val as number) >= 60 ? '#f59e0b' : '#ef4444',
                                }}
                              />
                            </div>
                            <span className="font-medium w-6 text-right">{val as number}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              <div className="space-y-3 mb-6">
                <Button
                  className="w-full justify-between"
                  variant="primary"
                  onClick={handleDownload}
                  disabled={downloading || !resume}
                >
                  <span>{downloading ? 'Generating PDF…' : 'Download Resume (PDF)'}</span>
                  {downloading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                </Button>
              </div>

              <hr className="my-6 border-border-soft" />

              <h4 className="text-sm font-bold text-ink mb-3">Share Profile</h4>
              <div className="flex gap-2">
                <Button variant="ghost" className="flex-1 bg-brand-blue/10 text-blue-700 hover:bg-blue-100">
                  <LinkIcon className="w-4 h-4 mr-2" /> LinkedIn
                </Button>
                <Button variant="ghost" className="flex-1 bg-surface-soft hover:bg-border-soft">
                  <Mail className="w-4 h-4 mr-2" /> Email
                </Button>
                <Button variant="ghost" className="px-3 bg-surface-soft hover:bg-border-soft">
                  <Share2 className="w-4 h-4" />
                </Button>
              </div>
            </Card>
          </div>

        </div>

      </div>
    </div>
  );
}

export default function ResumeDownloadPage() {
  return (
    <Suspense fallback={<div className="min-h-[80vh] flex items-center justify-center">Loading...</div>}>
      <DownloadContent />
    </Suspense>
  );
}
