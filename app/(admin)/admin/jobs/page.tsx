"use client";

import { useEffect, useState } from "react";
import { adminApi } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Search, Plus, Edit2, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";

export default function AdminJobsPage() {
  const [jobs, setJobs] = useState<any[]>([]);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [loading, setLoading] = useState(true);

  // Modal states
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  
  const [selectedJob, setSelectedJob] = useState<any>(null);
  
  // Form states
  const [formData, setFormData] = useState({
    title: "",
    company_id: "",
    status: "draft",
    location: "",
    employment_type: ""
  });

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

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await adminApi.createJob(formData);
      setIsCreateOpen(false);
      fetchJobs();
      setFormData({ title: "", company_id: "", status: "draft", location: "", employment_type: "" });
    } catch (err) {
      console.error(err);
      alert("Failed to create job");
    }
  };

  const handleEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedJob) return;
    try {
      await adminApi.updateJob(selectedJob.id, {
        title: formData.title,
        status: formData.status,
        location: formData.location,
        employment_type: formData.employment_type
      });
      setIsEditOpen(false);
      fetchJobs();
    } catch (err) {
      console.error(err);
      alert("Failed to update job");
    }
  };

  const handleDelete = async () => {
    if (!selectedJob) return;
    try {
      await adminApi.deleteJob(selectedJob.id);
      setIsDeleteOpen(false);
      fetchJobs();
    } catch (err) {
      console.error(err);
      alert("Failed to delete job");
    }
  };

  const openEditModal = (job: any) => {
    setSelectedJob(job);
    setFormData({
      title: job.title || "",
      company_id: job.company_id || "",
      status: job.status || "draft",
      location: job.location || "",
      employment_type: job.employment_type || ""
    });
    setIsEditOpen(true);
  };

  const openDeleteModal = (job: any) => {
    setSelectedJob(job);
    setIsDeleteOpen(true);
  };

  return (
    <div className="p-8 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Jobs Management</h1>
          <p className="text-muted-foreground">View and moderate job postings across the platform.</p>
        </div>

        <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
          <DialogTrigger asChild>
            <Button className="gap-2">
              <Plus className="h-4 w-4" /> Create Job
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create New Job</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleCreate} className="space-y-4 pt-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Job Title</label>
                <input required type="text" value={formData.title} onChange={e => setFormData({...formData, title: e.target.value})} className="flex h-10 w-full rounded-md border border-border-soft bg-transparent px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-brand-blue" />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Company ID</label>
                <input required type="text" value={formData.company_id} onChange={e => setFormData({...formData, company_id: e.target.value})} className="flex h-10 w-full rounded-md border border-border-soft bg-transparent px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-brand-blue" placeholder="UUID" />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Location</label>
                <input type="text" value={formData.location} onChange={e => setFormData({...formData, location: e.target.value})} className="flex h-10 w-full rounded-md border border-border-soft bg-transparent px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-brand-blue" />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Employment Type</label>
                <select value={formData.employment_type} onChange={e => setFormData({...formData, employment_type: e.target.value})} className="flex h-10 w-full rounded-md border border-border-soft bg-transparent px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-brand-blue">
                  <option value="">Select Type...</option>
                  <option value="full_time">Full Time</option>
                  <option value="part_time">Part Time</option>
                  <option value="contract">Contract</option>
                  <option value="internship">Internship</option>
                </select>
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Status</label>
                <select value={formData.status} onChange={e => setFormData({...formData, status: e.target.value})} className="flex h-10 w-full rounded-md border border-border-soft bg-transparent px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-brand-blue">
                  <option value="live">Live</option>
                  <option value="draft">Draft</option>
                  <option value="closed">Closed</option>
                </select>
              </div>
              <div className="flex justify-end gap-2 pt-4">
                <Button type="button" variant="secondary" onClick={() => setIsCreateOpen(false)}>Cancel</Button>
                <Button type="submit">Create</Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
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
                <th className="h-12 px-4 align-middle font-medium text-muted-foreground">Status</th>
                <th className="h-12 px-4 align-middle font-medium text-muted-foreground text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={5} className="text-center py-8 text-muted-foreground animate-pulse">
                    Loading jobs...
                  </td>
                </tr>
              ) : jobs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="text-center py-8 text-muted-foreground">
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
                      <Badge variant={job.status === 'live' ? 'default' : 'secondary'} className="capitalize">
                        {job.status}
                      </Badge>
                    </td>
                    <td className="p-4 align-middle text-right">
                      <div className="flex justify-end gap-2">
                        <Button variant="secondary" size="icon" onClick={() => openEditModal(job)} className="h-8 w-8">
                          <Edit2 className="h-4 w-4" />
                        </Button>
                        <Button variant="destructive" size="icon" onClick={() => openDeleteModal(job)} className="h-8 w-8">
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Edit Modal */}
      <Dialog open={isEditOpen} onOpenChange={setIsEditOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Job</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleEdit} className="space-y-4 pt-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Job Title</label>
              <input required type="text" value={formData.title} onChange={e => setFormData({...formData, title: e.target.value})} className="flex h-10 w-full rounded-md border border-border-soft bg-transparent px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-brand-blue" />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Location</label>
              <input type="text" value={formData.location} onChange={e => setFormData({...formData, location: e.target.value})} className="flex h-10 w-full rounded-md border border-border-soft bg-transparent px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-brand-blue" />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Employment Type</label>
              <select value={formData.employment_type} onChange={e => setFormData({...formData, employment_type: e.target.value})} className="flex h-10 w-full rounded-md border border-border-soft bg-transparent px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-brand-blue">
                <option value="">Select Type...</option>
                <option value="full_time">Full Time</option>
                <option value="part_time">Part Time</option>
                <option value="contract">Contract</option>
                <option value="internship">Internship</option>
              </select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Status</label>
              <select value={formData.status} onChange={e => setFormData({...formData, status: e.target.value})} className="flex h-10 w-full rounded-md border border-border-soft bg-transparent px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-brand-blue">
                <option value="live">Live</option>
                <option value="draft">Draft</option>
                <option value="closed">Closed</option>
              </select>
            </div>
            <div className="flex justify-end gap-2 pt-4">
              <Button type="button" variant="secondary" onClick={() => setIsEditOpen(false)}>Cancel</Button>
              <Button type="submit">Save Changes</Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Modal */}
      <Dialog open={isDeleteOpen} onOpenChange={setIsDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Job</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <p className="text-sm text-muted-foreground">Are you sure you want to delete the job <strong>{selectedJob?.title}</strong>? This action cannot be undone.</p>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setIsDeleteOpen(false)}>Cancel</Button>
            <Button variant="destructive" onClick={handleDelete}>Delete</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
