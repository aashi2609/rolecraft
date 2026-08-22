"use client";

import { useEffect, useState } from "react";
import { adminApi } from "@/lib/api";
import { Badge } from "@/components/ui/badge";

export default function AdminSubscriptionsPage() {
  const [subs, setSubs] = useState<any[]>([]);
  const [statusFilter, setStatusFilter] = useState("all");
  const [loading, setLoading] = useState(true);

  const fetchSubs = () => {
    setLoading(true);
    const params: any = {};
    if (statusFilter !== "all") params.status = statusFilter;

    adminApi.getSubscriptions(params)
      .then(setSubs)
      .catch(err => console.error(err))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchSubs();
  }, [statusFilter]);

  const handleUpdate = async (subId: string, field: string, value: string) => {
    try {
      await adminApi.updateSubscription(subId, { [field]: value });
      setSubs(subs.map(s => s.id === subId ? { ...s, [field]: value } : s));
    } catch (err) {
      console.error(err);
      alert("Failed to update subscription");
    }
  };

  return (
    <div className="p-8 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Subscriptions</h1>
          <p className="text-muted-foreground">Manage active billing plans and status.</p>
        </div>
        
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
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={5} className="text-center py-8 text-muted-foreground animate-pulse">
                    Loading subscriptions...
                  </td>
                </tr>
              ) : subs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="text-center py-8 text-muted-foreground">
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
                      <select 
                        value={sub.status} 
                        onChange={(e) => handleUpdate(sub.id, "status", e.target.value)}
                        className={`h-8 w-[130px] rounded-md border border-border-soft bg-transparent px-2 text-sm outline-none focus:ring-1 focus:ring-brand-blue ${sub.status === 'active' ? 'text-green-600 font-medium' : 'text-muted-foreground'}`}
                      >
                        <option value="active">Active</option>
                        <option value="cancelled">Cancelled</option>
                      </select>
                    </td>
                    <td className="p-4 align-middle">
                      <select 
                        value={sub.plan_tier} 
                        onChange={(e) => handleUpdate(sub.id, "plan_tier", e.target.value)}
                        className="h-8 w-[140px] capitalize rounded-md border border-border-soft bg-transparent px-2 text-sm outline-none focus:ring-1 focus:ring-brand-blue"
                      >
                        {/* Company Plans */}
                        {sub.role === 'company' && [
                          <option key="starter" value="starter">Starter</option>,
                          <option key="growth" value="growth">Growth</option>,
                          <option key="scale" value="scale">Scale</option>
                        ]}
                        {/* Candidate Plans */}
                        {sub.role === 'candidate' && [
                          <option key="free" value="free">Free</option>,
                          <option key="basic" value="basic">Basic</option>,
                          <option key="premium" value="premium">Premium</option>,
                          <option key="elite" value="elite">Elite</option>
                        ]}
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
