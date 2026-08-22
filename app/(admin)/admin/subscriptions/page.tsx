"use client";

import React, { useEffect, useState } from 'react';
import { adminApi } from '@/lib/api';
import { Button } from '@/components/ui/Button';

export default function AdminSubscriptionsPage() {
  const [subs, setSubs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingSub, setEditingSub] = useState<any | null>(null);

  async function loadSubs() {
    setLoading(true);
    try {
      const data = await adminApi.getSubscriptions(0, 100);
      setSubs(data as any[]);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadSubs();
  }, []);

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingSub) return;
    try {
      await adminApi.updateSubscription(editingSub.id, editingSub.plan_tier);
      setEditingSub(null);
      await loadSubs();
    } catch (err) {
      console.error(err);
      alert('Failed to update subscription');
    }
  };

  return (
    <div className="p-6 md:p-8 max-w-7xl mx-auto relative">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-foreground">Subscriptions Management</h1>
      </div>
      
      {loading ? (
        <div className="text-muted-foreground">Loading subscriptions...</div>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border border-border overflow-hidden">
          <table className="w-full text-left text-sm">
            <thead className="bg-secondary/50 border-b border-border">
              <tr>
                <th className="px-6 py-4 font-medium text-muted-foreground">ID</th>
                <th className="px-6 py-4 font-medium text-muted-foreground">Role</th>
                <th className="px-6 py-4 font-medium text-muted-foreground">Plan Tier</th>
                <th className="px-6 py-4 font-medium text-muted-foreground">Status</th>
                <th className="px-6 py-4 font-medium text-muted-foreground">Created At</th>
                <th className="px-6 py-4 font-medium text-muted-foreground text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {subs.map(sub => (
                <tr key={sub.id} className="hover:bg-secondary/20 transition-colors">
                  <td className="px-6 py-4 text-xs font-mono text-muted-foreground">{sub.id.substring(0, 8)}...</td>
                  <td className="px-6 py-4 font-medium">{sub.role}</td>
                  <td className="px-6 py-4">
                    <span className="font-medium text-primary">{sub.plan_tier}</span>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex px-2 py-1 rounded-full text-xs font-medium ${
                      sub.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                    }`}>
                      {sub.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-muted-foreground">{new Date(sub.started_at).toLocaleDateString()}</td>
                  <td className="px-6 py-4 text-right">
                    <Button variant="outline" size="sm" onClick={() => setEditingSub(sub)}>Edit</Button>
                  </td>
                </tr>
              ))}
              {subs.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-6 py-8 text-center text-muted-foreground">No subscriptions found.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Edit Modal */}
      {editingSub && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md overflow-hidden">
            <div className="px-6 py-4 border-b border-border flex justify-between items-center">
              <h3 className="font-bold text-lg">Edit Subscription</h3>
              <button onClick={() => setEditingSub(null)} className="text-muted-foreground hover:text-foreground">&times;</button>
            </div>
            <form onSubmit={handleUpdate} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Role</label>
                <input type="text" disabled value={editingSub.role} className="w-full px-3 py-2 border rounded-lg bg-secondary/50 text-muted-foreground cursor-not-allowed" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Plan Tier</label>
                <select 
                  value={editingSub.plan_tier} 
                  onChange={e => setEditingSub({...editingSub, plan_tier: e.target.value})}
                  className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="basic">Basic</option>
                  <option value="pro">Pro</option>
                  <option value="enterprise">Enterprise</option>
                </select>
              </div>
              <div className="pt-4 flex justify-end gap-3">
                <Button type="button" variant="outline" onClick={() => setEditingSub(null)}>Cancel</Button>
                <Button type="submit">Save Changes</Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
