"use client";

import React from 'react';
import { Card } from '@/components/ui/Card';
import { BarChart3, TrendingUp, Users, ClipboardList } from 'lucide-react';

export default function CompanyAnalyticsPage() {
  return (
    <div className="py-8 px-4 md:px-8 max-w-6xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl md:text-3xl font-bold text-foreground">Hiring Analytics</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Monitor job posting engagement, applicant fitment scores, and response times.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Job Page Views', value: '1,420', change: '+18% this month', icon: Users },
          { label: 'Total Applications', value: '184', change: '+32 this week', icon: ClipboardList },
          { label: 'Avg Candidate Fit', value: '78%', change: '+2% quality lift', icon: TrendingUp },
          { label: 'Response Rate', value: '94%', change: 'Typically 2 days', icon: BarChart3 },
        ].map((stat) => (
          <Card key={stat.label} className="p-5">
            <div className="flex items-center justify-between mb-3">
              <p className="text-sm text-muted-foreground">{stat.label}</p>
              <stat.icon className="w-4 h-4 text-primary" />
            </div>
            <p className="text-3xl font-bold text-foreground">{stat.value}</p>
            <p className="text-xs text-green-600 font-medium mt-1">{stat.change}</p>
          </Card>
        ))}
      </div>

      <Card className="p-6">
        <h3 className="font-bold text-foreground mb-4">Fitment Distribution (All Candidates)</h3>
        <div className="h-64 bg-surface-soft rounded-lg flex items-end justify-between p-6 gap-2">
          {[20, 35, 60, 95, 50, 30].map((val, idx) => {
            const labels = ['<50%', '50-60%', '60-70%', '70-80%', '80-90%', '90%+'];
            return (
              <div key={idx} className="flex-1 flex flex-col items-center gap-2">
                <div 
                  className="w-full bg-primary/20 hover:bg-primary transition-all rounded-t-md" 
                  style={{ height: `${val * 2}%` }}
                />
                <span className="text-xs text-muted-foreground">{labels[idx]}</span>
              </div>
            );
          })}
        </div>
      </Card>
    </div>
  );
}
