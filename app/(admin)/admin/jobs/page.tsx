"use client";

import { useEffect, useState } from "react";
import { adminApi } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Search, Plus, Edit2, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { FormField, Input, Textarea } from "@/components/ui/FormField";
import { SearchableCombobox } from "@/components/ui/SearchableCombobox";
import { DEPARTMENTS, EMPLOYMENT_TYPES, JOB_TYPES, SKILLS } from "@/lib/constants";
import { CheckCircle, XCircle } from "lucide-react";

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
    department: "",
    role: "",
    level: "",
    employment_type: "",
    experience: "",
    min_salary: "",
    max_salary: "",
    salary_unit: "Per annum",
    country: "",
    state: "",
    city: "",
    location: "",
    job_type: "On-site",
    skills: [] as string[],
    num_openings: 1,
    application_deadline: "",
    description: "",
    responsibilities: "",
    requirements: "",
    benefits: "",
    status: "draft"
  });

  const [companyName, setCompanyName] = useState<string | null>(null);
  const [companyError, setCompanyError] = useState<string | null>(null);

  useEffect(() => {
    if (!formData.company_id || formData.company_id.length !== 36) {
      setCompanyName(null);
      setCompanyError(null);
      return;
    }
    const timer = setTimeout(() => {
      adminApi.getUsers({ role: 'company' }).then((users: any) => {
         // handle array response or object with data
         const userList = Array.isArray(users) ? users : (users.data || []);
         const comp = userList.find((u: any) => u.id === formData.company_id);
         if (comp) {
           setCompanyName(comp.name || comp.email);
           setCompanyError(null);
         } else {
           setCompanyName(null);
           setCompanyError("Company not found");
         }
      }).catch(() => {
         setCompanyError("Error looking up company");
      });
    }, 500);
    return () => clearTimeout(timer);
  }, [formData.company_id]);

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
      await adminApi.createJob({
        title: formData.title,
        company_id: formData.company_id,
        department: formData.department,
        job_role: formData.role,
        job_level: formData.level,
        employment_type: formData.employment_type,
        experience_range: formData.experience,
        min_salary: formData.min_salary ? Number(formData.min_salary) : undefined,
        max_salary: formData.max_salary ? Number(formData.max_salary) : undefined,
        salary_unit: formData.salary_unit,
        location: formData.city ? `${formData.city}, ${formData.state}, ${formData.country}` : undefined,
        country: formData.country,
        state: formData.state,
        city: formData.city,
        job_type: formData.job_type?.toLowerCase(),
        required_skills: formData.skills,
        num_openings: Number(formData.num_openings) || 1,
        application_deadline: formData.application_deadline || undefined,
        description: formData.description,
        responsibilities: formData.responsibilities,
        requirements: formData.requirements,
        benefits: formData.benefits,
        status: formData.status
      });
      setIsCreateOpen(false);
      fetchJobs();
      setFormData({
        title: "", company_id: "", department: "", role: "", level: "", employment_type: "", experience: "", min_salary: "", max_salary: "", salary_unit: "Per annum", country: "", state: "", city: "", location: "", job_type: "On-site", skills: [], num_openings: 1, application_deadline: "", description: "", responsibilities: "", requirements: "", benefits: "", status: "draft"
      });
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
    setFormData((prev) => ({
      ...prev,
      title: job.title || "",
      company_id: job.company_id || "",
      status: job.status || "draft",
      location: job.location || "",
      employment_type: job.employment_type || ""
    }));
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
          <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Create New Job</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleCreate} className="space-y-6 pt-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <FormField label="Job Title" required>
                  <Input placeholder="e.g. Senior UI/UX Designer" value={formData.title} onChange={e => setFormData({...formData, title: e.target.value})} />
                </FormField>

                <FormField label="Company ID" required>
                  <div className="relative">
                    <Input placeholder="Enter company UUID" value={formData.company_id} onChange={e => setFormData({...formData, company_id: e.target.value})} />
                    {companyName && <span className="absolute right-3 top-2.5 text-green-600 flex items-center text-xs font-medium"><CheckCircle className="w-3 h-3 mr-1" /> {companyName}</span>}
                    {companyError && <span className="absolute right-3 top-2.5 text-red-600 flex items-center text-xs font-medium"><XCircle className="w-3 h-3 mr-1" /> {companyError}</span>}
                  </div>
                </FormField>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <FormField label="Department">
                  <SearchableCombobox options={[...DEPARTMENTS]} value={formData.department} onChange={v => setFormData({...formData, department: v})} placeholder="Select department" />
                </FormField>

                <FormField label="Job Role" required>
                  <Input placeholder="e.g. Frontend Developer" value={formData.role} onChange={e => setFormData({...formData, role: e.target.value})} />
                </FormField>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <FormField label="Job Level" required>
                  <select className="w-full px-3 py-2 bg-white border border-border-soft rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-blue" value={formData.level} onChange={e => setFormData({...formData, level: e.target.value})}>
                    <option value="">Select level</option>
                    <option value="Internship">Internship</option>
                    <option value="Entry">Entry Level</option>
                    <option value="Mid">Mid Level</option>
                    <option value="Senior">Senior Level</option>
                    <option value="Director">Director</option>
                    <option value="Executive">Executive</option>
                  </select>
                </FormField>

                <FormField label="Employment Type" required>
                  <select className="w-full px-3 py-2 bg-white border border-border-soft rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-blue" value={formData.employment_type} onChange={e => setFormData({...formData, employment_type: e.target.value})}>
                    <option value="">Select type</option>
                    {EMPLOYMENT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </FormField>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <FormField label="Experience Required" required>
                  <Input placeholder="e.g. 3-5 Years" value={formData.experience} onChange={e => setFormData({...formData, experience: e.target.value})} />
                </FormField>
                <FormField label="Min Salary">
                  <Input type="number" placeholder="Min" value={formData.min_salary} onChange={e => setFormData({...formData, min_salary: e.target.value})} />
                </FormField>
                <FormField label="Max Salary">
                  <div className="flex gap-2">
                    <Input type="number" placeholder="Max" value={formData.max_salary} onChange={e => setFormData({...formData, max_salary: e.target.value})} className="flex-1" />
                    <select className="w-[110px] px-2 py-2 bg-white border border-border-soft rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-blue" value={formData.salary_unit} onChange={e => setFormData({...formData, salary_unit: e.target.value})}>
                      <option value="Per month">Per month</option>
                      <option value="Per annum">Per annum</option>
                    </select>
                  </div>
                </FormField>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <FormField label="Country" required>
                  <Input placeholder="e.g. India" value={formData.country} onChange={e => setFormData({...formData, country: e.target.value})} />
                </FormField>
                <FormField label="State" required>
                  <Input placeholder="e.g. Karnataka" value={formData.state} onChange={e => setFormData({...formData, state: e.target.value})} />
                </FormField>
                <FormField label="City" required>
                  <Input placeholder="e.g. Bangalore" value={formData.city} onChange={e => setFormData({...formData, city: e.target.value})} />
                </FormField>
              </div>

              <FormField label="Job Type" required>
                <div className="flex flex-wrap gap-3">
                  {JOB_TYPES.map((t) => (
                    <label key={t} className={`inline-flex items-center gap-2 px-4 py-2.5 rounded-lg border cursor-pointer transition-colors ${formData.job_type === t ? 'border-brand-blue bg-brand-blue/5 text-brand-blue' : 'border-border-soft hover:border-brand-blue/40'}`}>
                      <input type="radio" name="jobType" className="accent-brand-blue" checked={formData.job_type === t} onChange={() => setFormData({...formData, job_type: t})} />
                      <span className="text-sm font-medium">{t}</span>
                    </label>
                  ))}
                </div>
              </FormField>

              <FormField label="Required Skills" required>
                <SearchableCombobox multiSelect options={[...SKILLS]} value={formData.skills} onChange={(v: string[]) => setFormData({...formData, skills: v})} placeholder="e.g. Figma, UI Design, Prototyping" />
              </FormField>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <FormField label="Number of Openings" required>
                  <Input type="number" min={1} value={formData.num_openings} onChange={e => setFormData({...formData, num_openings: Number(e.target.value)})} />
                </FormField>
                <FormField label="Application Deadline">
                  <Input type="date" value={formData.application_deadline} onChange={e => setFormData({...formData, application_deadline: e.target.value})} />
                </FormField>
              </div>

              <FormField label="Full Description" required>
                <Textarea rows={5} placeholder="Summarize the role, team, and impact..." value={formData.description} onChange={e => setFormData({...formData, description: e.target.value})} />
              </FormField>

              <FormField label="Responsibilities">
                <Textarea rows={4} placeholder="One responsibility per line" value={formData.responsibilities} onChange={e => setFormData({...formData, responsibilities: e.target.value})} />
              </FormField>

              <FormField label="Requirements">
                <Textarea rows={4} placeholder="Must-haves and nice-to-haves" value={formData.requirements} onChange={e => setFormData({...formData, requirements: e.target.value})} />
              </FormField>

              <FormField label="Benefits">
                <Textarea rows={3} placeholder="Perks, benefits, and culture highlights" value={formData.benefits} onChange={e => setFormData({...formData, benefits: e.target.value})} />
              </FormField>

              <FormField label="Status" required>
                <select className="w-full px-3 py-2 bg-white border border-border-soft rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-blue" value={formData.status} onChange={e => setFormData({...formData, status: e.target.value})}>
                  <option value="live">Live</option>
                  <option value="draft">Draft</option>
                  <option value="closed">Closed</option>
                </select>
              </FormField>

              <div className="flex justify-end gap-2 pt-4 border-t border-border-soft">
                <Button type="button" variant="secondary" onClick={() => setIsCreateOpen(false)}>Cancel</Button>
                <Button type="submit" disabled={!!companyError || !companyName || !formData.title || !formData.description}>Create Job</Button>
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
