"use client";

import { useEffect, useState } from "react";
import { adminApi } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/Button";
import { Search, Plus, Edit2, Trash2 } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";

export default function AdminSubscriptionsPage() {
  const [subs, setSubs] = useState<any[]>([]);
  const [statusFilter, setStatusFilter] = useState("all");
  const [loading, setLoading] = useState(true);

  // Modal states
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  
  const [selectedSub, setSelectedSub] = useState<any>(null);
  
  // Form states
  const [formData, setFormData] = useState({
    user_id: "",
    role: "candidate",
    plan_tier: "free",
    status: "active"
  });

  const fetchSubs = () => {
    setLoading(true);
    const params: any = {};
    if (statusFilter !== "all") params.status = statusFilter;

    adminApi.getSubscriptions(params)
      .then((data: any) => setSubs(data))
      .catch(err => console.error(err))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchSubs();
  }, [statusFilter]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await adminApi.createSubscription(formData);
      setIsCreateOpen(false);
      fetchSubs();
      setFormData({ user_id: "", role: "candidate", plan_tier: "free", status: "active" });
    } catch (err) {
      console.error(err);
      alert("Failed to create subscription");
    }
  };

  const handleEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedSub) return;
    try {
      await adminApi.updateSubscription(selectedSub.id, {
        plan_tier: formData.plan_tier,
        status: formData.status,
        role: formData.role
      });
      setIsEditOpen(false);
      fetchSubs();
    } catch (err) {
      console.error(err);
      alert("Failed to update subscription");
    }
  };

  const handleDelete = async () => {
    if (!selectedSub) return;
    try {
      await adminApi.deleteSubscription(selectedSub.id);
      setIsDeleteOpen(false);
      fetchSubs();
    } catch (err) {
      console.error(err);
      alert("Failed to delete subscription");
    }
  };

  const openEditModal = (sub: any) => {
    setSelectedSub(sub);
    setFormData({
      user_id: sub.user_id || "",
      role: sub.role || "candidate",
      plan_tier: sub.plan_tier || "free",
      status: sub.status || "active"
    });
    setIsEditOpen(true);
  };

  const openDeleteModal = (sub: any) => {
    setSelectedSub(sub);
    setIsDeleteOpen(true);
  };

  return (
    <div className="p-8 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Subscriptions</h1>
          <p className="text-muted-foreground">Manage active billing plans and status.</p>
        </div>
        
        <div className="flex items-center gap-4">
          <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
            <DialogTrigger asChild>
              <Button className="gap-2">
                <Plus className="h-4 w-4" /> Create Subscription
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create New Subscription</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleCreate} className="space-y-4 pt-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">User ID</label>
                  <input required type="text" value={formData.user_id} onChange={e => setFormData({...formData, user_id: e.target.value})} className="flex h-10 w-full rounded-md border border-border-soft bg-transparent px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-brand-blue" placeholder="UUID" />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Role</label>
                  <select value={formData.role} onChange={e => setFormData({...formData, role: e.target.value})} className="flex h-10 w-full rounded-md border border-border-soft bg-transparent px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-brand-blue">
                    <option value="candidate">Candidate</option>
                    <option value="company">Company</option>
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Plan Tier</label>
                  <select value={formData.plan_tier} onChange={e => setFormData({...formData, plan_tier: e.target.value})} className="flex h-10 w-full rounded-md border border-border-soft bg-transparent px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-brand-blue capitalize">
                    {formData.role === 'company' ? (
                      <>
                        <option value="corporate_annual">Corporate Annual</option>
                        <option value="corporate_lifetime">Corporate Lifetime</option>
                      </>
                    ) : (
                      <>
                        <option value="resume_builder">Resume Builder</option>
                        <option value="job_search">Job Search</option>
                        <option value="complete">Complete</option>
                      </>
                    )}
                  </select>
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Status</label>
                  <select value={formData.status} onChange={e => setFormData({...formData, status: e.target.value})} className="flex h-10 w-full rounded-md border border-border-soft bg-transparent px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-brand-blue">
                    <option value="active">Active</option>
                    <option value="cancelled">Cancelled</option>
                  </select>
                </div>
                <div className="flex justify-end gap-2 pt-4">
                  <Button type="button" variant="secondary" onClick={() => setIsCreateOpen(false)}>Cancel</Button>
                  <Button type="submit">Create</Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>

          <select 
            value={statusFilter} 
            onChange={(e) => setStatusFilter(e.target.value)}
            className="flex h-10 w-[180px] rounded-md border border-border-soft bg-transparent px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-brand-blue"
          >
            <option value="all">All Statuses</option>
            <option value="active">Active</option>
            <option value="cancelled">Cancelled</option>
          </select>
        </div>
      </div>

      <div className="border border-border-soft rounded-lg bg-surface-white overflow-hidden">
        <div className="w-full overflow-auto">
          <table className="w-full text-sm text-left">
            <thead className="border-b border-border-soft bg-surface-soft">
              <tr>
                <th className="h-12 px-4 align-middle font-medium text-muted-foreground">User</th>
                <th className="h-12 px-4 align-middle font-medium text-muted-foreground">Role</th>
                <th className="h-12 px-4 align-middle font-medium text-muted-foreground">Started At</th>
                <th className="h-12 px-4 align-middle font-medium text-muted-foreground">Status</th>
                <th className="h-12 px-4 align-middle font-medium text-muted-foreground">Plan Tier</th>
                <th className="h-12 px-4 align-middle font-medium text-muted-foreground text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={6} className="text-center py-8 text-muted-foreground animate-pulse">
                    Loading subscriptions...
                  </td>
                </tr>
              ) : subs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-8 text-muted-foreground">
                    No subscriptions found matching your criteria.
                  </td>
                </tr>
              ) : (
                subs.map((sub) => (
                  <tr key={sub.id} className="border-b border-border-soft transition-colors hover:bg-surface-soft/50 data-[state=selected]:bg-surface-soft">
                    <td className="p-4 align-middle">
                      <div className="font-medium">{sub.user_name || sub.user_email || "Unknown"}</div>
                      {sub.user_name && <div className="text-xs text-muted-foreground">{sub.user_email}</div>}
                    </td>
                    <td className="p-4 align-middle">
                      <Badge variant="outline" className="capitalize">{sub.role}</Badge>
                    </td>
                    <td className="p-4 align-middle text-sm text-muted-foreground">
                      {new Date(sub.started_at).toLocaleDateString()}
                    </td>
                    <td className="p-4 align-middle">
                      <Badge variant={sub.status === 'active' ? 'default' : 'secondary'} className="capitalize">
                        {sub.status}
                      </Badge>
                    </td>
                    <td className="p-4 align-middle">
                      <span className="capitalize">{sub.plan_tier}</span>
                    </td>
                    <td className="p-4 align-middle text-right">
                      <div className="flex justify-end gap-2">
                        <Button variant="secondary" size="icon" onClick={() => openEditModal(sub)} className="h-8 w-8">
                          <Edit2 className="h-4 w-4" />
                        </Button>
                        <Button variant="destructive" size="icon" onClick={() => openDeleteModal(sub)} className="h-8 w-8">
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
            <DialogTitle>Edit Subscription</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleEdit} className="space-y-4 pt-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Role</label>
              <select value={formData.role} onChange={e => setFormData({...formData, role: e.target.value})} className="flex h-10 w-full rounded-md border border-border-soft bg-transparent px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-brand-blue">
                <option value="candidate">Candidate</option>
                <option value="company">Company</option>
              </select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Plan Tier</label>
              <select value={formData.plan_tier} onChange={e => setFormData({...formData, plan_tier: e.target.value})} className="flex h-10 w-full rounded-md border border-border-soft bg-transparent px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-brand-blue capitalize">
                {formData.role === 'company' ? (
                  <>
                    <option value="corporate_annual">Corporate Annual</option>
                    <option value="corporate_lifetime">Corporate Lifetime</option>
                  </>
                ) : (
                  <>
                    <option value="resume_builder">Resume Builder</option>
                    <option value="job_search">Job Search</option>
                    <option value="complete">Complete</option>
                  </>
                )}
              </select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Status</label>
              <select value={formData.status} onChange={e => setFormData({...formData, status: e.target.value})} className="flex h-10 w-full rounded-md border border-border-soft bg-transparent px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-brand-blue">
                <option value="active">Active</option>
                <option value="cancelled">Cancelled</option>
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
            <DialogTitle>Delete Subscription</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <p className="text-sm text-muted-foreground">Are you sure you want to delete the subscription for <strong>{selectedSub?.user_email}</strong>? This action cannot be undone.</p>
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
