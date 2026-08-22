"use client";

import { useEffect, useState } from "react";
import { adminApi } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Search } from "lucide-react";
import { Badge } from "@/components/ui/badge";

export default function AdminJobsPage() {
  const [jobs, setJobs] = useState<any[]>([]);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [loading, setLoading] = useState(true);

  const fetchJobs = () => {
    setLoading(true);
    const params: any = {};
    if (search) params.search = search;
    if (statusFilter && statusFilter !== "all") params.status = statusFilter;
    
    adminApi.getJobs(params)
      .then((data) => setJobs(data as any[]))
      .catch(err => console.error(err))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchJobs();
  }, [statusFilter]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchJobs();
  };

  const handleStatusChange = async (jobId: string, newStatus: string) => {
    try {
      await adminApi.updateJob(jobId, { status: newStatus });
      setJobs(jobs.map(j => j.id === jobId ? { ...j, status: newStatus } : j));
    } catch (err) {
      console.error(err);
      alert("Failed to update job status");
    }
  };

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Jobs Management</h1>
        <p className="text-muted-foreground">View and moderate job postings across the platform.</p>
      </div>

      <div className="flex flex-col sm:flex-row gap-4">
        <form onSubmit={handleSearch} className="flex flex-1 gap-2">
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <input 
              type="search" 
              placeholder="Search by job title..." 
              className="flex h-10 w-full rounded-md border border-border-soft bg-transparent px-3 py-2 text-sm pl-8 outline-none focus:ring-2 focus:ring-brand-blue"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <Button type="submit" variant="secondary">Search</Button>
        </form>
        
        <select 
          value={statusFilter} 
          onChange={(e) => setStatusFilter(e.target.value)}
          className="flex h-10 w-[180px] rounded-md border border-border-soft bg-transparent px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-brand-blue"
        >
          <option value="all">All Statuses</option>
          <option value="live">Live</option>
          <option value="draft">Draft</option>
          <option value="closed">Closed</option>
        </select>
      </div>

      <div className="border border-border-soft rounded-lg bg-surface-white overflow-hidden">
        <div className="w-full overflow-auto">
          <table className="w-full text-sm text-left">
            <thead className="border-b border-border-soft bg-surface-soft">
              <tr>
                <th className="h-12 px-4 align-middle font-medium text-muted-foreground">Job Title</th>
                <th className="h-12 px-4 align-middle font-medium text-muted-foreground">Company</th>
                <th className="h-12 px-4 align-middle font-medium text-muted-foreground">Location</th>
                <th className="h-12 px-4 align-middle font-medium text-muted-foreground">Applications</th>
                <th className="h-12 px-4 align-middle font-medium text-muted-foreground">Posted</th>
                <th className="h-12 px-4 align-middle font-medium text-muted-foreground w-[150px]">Status</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={6} className="text-center py-8 text-muted-foreground animate-pulse">
                    Loading jobs...
                  </td>
                </tr>
              ) : jobs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-8 text-muted-foreground">
                    No jobs found matching your filters.
                  </td>
                </tr>
              ) : (
                jobs.map((job) => (
                  <tr key={job.id} className="border-b border-border-soft transition-colors hover:bg-surface-soft/50 data-[state=selected]:bg-surface-soft">
                    <td className="p-4 align-middle font-medium">{job.title}</td>
                    <td className="p-4 align-middle">{job.company_name || <span className="text-muted-foreground italic text-xs">Unknown</span>}</td>
                    <td className="p-4 align-middle text-muted-foreground text-sm">{job.location || 'Remote'}</td>
                    <td className="p-4 align-middle">
                      <Badge variant="secondary">{job.application_count}</Badge>
                    </td>
                    <td className="p-4 align-middle text-muted-foreground text-sm">
                      {new Date(job.created_at).toLocaleDateString()}
                    </td>
                    <td className="p-4 align-middle">
                      <select 
                        value={job.status} 
                        onChange={(e) => handleStatusChange(job.id, e.target.value)}
                        className={`h-8 w-full rounded-md border border-border-soft bg-transparent px-2 text-sm outline-none focus:ring-1 focus:ring-brand-blue ${job.status === 'live' ? 'text-green-600 font-medium border-green-200' : ''}`}
                      >
                        <option value="live">Live</option>
                        <option value="draft">Draft</option>
                        <option value="closed">Closed</option>
                      </select>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
