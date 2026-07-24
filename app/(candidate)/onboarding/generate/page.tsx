"use client";

import React, { Suspense, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { CheckCircle2, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { FormField } from '@/components/ui/FormField';
import { SearchableCombobox } from '@/components/ui/SearchableCombobox';
import { UpsellPrompt } from '@/components/UpsellPrompt';
import { useUser } from '@/context/UserContext';
import { VERTICALS } from '@/lib/constants';
import { maxTargetRoles, isFreePlan } from '@/lib/plans';
import { resumesApi } from '@/lib/api';

type Phase = 'select' | 'generating' | 'summary';

type GeneratedResume = {
  vertical: string;
  score: number;
  date: string;
  summary?: string;
  mappingNotes?: string;
  highlightedSkills?: string[];
  emphasis?: string[];
  id?: string;
};

function GenerateContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const skipProfile = searchParams.get('skipProfile') === 'true';
  const { plan, resumes, addResume, setCandidateProfile, refreshResumes } = useUser();

  const [roles, setRoles] = useState<string[]>([]);
  const [phase, setPhase] = useState<Phase>('select');
  const [currentRoleIndex, setCurrentRoleIndex] = useState(0);
  const [generated, setGenerated] = useState<GeneratedResume[]>([]);
  const [error, setError] = useState('');

  const freeCapped = isFreePlan(plan);
  const roleLimit = maxTargetRoles(plan);
  const atCap = freeCapped && resumes.length >= 1;

  const onRolesChange = (next: string[]) => {
    if (Number.isFinite(roleLimit) && next.length > roleLimit) {
      setRoles(next.slice(0, roleLimit as number));
      return;
    }
    setRoles(next);
  };

  const startGenerate = async () => {
    if (roles.length === 0 || atCap) return;
    const selected = freeCapped ? roles.slice(0, 1) : roles;
    setRoles(selected);
    setPhase('generating');
    setCurrentRoleIndex(0);
    setGenerated([]);
    setError('');

    // Animate per-role progress while API runs
    selected.forEach((_, idx) => {
      setTimeout(() => setCurrentRoleIndex(idx), idx * 600);
    });

    try {
      const raw = await resumesApi.generate(selected);
      const results: GeneratedResume[] = (raw || []).map((r: any) => ({
        id: r.id,
        vertical: r.target_vertical,
        score: r.ats_score,
        date: r.created_at?.slice?.(0, 10) || new Date().toISOString().slice(0, 10),
        summary: r.content?.summary,
        mappingNotes: r.content?.mappingNotes,
        highlightedSkills: r.content?.highlightedSkills,
        emphasis: r.content?.emphasis,
      }));
      results.forEach((r) => addResume(r));
      setGenerated(results);
      localStorage.setItem('rolecraft_target_verticals', JSON.stringify(selected));
      localStorage.setItem('rolecraft_target_vertical', selected[0] || '');
      setCandidateProfile({ targetVerticals: selected });
      await refreshResumes();
      setPhase('summary');
    } catch (err: any) {
      setError(err?.detail || err?.message || 'Generation failed');
      setPhase('select');
    }
  };

  const goNext = () => {
    router.push(skipProfile ? '/resumes' : '/onboarding/resume-preview');
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center py-10 px-4">
      <div className="w-full max-w-xl bg-white rounded-2xl shadow-card border border-border p-8">
        {phase === 'select' && (
          <>
            <div className="text-center mb-8">
              <div className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-primary mb-4">
                <Sparkles className="w-5 h-5" />
              </div>
              <h2 className="text-2xl font-bold text-foreground mb-2">Choose target roles</h2>
              <p className="text-muted-foreground text-sm">
                Select one or more verticals. We&apos;ll generate a separate tailored resume for each —
                reweighting your profile for genuine cross-domain fit.
              </p>
            </div>

            {freeCapped && (
              <UpsellPrompt
                compact
                className="mb-5"
                title="Free plan: 1 target role at a time"
                description="Upgrade to generate multiple vertical resumes in one pass (e.g. Core Electronics + IT/Software)."
              />
            )}

            {atCap && (
              <UpsellPrompt
                className="mb-5"
                title="Resume generation cap reached"
                description="Your free plan allows one tailored resume. Upgrade to unlock unlimited multi-vertical generations."
              />
            )}

            <div className="text-left mb-6">
              <FormField label="Target roles" required>
                <SearchableCombobox
                  multiSelect
                  options={[...VERTICALS]}
                  value={roles}
                  onChange={onRolesChange}
                  placeholder="e.g. Core Electronics, IT/Software"
                />
              </FormField>
              {freeCapped && roles.length >= 1 && (
                <p className="text-xs text-amber-700 mt-2">
                  Free tier limited to 1 role. Remove it to pick another, or upgrade.
                </p>
              )}
              {roles.length > 0 && (
                <p className="text-xs text-muted-foreground mt-2">
                  Will create {roles.length} separate resume{roles.length === 1 ? '' : 's'}.
                </p>
              )}
            </div>

            {error && <p className="text-sm text-red-600 mb-4 text-left">{error}</p>}

            <Button
              className="w-full"
              onClick={startGenerate}
              disabled={roles.length === 0 || atCap}
            >
              Generate {roles.length > 1 ? `${roles.length} Resumes` : 'Resume'}
            </Button>
          </>
        )}

        {phase === 'generating' && (
          <div className="py-10 flex flex-col items-center text-center">
            <div className="w-12 h-12 border-4 border-primary/30 border-t-primary rounded-full animate-spin mb-6" />
            <h2 className="text-xl font-bold text-foreground mb-2">
              Generating your {roles[currentRoleIndex] || '…'} resume…
            </h2>
            <p className="text-muted-foreground text-sm max-w-sm">
              Mapping transferable experience to this vertical, then writing a tailored ATS version (
              {Math.min(currentRoleIndex + 1, roles.length)} of {roles.length}).
            </p>
            <ul className="mt-8 w-full space-y-2 text-left">
              {roles.map((r, idx) => (
                <li
                  key={r}
                  className={`flex items-center gap-2 text-sm rounded-lg px-3 py-2 ${
                    idx < currentRoleIndex
                      ? 'bg-green-50 text-green-800'
                      : idx === currentRoleIndex
                        ? 'bg-primary/5 text-primary font-medium'
                        : 'bg-secondary text-muted-foreground'
                  }`}
                >
                  {idx < currentRoleIndex ? (
                    <CheckCircle2 className="w-4 h-4" />
                  ) : (
                    <span className="w-4 h-4 rounded-full border border-current inline-block" />
                  )}
                  {r}
                </li>
              ))}
            </ul>
          </div>
        )}

        {phase === 'summary' && (
          <div>
            <div className="text-center mb-6">
              <CheckCircle2 className="w-12 h-12 text-green-500 mx-auto mb-3" />
              <h2 className="text-2xl font-bold text-foreground mb-2">Resumes ready</h2>
              <p className="text-muted-foreground text-sm">
                Generated {generated.length} tailored version{generated.length === 1 ? '' : 's'} from
                your profile.
              </p>
            </div>

            <div className="space-y-3 mb-8">
              {generated.map((r) => (
                <div key={r.vertical} className="rounded-xl border border-border p-4 text-left">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h3 className="font-bold text-foreground">{r.vertical}</h3>
                      <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{r.summary}</p>
                      {r.mappingNotes && (
                        <p className="text-xs text-primary/80 mt-2">{r.mappingNotes}</p>
                      )}
                    </div>
                    <div className="text-right shrink-0">
                      <p className="text-lg font-bold text-green-600">{r.score}</p>
                      <p className="text-[10px] text-muted-foreground uppercase">ATS</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <Button className="w-full" onClick={goNext}>
              {skipProfile ? 'Back to My Resumes' : 'Continue to Preview'}
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

export default function GenerateResumePage() {
  return (
    <Suspense fallback={<div className="min-h-[80vh] flex items-center justify-center">Loading...</div>}>
      <GenerateContent />
    </Suspense>
  );
}
