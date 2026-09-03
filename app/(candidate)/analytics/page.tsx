"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { Card } from '@/components/ui/Card';
import { AnalyticsChart } from '@/components/ui/AnalyticsChart';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { Button } from '@/components/ui/Button';
import { BarChart3, TrendingUp, Users, FileText, Download, RefreshCw } from 'lucide-react';
import { analyticsApi } from '@/lib/api';
import { useToast } from '@/components/ui/Toast';
import {
  APPLICATION_STATUS_LABELS,
  CandidateAnalytics,
  candidateAnalyticsToCsv,
  downloadAnalyticsCsv,
} from '@/lib/analytics';

export default function CandidateAnalyticsPage() {
  const { showToast } = useToast();
  const [loading, setLoading] = useState(true);
  const [analytics, setAnalytics] = useState<CandidateAnalytics | null>(null);
  const [days, setDays] = useState(30);

  const fetchAnalytics = useCallback(async () => {
    setLoading(true);
    try {
      const data = await analyticsApi.candidate(days);
      setAnalytics(data);
    } catch {
      showToast('error', 'Failed to load analytics data');
      setAnalytics(null);
    } finally {
      setLoading(false);
    }
  }, [days, showToast]);

  useEffect(() => {
    fetchAnalytics();
  }, [fetchAnalytics]);

  const handleExport = () => {
    if (!analytics) return;
    const { summary, statuses, trend } = candidateAnalyticsToCsv(analytics);
    downloadAnalyticsCsv(`candidate-analytics-summary-${days}d.csv`, summary);
    if (statuses.length) {
      downloadAnalyticsCsv(`candidate-analytics-status-${days}d.csv`, statuses);
    }
    if (trend.length) {
      downloadAnalyticsCsv(`candidate-analytics-trend-${days}d.csv`, trend);
    }
    showToast('success', 'Analytics exported');
  };

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
        <Card className="text-center py-16 space-y-4">
          <p className="text-muted-foreground">Failed to load analytics data</p>
          <Button variant="outline" onClick={fetchAnalytics}>
            <RefreshCw className="w-4 h-4 mr-2" /> Retry
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="py-8 px-4 md:px-8 max-w-6xl mx-auto space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold text-foreground">Analytics</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Track your applications, saved jobs, and fitment scores.
          </p>
        </div>
        <div className="flex items-center gap-2">
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
          <Button variant="outline" onClick={fetchAnalytics} aria-label="Refresh analytics">
            <RefreshCw className="w-4 h-4" />
          </Button>
          <Button variant="outline" onClick={handleExport}>
            <Download className="w-4 h-4 mr-2" /> Export CSV
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-5">
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm text-muted-foreground">Total Applications</p>
            <FileText className="w-4 h-4 text-primary" />
          </div>
          <p className="text-3xl font-bold text-foreground">{analytics.total_applications}</p>
          <p className="text-xs text-muted-foreground mt-1">Last {days} days</p>
        </Card>

        <Card className="p-5">
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm text-muted-foreground">Saved Jobs</p>
            <Users className="w-4 h-4 text-primary" />
          </div>
          <p className="text-3xl font-bold text-foreground">{analytics.saved_jobs}</p>
          <p className="text-xs text-muted-foreground mt-1">Total saved</p>
        </Card>

        <Card className="p-5">
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm text-muted-foreground">Avg Fitment Score</p>
            <TrendingUp className="w-4 h-4 text-primary" />
          </div>
          <p className="text-3xl font-bold text-foreground">{analytics.average_fitment_score}</p>
          <p className="text-xs text-muted-foreground mt-1">Out of 100</p>
        </Card>

        <Card className="p-5">
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm text-muted-foreground">Status Breakdown</p>
            <BarChart3 className="w-4 h-4 text-primary" />
          </div>
          <p className="text-3xl font-bold text-foreground">
            {Object.keys(analytics.status_distribution).length}
          </p>
          <p className="text-xs text-muted-foreground mt-1">Different statuses</p>
        </Card>
      </div>

      <Card className="p-6">
        <h3 className="font-bold text-foreground mb-4">Application Status Distribution</h3>
        <div className="space-y-3">
          {Object.entries(analytics.status_distribution).map(([status, count]) => (
            <div key={status} className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">
                {APPLICATION_STATUS_LABELS[status] || status}
              </span>
              <span className="font-semibold text-foreground">{count}</span>
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
