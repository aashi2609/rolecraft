"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { FileText, Download, RotateCcw, CheckCircle2, Sparkles, Loader2, ChevronDown, ChevronUp } from 'lucide-react';
import { useUser } from '@/context/UserContext';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { UpsellPrompt } from '@/components/UpsellPrompt';
import { FitmentRing } from '@/components/ui/FitmentRing';
import { isFreePlan } from '@/lib/plans';
import { resumesApi } from '@/lib/api';

export default function ResumesPage() {
  const { resumes, plan, refreshResumes } = useUser();
  const router = useRouter();
  const [defaultResumeId, setDefaultResumeId] = useState<number | string | null>(
    resumes[0]?.id ?? null
  );
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [regeneratingId, setRegeneratingId] = useState<string | null>(null);
  const [expandedBreakdown, setExpandedBreakdown] = useState<string | null>(null);
  const [isCustomDownloadOpen, setIsCustomDownloadOpen] = useState(false);
  const [customRole, setCustomRole] = useState('');
  const [isCustomDownloading, setIsCustomDownloading] = useState(false);

  const free = isFreePlan(plan);
  const reachedCap = free && resumes.length >= 1;
  const [limitError, setLimitError] = useState<string | null>(null);

  const handleGenerateClick = () => {
    if (reachedCap) {
      setLimitError('Free plan allows 1 tailored resume. Upgrade to generate another vertical.');
      router.push('/subscribe?role=candidate');
      return;
    }
    setLimitError(null);
    router.push('/onboarding/generate?skipProfile=true');
  };

  const handleDownload = async (resume: any) => {
    const id = String(resume.id);
    setDownloadingId(id);
    try {
      const vertical = (resume.vertical || 'resume').replace(/\s+/g, '_').toLowerCase();
      await resumesApi.downloadPdf(id, `resume_${vertical}.pdf`);
    } catch (err: any) {
      console.error('Download failed:', err);
      alert(err?.message || 'PDF download failed. Please try again.');
    } finally {
      setDownloadingId(null);
    }
  };

  const handleRegenerate = async (resume: any) => {
    const id = String(resume.id);
    setRegeneratingId(id);
    setLimitError(null);
    try {
      await resumesApi.regenerate(id);
      await refreshResumes();
    } catch (err: any) {
      console.error('Regenerate failed:', err);
      const msg = err?.message || 'Regenerate failed';
      const isLimit =
        err?.status === 402 ||
        err?.status === 403 ||
        /upgrade|limit|plan/i.test(msg);
      if (isLimit) {
        setLimitError(msg);
      } else {
        alert(msg);
      }
    } finally {
      setRegeneratingId(null);
    }
  };

  const handleCustomDownload = async () => {
    if (!customRole) return;
    setIsCustomDownloading(true);
    try {
      await resumesApi.downloadTailored(customRole);
      setIsCustomDownloadOpen(false);
      setCustomRole('');
    } catch (err: any) {
      console.error('Custom download failed', err);
      alert('Failed: ' + err.message);
    } finally {
      setIsCustomDownloading(false);
    }
  };

  return (
    <div className="py-8 px-4 md:px-8 max-w-6xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-foreground">My Resumes</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Manage AI-tailored resume versions across different verticals.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setIsCustomDownloadOpen(true)} className="gap-2">
            <Download className="w-4 h-4" />
            Download Custom Tailored PDF
          </Button>
          <Button onClick={handleGenerateClick} className="gap-2">
            <FileText className="w-4 h-4" />
            + Generate New Version
          </Button>
        </div>
      </div>

      {isCustomDownloadOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <Card className="w-full max-w-md p-6 m-4 animate-in fade-in zoom-in-95">
            <h3 className="text-xl font-bold mb-2">Custom Tailored Resume</h3>
            <p className="text-muted-foreground text-sm mb-4">
              Enter a specific job role (e.g. &quot;Senior React Developer&quot;) and our AI will generate a tailored resume PDF on the fly based on your profile!
            </p>
            <input 
              type="text" 
              className="w-full border rounded-md p-2 mb-4" 
              placeholder="Target Role"
              value={customRole}
              onChange={(e) => setCustomRole(e.target.value)}
              disabled={isCustomDownloading}
            />
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setIsCustomDownloadOpen(false)} disabled={isCustomDownloading}>Cancel</Button>
              <Button onClick={handleCustomDownload} disabled={isCustomDownloading || !customRole}>
                {isCustomDownloading ? (
                  <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Generating PDF...</>
                ) : (
                  'Download PDF'
                )}
              </Button>
            </div>
          </Card>
        </div>
      )}

      {(reachedCap || limitError) && (
        <UpsellPrompt
          className="mb-8"
          title="Generation cap reached"
          description={
            limitError ||
            'Free plan allows 1 tailored resume at a time. Upgrade for unlimited multi-vertical generations.'
          }
        />
      )}

      {resumes.some(r => r.is_stale) && (
        <div className="mb-8 bg-yellow-50 border border-yellow-200 rounded-xl p-5 flex flex-col md:flex-row items-center justify-between gap-4">
          <div>
            <h3 className="font-bold text-yellow-800 text-lg flex items-center gap-2">
              <span className="text-xl">⚠️</span> Profile Updated
            </h3>
            <p className="text-yellow-700 text-sm mt-1 max-w-xl">
              You recently updated your profile. Some of your generated resumes are now out of date. Click "Update Resume" on any outdated card below to regenerate it with your latest changes.
            </p>
          </div>
        </div>
      )}

      {resumes.length === 0 ? (
        <Card className="text-center py-20 border-dashed">
          <FileText className="w-16 h-16 text-muted-foreground/30 mx-auto mb-4" />
          <h3 className="text-xl font-bold text-foreground mb-2">No resumes generated yet</h3>
          <p className="text-muted-foreground mb-6 max-w-md mx-auto text-sm">
            Create your first AI-tailored resume — or generate several verticals at once on a paid plan.
          </p>
          <Button onClick={handleGenerateClick}>Generate My First Resume</Button>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {resumes.map((resume) => {
            const isDefault = defaultResumeId === resume.id;
            const isDownloading = downloadingId === String(resume.id);
            const isRegenerating = regeneratingId === String(resume.id);
            const hasBreakdown = resume.atsBreakdown || resume.content?.ats_breakdown;
            const breakdown = resume.atsBreakdown || resume.content?.ats_breakdown;
            const isExpanded = expandedBreakdown === String(resume.id);

            return (
              <Card
                key={resume.id}
                className={`p-6 relative border-2 transition-all ${
                  isDefault ? 'border-primary shadow-md' : 'border-border hover:border-primary/30'
                }`}
              >
                {isDefault && (
                  <div className="absolute top-0 right-0 bg-primary text-primary-foreground text-xs font-bold px-3 py-1 rounded-bl-lg rounded-tr-lg flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3" /> Default
                  </div>
                )}

                <div className="w-12 h-12 bg-primary/10 text-primary rounded-lg flex items-center justify-center mb-4">
                  <FileText className="w-6 h-6" />
                </div>

                <div className="flex items-center gap-2 mb-1">
                  <h3 className="text-xl font-bold text-foreground">
                    {resume.vertical || 'Untitled'}
                  </h3>
                  {resume.is_stale && (
                    <span className="bg-yellow-100 text-yellow-800 text-[10px] px-1.5 py-0.5 rounded-full font-bold uppercase whitespace-nowrap">
                      Outdated
                    </span>
                  )}
                </div>
                <p className="text-sm text-muted-foreground mb-2">
                  Generated on {resume.date || 'Today'}
                  {resume.version && resume.version > 1 && (
                    <span className="text-xs text-primary ml-2">v{resume.version}</span>
                  )}
                </p>
                {resume.mappingNotes && (
                  <p className="text-xs text-primary/80 mb-4 line-clamp-2">{resume.mappingNotes}</p>
                )}

                {/* ATS Score */}
                <div className="bg-secondary/60 p-4 rounded-lg mb-4 border border-border">
                  <div className="flex items-center gap-4">
                    <FitmentRing score={resume.score || 0} size="small" />
                    <div className="flex-1">
                      <span className="text-sm font-medium text-foreground">ATS Score</span>
                      {resume.generationMethod === 'ai' ? (
                        <span className="ml-2 inline-flex items-center gap-1 text-[10px] bg-primary/10 text-primary px-1.5 py-0.5 rounded-full font-medium">
                          <Sparkles className="w-2.5 h-2.5" /> AI
                        </span>
                      ) : (
                        <span className="ml-2 inline-flex items-center gap-1 text-[10px] bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded-full font-medium" title="Generated using fallback deterministic logic (likely due to API rate limits)">
                          ⚠️ Fallback
                        </span>
                      )}
                    </div>
                    {hasBreakdown && (
                      <button
                        type="button"
                        className="text-xs text-muted-foreground hover:text-primary"
                        onClick={() => setExpandedBreakdown(isExpanded ? null : String(resume.id))}
                      >
                        {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </button>
                    )}
                  </div>

                  {/* ATS Breakdown */}
                  {isExpanded && breakdown && (
                    <div className="mt-3 pt-3 border-t border-border space-y-2">
                      {Object.entries(breakdown).map(([key, val]) => (
                        <div key={key} className="flex items-center justify-between text-xs">
                          <span className="text-muted-foreground capitalize">
                            {key.replace(/_/g, ' ')}
                          </span>
                          <div className="flex items-center gap-2">
                            <div className="w-20 h-1.5 bg-border rounded-full overflow-hidden">
                              <div
                                className="h-full rounded-full transition-all"
                                style={{
                                  width: `${val}%`,
                                  backgroundColor:
                                    (val as number) >= 80
                                      ? '#22c55e'
                                      : (val as number) >= 60
                                        ? '#f59e0b'
                                        : '#ef4444',
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

                <div className="space-y-3">
                  <Button
                    variant="outline"
                    className="w-full justify-start gap-3"
                    onClick={() => handleDownload(resume)}
                    disabled={isDownloading}
                  >
                    {isDownloading ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Download className="w-4 h-4 text-muted-foreground" />
                    )}
                    {isDownloading ? 'Generating PDF…' : 'Download PDF'}
                  </Button>
                  <Button
                    variant={resume.is_stale ? "default" : "outline"}
                    className={`w-full justify-start gap-3 ${resume.is_stale ? "bg-yellow-600 hover:bg-yellow-700 text-white" : ""}`}
                    onClick={() => handleRegenerate(resume)}
                    disabled={isRegenerating}
                  >
                    {isRegenerating ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <RotateCcw className="w-4 h-4" />
                    )}
                    {isRegenerating ? 'Updating…' : resume.is_stale ? 'Update Resume' : 'Regenerate AI'}
                  </Button>

                  {!isDefault && (
                    <button
                      type="button"
                      className="w-full text-center text-sm text-muted-foreground hover:text-primary pt-2 font-medium"
                      onClick={() => setDefaultResumeId(resume.id)}
                    >
                      Set as Default
                    </button>
                  )}
                </div>
              </Card>
            );
          })}
        </div>
      )}

      <p className="text-center text-sm text-muted-foreground mt-10">
        Need more verticals?{' '}
        <Link href="/subscribe?role=candidate" className="text-primary font-medium hover:underline">
          View plans
        </Link>
      </p>
    </div>
  );
}
