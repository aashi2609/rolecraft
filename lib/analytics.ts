export interface TrendPoint {
  date: string;
  count: number;
}

export interface CandidateAnalytics {
  period_days: number;
  total_applications: number;
  saved_jobs: number;
  average_fitment_score: number;
  status_distribution: Record<string, number>;
  application_trend: TrendPoint[];
}

export interface CompanyAnalytics {
  period_days: number;
  total_jobs: number;
  total_applications: number;
  average_fitment_score: number;
  status_distribution: Record<string, number>;
  response_rate: number;
  application_trend: TrendPoint[];
}

export const APPLICATION_STATUS_LABELS: Record<string, string> = {
  applied: 'Applied',
  shortlisted: 'Shortlisted',
  rejected: 'Rejected',
  interview: 'Interview',
};

function escapeCsv(value: string | number): string {
  const text = String(value);
  if (text.includes(',') || text.includes('"') || text.includes('\n')) {
    return `"${text.replace(/"/g, '""')}"`;
  }
  return text;
}

export function downloadAnalyticsCsv(filename: string, rows: Record<string, string | number>[]): void {
  if (!rows.length) return;
  const headers = Object.keys(rows[0]);
  const lines = [
    headers.join(','),
    ...rows.map((row) => headers.map((key) => escapeCsv(row[key] ?? '')).join(',')),
  ];
  const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export function candidateAnalyticsToCsv(data: CandidateAnalytics) {
  const summary = [
    { metric: 'Period (days)', value: data.period_days },
    { metric: 'Total applications', value: data.total_applications },
    { metric: 'Saved jobs', value: data.saved_jobs },
    { metric: 'Average fitment score', value: data.average_fitment_score },
  ];
  const statuses = Object.entries(data.status_distribution).map(([status, count]) => ({
    status: APPLICATION_STATUS_LABELS[status] || status,
    count,
  }));
  const trend = data.application_trend.map((point) => ({
    date: point.date,
    applications: point.count,
  }));
  return { summary, statuses, trend };
}

export function companyAnalyticsToCsv(data: CompanyAnalytics) {
  const summary = [
    { metric: 'Period (days)', value: data.period_days },
    { metric: 'Total jobs', value: data.total_jobs },
    { metric: 'Total applications', value: data.total_applications },
    { metric: 'Average fitment score', value: data.average_fitment_score },
    { metric: 'Response rate (%)', value: data.response_rate },
  ];
  const statuses = Object.entries(data.status_distribution).map(([status, count]) => ({
    status: APPLICATION_STATUS_LABELS[status] || status,
    count,
  }));
  const trend = data.application_trend.map((point) => ({
    date: point.date,
    applications: point.count,
  }));
  return { summary, statuses, trend };
}
