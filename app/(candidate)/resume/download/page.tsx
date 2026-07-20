import React from 'react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Download, Share2, Mail, Link as LinkIcon } from 'lucide-react';

export default function ResumeDownloadPage() {
  return (
    <div className="min-h-screen bg-slate-50 py-10">
      <div className="max-w-6xl mx-auto px-4">
        
        <div className="flex flex-col lg:flex-row gap-8">
          
          {/* Left Column: Previews */}
          <div className="flex-1 space-y-8">
            <section>
              <h2 className="text-xl font-bold text-slate-900 mb-4">Resume Preview</h2>
              <div className="bg-white border border-slate-200 shadow-sm p-8 min-h-[600px] flex flex-col items-center justify-center text-slate-400">
                 {/* Mock Document */}
                 <div className="w-full h-full border border-slate-100 p-8 space-y-4 text-left">
                   <h1 className="text-2xl font-bold text-slate-800">John Doe</h1>
                   <p className="text-sm">Software Engineer | john@example.com</p>
                   <hr/>
                   <h3 className="font-bold text-slate-700 mt-4">Experience</h3>
                   <div className="h-16 bg-slate-100 rounded w-full"></div>
                   <h3 className="font-bold text-slate-700 mt-4">Education</h3>
                   <div className="h-16 bg-slate-100 rounded w-full"></div>
                 </div>
              </div>
            </section>
            
            <section>
              <h2 className="text-xl font-bold text-slate-900 mb-4">Cover Letter Preview</h2>
              <div className="bg-white border border-slate-200 shadow-sm p-8 min-h-[400px] flex flex-col items-center justify-center text-slate-400">
                 <div className="w-full h-full border border-slate-100 p-8 space-y-4 text-left">
                   <p className="text-sm">Dear Hiring Manager,</p>
                   <div className="h-4 bg-slate-100 rounded w-full"></div>
                   <div className="h-4 bg-slate-100 rounded w-full"></div>
                   <div className="h-4 bg-slate-100 rounded w-3/4"></div>
                   <p className="text-sm mt-8">Sincerely,<br/>John Doe</p>
                 </div>
              </div>
            </section>
          </div>

          {/* Right Column: Actions */}
          <div className="w-full lg:w-96 space-y-6">
            <Card className="sticky top-10">
              <h3 className="text-lg font-bold text-slate-900 mb-4">Generate & Download</h3>
              
              <div className="space-y-4 mb-6">
                <div>
                  <label className="text-sm font-semibold text-slate-800 mb-1 block">Choose Job Role</label>
                  <select className="w-full px-3 py-2 bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary text-slate-900">
                    <option>Frontend Developer</option>
                    <option>Backend Developer</option>
                    <option>Full Stack Engineer</option>
                  </select>
                </div>
              </div>

              <div className="space-y-3">
                <Button className="w-full justify-between" variant="primary">
                  <span>Download Resume (PDF)</span>
                  <Download className="w-4 h-4" />
                </Button>
                <Button className="w-full justify-between" variant="outline">
                  <span>Download Cover Letter</span>
                  <Download className="w-4 h-4" />
                </Button>
              </div>

              <hr className="my-6 border-slate-100" />

              <h4 className="text-sm font-bold text-slate-900 mb-3">Share Profile</h4>
              <div className="flex gap-2">
                <Button variant="ghost" className="flex-1 bg-blue-50 text-blue-700 hover:bg-blue-100">
                  <LinkIcon className="w-4 h-4 mr-2" /> LinkedIn
                </Button>
                <Button variant="ghost" className="flex-1 bg-slate-100 hover:bg-slate-200">
                  <Mail className="w-4 h-4 mr-2" /> Email
                </Button>
                <Button variant="ghost" className="px-3 bg-slate-100 hover:bg-slate-200">
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
