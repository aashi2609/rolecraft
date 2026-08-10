"use client";

import React, { useState, useEffect } from 'react';
import { Card } from '@/components/ui/Card';
import { AnalyticsChart } from '@/components/ui/AnalyticsChart';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { BarChart3, TrendingUp, Users, ClipboardList, Briefcase } from 'lucide-react';
import { analyticsApi } from '@/lib/api';
import { useToast } from '@/components/ui/Toast';

export default function CompanyAnalyticsPage() {
  const { showToast } = useToast();
  const [loading, setLoading] = useState(true);
  const [analytics, setAnalytics] = useState<any>(null);
  const [days, setDays] = useState(30);

  const fetchAnalytics = async () => {
    setLoading(true);
    try {
      const data = await analyticsApi.company(days);
      setAnalytics(data);
    } catch (error) {
      showToast('error', 'Failed to load analytics data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, [days]);

  if (loading) {
    return (
      <div className="py-8 px-4 md:px-8 max-w-6xl mx-auto">
        <LoadingSpinner size="lg" className="mx-auto" />
      </div>
    );
  }

  if (!analytics) {
    return (
      <div className="py-8 px-4 md:px-8 max-w-6xl mx-auto">
        <Card className="text-center py-16">
          <p className="text-muted-foreground">Failed to load analytics data</p>
        </Card>
      </div>
    );
  }

  const statusLabels = {
    applied: 'Applied',
    shortlisted: 'Shortlisted',
    rejected: 'Rejected',
    interview: 'Interview',
  };

  return (
    <div className="py-8 px-4 md:px-8 max-w-6xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-foreground">Hiring Analytics</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Monitor job posting engagement, applicant fitment scores, and response times.
          </p>
        </div>
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="px-3 py-2 border rounded-lg bg-background"
        >
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
          <option value={365}>Last year</option>
        </select>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-5">
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm text-muted-foreground">Active Jobs</p>
            <Briefcase className="w-4 h-4 text-primary" />
          </div>
          <p className="text-3xl font-bold text-foreground">{analytics.total_jobs}</p>
          <p className="text-xs text-muted-foreground mt-1">Total postings</p>
        </Card>

        <Card className="p-5">
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm text-muted-foreground">Total Applications</p>
            <ClipboardList className="w-4 h-4 text-primary" />
          </div>
          <p className="text-3xl font-bold text-foreground">{analytics.total_applications}</p>
          <p className="text-xs text-muted-foreground mt-1">Last {days} days</p>
        </Card>

        <Card className="p-5">
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm text-muted-foreground">Avg Candidate Fit</p>
            <TrendingUp className="w-4 h-4 text-primary" />
          </div>
          <p className="text-3xl font-bold text-foreground">{analytics.average_fitment_score}</p>
          <p className="text-xs text-muted-foreground mt-1">Out of 100</p>
        </Card>

        <Card className="p-5">
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm text-muted-foreground">Response Rate</p>
            <BarChart3 className="w-4 h-4 text-primary" />
          </div>
          <p className="text-3xl font-bold text-foreground">{analytics.response_rate}%</p>
          <p className="text-xs text-muted-foreground mt-1">Applications reviewed</p>
        </Card>
      </div>

      <Card className="p-6">
        <h3 className="font-bold text-foreground mb-4">Application Status Distribution</h3>
        <div className="space-y-3">
          {Object.entries(analytics.status_distribution).map(([status, count]) => (
            <div key={status} className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">{statusLabels[status as keyof typeof statusLabels] || status}</span>
              <span className="font-semibold text-foreground">{count as number}</span>
            </div>
          ))}
          {Object.keys(analytics.status_distribution).length === 0 && (
            <p className="text-sm text-muted-foreground text-center py-4">No applications yet</p>
          )}
        </div>
      </Card>

      <AnalyticsChart data={analytics.application_trend} />
    </div>
  );
}
