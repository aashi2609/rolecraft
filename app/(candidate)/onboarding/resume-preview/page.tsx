"use client";

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Button } from '@/components/ui/Button';
import { CheckCircle2, Download, FileText } from 'lucide-react';
import { useUser } from '@/context/UserContext';
import { getDisplayName, getProfileLocation } from '@/lib/profile';
import { resumesApi } from '@/lib/api';

export default function ResumePreviewPage() {
  const router = useRouter();
  const { resumes, candidateProfile } = useUser();
  const [verticals, setVerticals] = useState<string[]>([]);
  const [active, setActive] = useState(0);

  const displayName = getDisplayName(candidateProfile) || 'Your Name';
  const email = (candidateProfile?.email as string) || '';
  const location = getProfileLocation(candidateProfile) || 'India';

  useEffect(() => {
    const multi = localStorage.getItem('rolecraft_target_verticals');
    if (multi) {
      try {
        const parsed = JSON.parse(multi);
        if (Array.isArray(parsed) && parsed.length) {
          setVerticals(parsed);
          return;
        }
      } catch {
        /* ignore */
      }
    }
    const stored = localStorage.getItem('rolecraft_target_vertical');
    if (stored) setVerticals([stored]);
    else if (resumes.length) setVerticals(resumes.map((r) => r.vertical).filter(Boolean));
    else setVerticals(['your targeted role']);
  }, [resumes]);

  const vertical = verticals[active] || 'your targeted role';
  const resumeMeta = resumes.find((r) => r.vertical === vertical);
  const score = resumeMeta?.score ?? null;
  const safeFileName = displayName.replace(/\s+/g, '_');

  const handleDownload = async () => {
    if (!resumeMeta?.id) return;
    try {
      await resumesApi.downloadPdf(String(resumeMeta.id), `${safeFileName}_${vertical.replace(/\s+/g, '_')}_Resume.pdf`);
    } catch {
      alert('PDF download failed. Try again from My Resumes.');
    }
  };

  return (
    <div className="max-w-4xl mx-auto py-10 px-4">
      <div className="flex flex-col md:flex-row md:justify-between md:items-end gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold text-foreground mb-2">Your Resume is Ready!</h1>
          <p className="text-muted-foreground text-sm">
            {verticals.length > 1
              ? `${verticals.length} tailored versions generated — preview each below.`
              : (
                <>
                  Perfectly tailored for{' '}
                  <span className="font-medium text-foreground">{vertical}</span> positions.
                </>
              )}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" className="gap-2" onClick={handleDownload} disabled={!resumeMeta?.id}>
            <Download className="w-4 h-4" /> Download PDF
          </Button>
          <Button onClick={() => router.push('/dashboard')}>Continue to Dashboard</Button>
        </div>
      </div>

      {verticals.length > 1 && (
        <div className="flex flex-wrap gap-2 mb-6">
          {verticals.map((v, i) => (
            <button
              key={v}
              type="button"
              onClick={() => setActive(i)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                i === active
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-secondary text-muted-foreground hover:text-foreground'
              }`}
            >
              {v}
            </button>
          ))}
        </div>
      )}

      <div className="bg-white rounded-xl shadow-card border border-border overflow-hidden">
        <div className="bg-secondary/50 border-b border-border p-4 flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-2 text-foreground font-medium">
            <FileText className="w-5 h-5 text-primary" />
            {safeFileName}_{vertical.replace(/\s+/g, '_')}_Resume.pdf
          </div>
          {score != null && (
            <div className="flex items-center gap-1.5 bg-green-50 text-green-700 px-3 py-1 rounded-full text-sm font-medium border border-green-200">
              <CheckCircle2 className="w-4 h-4" />
              {score}/100 — ATS Ready
            </div>
          )}
        </div>

        <div className="p-8 md:p-12 bg-white text-sm text-foreground/80 leading-relaxed mx-auto max-w-3xl">
          <div className="text-center mb-8 border-b border-border pb-6">
            <h2 className="text-3xl font-bold text-foreground mb-2">{displayName}</h2>
            <p className="text-muted-foreground">
              {location}
              {email ? ` • ${email}` : ''}
            </p>
            <p className="text-primary font-medium mt-1">{vertical}</p>
          </div>

          {resumeMeta?.summary && (
            <div className="mb-6">
              <h3 className="font-bold text-foreground uppercase tracking-wide mb-2 text-xs">
                Professional Summary
              </h3>
              <p>{resumeMeta.summary}</p>
            </div>
          )}

          {resumeMeta?.mappingNotes && (
            <div className="mb-6 rounded-lg bg-primary/5 border border-primary/15 p-4 text-sm">
              <p className="font-semibold text-primary mb-1">Cross-domain mapping</p>
              <p className="text-foreground/80">{resumeMeta.mappingNotes}</p>
            </div>
          )}

          <div className="mb-6">
            <h3 className="font-bold text-foreground uppercase tracking-wide mb-2 text-xs">
              Highlighted Skills
            </h3>
            <div className="flex flex-wrap gap-2">
              {(resumeMeta?.highlightedSkills || (candidateProfile?.skills as string[]) || []).map(
                (s: string) => (
                  <span key={s} className="px-2 py-1 rounded-md bg-secondary text-xs font-medium">
                    {s}
                  </span>
                )
              )}
            </div>
          </div>

          <div className="mb-6">
            <h3 className="font-bold text-foreground uppercase tracking-wide mb-2 text-xs">
              Experience Emphasis
            </h3>
            <ul className="list-disc pl-5 space-y-1">
              {(resumeMeta?.emphasis || [
                'Delivered outcomes aligned to this vertical',
                'Collaborated across teams with measurable impact',
              ]).map((item: string) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>

          <div className="text-center pt-4">
            <Link href="/resumes" className="text-sm text-primary font-medium hover:underline">
              View all versions in My Resumes →
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
