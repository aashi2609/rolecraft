"use client";

import React from 'react';
import { Card } from '@/components/ui/Card';
import { BarChart3, TrendingUp, Users, Eye } from 'lucide-react';

export default function CandidateAnalyticsPage() {
  return (
    <div className="py-8 px-4 md:px-8 max-w-6xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl md:text-3xl font-bold text-foreground">Analytics</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Track your resume views, search appearances, and match rates.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Profile Views', value: '48', change: '+12% this week', icon: Eye },
          { label: 'Search Appearances', value: '112', change: '+24% this week', icon: Users },
          { label: 'Avg Match Rate', value: '87%', change: '+3% improvement', icon: TrendingUp },
          { label: 'Resume Downloads', value: '9', change: '+1 today', icon: BarChart3 },
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
        <h3 className="font-bold text-foreground mb-4">Fitment Trajectory</h3>
        <div className="h-64 bg-surface-soft rounded-lg flex items-end justify-between p-6 gap-2">
          {[64, 72, 69, 78, 85, 92].map((val, idx) => (
            <div key={idx} className="flex-1 flex flex-col items-center gap-2">
              <div 
                className="w-full bg-primary/20 hover:bg-primary transition-all rounded-t-md" 
                style={{ height: `${val}%` }}
              />
              <span className="text-xs text-muted-foreground">Version {idx + 1}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
