"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { FileText, Download, RotateCcw, CheckCircle2 } from 'lucide-react';
import { useUser } from '@/context/UserContext';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { UpsellPrompt } from '@/components/UpsellPrompt';
import { FitmentRing } from '@/components/ui/FitmentRing';
import { isFreePlan } from '@/lib/plans';

export default function ResumesPage() {
  const { resumes, plan } = useUser();
  const router = useRouter();
  const [defaultResumeId, setDefaultResumeId] = useState<number | string | null>(
    resumes[0]?.id ?? null
  );

  const free = isFreePlan(plan);
  const reachedCap = free && resumes.length >= 1;

  const handleGenerateClick = () => {
    if (reachedCap) {
      router.push('/subscribe?role=candidate');
      return;
    }
    router.push('/onboarding/generate?skipProfile=true');
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
        <Button onClick={handleGenerateClick} className="gap-2">
          <FileText className="w-4 h-4" />
          + Generate New Version
        </Button>
      </div>

      {reachedCap && (
        <UpsellPrompt
          className="mb-8"
          title="Generation cap reached"
          description="Free plan allows 1 tailored resume at a time. Upgrade for unlimited multi-vertical generations."
        />
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

                <h3 className="text-xl font-bold text-foreground mb-1">
                  {resume.vertical || 'Untitled'}
                </h3>
                <p className="text-sm text-muted-foreground mb-2">
                  Generated on {resume.date || 'Today'}
                </p>
                {resume.mappingNotes && (
                  <p className="text-xs text-primary/80 mb-4 line-clamp-2">{resume.mappingNotes}</p>
                )}

                <div className="bg-secondary/60 p-4 rounded-lg mb-6 border border-border flex items-center gap-4">
                  <FitmentRing score={resume.score || 92} size="small" />
                  <span className="text-sm font-medium text-foreground">ATS Score</span>
                </div>

                <div className="space-y-3">
                  <Button variant="outline" className="w-full justify-start gap-3">
                    <Download className="w-4 h-4 text-muted-foreground" /> Download PDF
                  </Button>
                  <Button
                    variant="outline"
                    className="w-full justify-start gap-3"
                    onClick={() => router.push('/onboarding/generate?skipProfile=true')}
                  >
                    <RotateCcw className="w-4 h-4" /> Regenerate AI
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
