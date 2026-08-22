"use client";

import { useEffect, useState } from "react";
import { adminApi } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Search } from "lucide-react";
import { Badge } from "@/components/ui/badge";

export default function AdminUsersPage() {
  const [users, setUsers] = useState<any[]>([]);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState<string>("all");
  const [loading, setLoading] = useState(true);

  const fetchUsers = () => {
    setLoading(true);
    const params: any = {};
    if (search) params.search = search;
    if (roleFilter && roleFilter !== "all") params.role = roleFilter;
    
    adminApi.getUsers(params)
      .then(setUsers)
      .catch(err => console.error(err))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchUsers();
  }, [roleFilter]); // Reload when role filter changes

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchUsers();
  };

  const handleRoleChange = async (userId: string, newRole: string) => {
    try {
      await adminApi.updateUser(userId, { role: newRole });
      setUsers(users.map(u => u.id === userId ? { ...u, role: newRole } : u));
    } catch (err) {
      console.error(err);
      alert("Failed to update user role");
    }
  };

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Users Management</h1>
        <p className="text-muted-foreground">Manage roles, subscriptions, and accounts across the platform.</p>
      </div>

      <div className="flex flex-col sm:flex-row gap-4">
        <form onSubmit={handleSearch} className="flex flex-1 gap-2">
          <div className="relative flex-1 max-w-sm">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <input 
              type="search" 
              placeholder="Search by email..." 
              className="flex h-10 w-full rounded-md border border-border-soft bg-transparent px-3 py-2 text-sm pl-8 outline-none focus:ring-2 focus:ring-brand-blue"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <Button type="submit" variant="secondary">Search</Button>
        </form>
        
        <select 
          value={roleFilter} 
          onChange={(e) => setRoleFilter(e.target.value)}
          className="flex h-10 w-[180px] rounded-md border border-border-soft bg-transparent px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-brand-blue"
        >
          <option value="all">All Roles</option>
          <option value="candidate">Candidate</option>
          <option value="company">Company</option>
          <option value="admin">Admin</option>
        </select>
      </div>

      <div className="border border-border-soft rounded-lg bg-surface-white overflow-hidden">
        <div className="w-full overflow-auto">
          <table className="w-full text-sm text-left">
            <thead className="border-b border-border-soft bg-surface-soft">
              <tr>
                <th className="h-12 px-4 align-middle font-medium text-muted-foreground">Email</th>
                <th className="h-12 px-4 align-middle font-medium text-muted-foreground">Name / Company</th>
                <th className="h-12 px-4 align-middle font-medium text-muted-foreground">Joined</th>
                <th className="h-12 px-4 align-middle font-medium text-muted-foreground">Subscription</th>
                <th className="h-12 px-4 align-middle font-medium text-muted-foreground w-[150px]">Role</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={5} className="text-center py-8 text-muted-foreground animate-pulse">
                    Loading users...
                  </td>
                </tr>
              ) : users.length === 0 ? (
                <tr>
                  <td colSpan={5} className="text-center py-8 text-muted-foreground">
                    No users found matching your filters.
                  </td>
                </tr>
              ) : (
                users.map((user) => (
                  <tr key={user.id} className="border-b border-border-soft transition-colors hover:bg-surface-soft/50 data-[state=selected]:bg-surface-soft">
                    <td className="p-4 align-middle font-medium">{user.email}</td>
                    <td className="p-4 align-middle">
                      {user.name ? (
                        <span className="capitalize">{user.name}</span>
                      ) : (
                        <span className="text-muted-foreground italic text-xs">Profile incomplete</span>
                      )}
                    </td>
                    <td className="p-4 align-middle text-muted-foreground text-sm">
                      {new Date(user.created_at).toLocaleDateString()}
                    </td>
                    <td className="p-4 align-middle">
                      {user.plan_tier ? (
                        <div className="flex items-center gap-2">
                          <Badge variant={user.subscription_status === 'active' ? 'default' : 'secondary'} className="capitalize">
                            {user.plan_tier}
                          </Badge>
                        </div>
                      ) : (
                        <span className="text-muted-foreground text-xs">No plan</span>
                      )}
                    </td>
                    <td className="p-4 align-middle">
                      <select 
                        value={user.role} 
                        onChange={(e) => handleRoleChange(user.id, e.target.value)}
                        className="h-8 w-full rounded-md border border-border-soft bg-transparent px-2 text-sm outline-none focus:ring-1 focus:ring-brand-blue"
                      >
                        <option value="candidate">Candidate</option>
                        <option value="company">Company</option>
                        <option value="admin">Admin</option>
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
