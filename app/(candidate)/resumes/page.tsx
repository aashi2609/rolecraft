"use client";

import React, { useState } from 'react';
import { useUser } from '@/context/UserContext';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { FileText, Download, RotateCcw, CheckCircle2, AlertCircle } from 'lucide-react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

export default function ResumesPage() {
  const { resumes, plan } = useUser();
  const router = useRouter();
  
  // Local state to track "default" resume
  const [defaultResumeId, setDefaultResumeId] = useState<number | null>(resumes.length > 0 ? 0 : null);

  const isFreePlan = plan === 'free' || !plan;
  const reachedCap = isFreePlan && resumes.length >= 1;

  const handleGenerateClick = () => {
    if (reachedCap) {
      // In a real app we might show a modal, but for now we route to pricing or show alert
      alert('You have reached the resume generation cap for the Free plan. Please upgrade to create more tailored resumes.');
      router.push('/pricing');
      return;
    }
    // Flag skipProfile=true so onboarding starts at vertical selection
    router.push('/onboarding/generate?skipProfile=true');
  };

  return (
    <div className="min-h-screen bg-slate-50 py-10">
      <div className="max-w-5xl mx-auto px-4">
        
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-slate-900 mb-2">My Resumes</h1>
            <p className="text-slate-500">Manage your AI-tailored resume versions across different verticals.</p>
          </div>
          <Button onClick={handleGenerateClick} className="gap-2">
            <FileText className="w-4 h-4" /> 
            + Generate New Version
          </Button>
        </div>

        {reachedCap && (
          <div className="bg-orange-50 border border-orange-200 p-4 rounded-lg flex items-start gap-3 mb-8">
            <AlertCircle className="w-5 h-5 text-orange-500 shrink-0 mt-0.5" />
            <div>
              <h4 className="font-bold text-orange-800">Generation Cap Reached</h4>
              <p className="text-orange-700 text-sm mt-1">
                You are currently on the Free plan, which allows 1 tailored resume version. 
                Upgrade to Premium for unlimited tailoring to different roles.
              </p>
              <Link href="/pricing" className="text-primary hover:underline text-sm font-medium mt-2 inline-block">
                View Pricing Plans →
              </Link>
            </div>
          </div>
        )}

        {resumes.length === 0 ? (
          <Card className="text-center py-20 border-dashed">
            <FileText className="w-16 h-16 text-slate-300 mx-auto mb-4" />
            <h3 className="text-xl font-bold text-slate-900 mb-2">No resumes generated yet</h3>
            <p className="text-slate-500 mb-6 max-w-md mx-auto">Create your first AI-tailored resume to start matching with top employers.</p>
            <Button onClick={handleGenerateClick}>Generate My First Resume</Button>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {resumes.map((resume, i) => (
              <Card key={i} className={`p-6 relative border-2 transition-all ${defaultResumeId === i ? 'border-primary shadow-md' : 'border-slate-200 hover:border-slate-300'}`}>
                
                {defaultResumeId === i && (
                  <div className="absolute top-0 right-0 bg-primary text-white text-xs font-bold px-3 py-1 rounded-bl-lg rounded-tr-lg flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3" /> Default
                  </div>
                )}
                
                <div className="w-12 h-12 bg-blue-50 text-primary rounded-lg flex items-center justify-center mb-4">
                  <FileText className="w-6 h-6" />
                </div>
                
                <h3 className="text-xl font-bold text-slate-900 mb-1">{resume.vertical || 'Frontend Developer'}</h3>
                <p className="text-sm text-slate-500 mb-6">Generated on {resume.date || 'Today'}</p>
                
                <div className="bg-slate-50 p-4 rounded-lg mb-6 border border-slate-100">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium text-slate-700">ATS Score</span>
                    <span className="text-green-600 font-bold">{resume.score || '92'} / 100</span>
                  </div>
                  <div className="w-full bg-slate-200 rounded-full h-2 mt-2 overflow-hidden">
                    <div className="bg-green-500 h-2 rounded-full" style={{ width: `${resume.score || 92}%` }}></div>
                  </div>
                </div>
                
                <div className="space-y-3">
                  <Button variant="outline" className="w-full justify-start gap-3">
                    <Download className="w-4 h-4 text-slate-500" /> Download PDF
                  </Button>
                  <Button variant="outline" className="w-full justify-start gap-3 text-slate-600 hover:text-primary">
                    <RotateCcw className="w-4 h-4" /> Regenerate AI
                  </Button>
                  
                  {defaultResumeId !== i && (
                    <button 
                      className="w-full text-center text-sm text-slate-500 hover:text-primary pt-2 font-medium"
                      onClick={() => setDefaultResumeId(i)}
                    >
                      Set as Default
                    </button>
                  )}
                </div>
              </Card>
            ))}
          </div>
        )}

      </div>
    </div>
  );
}
