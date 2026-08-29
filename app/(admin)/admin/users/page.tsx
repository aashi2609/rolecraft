"use client";

import { useEffect, useState } from "react";
import { adminApi } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Search, Plus, Edit2, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";

export default function AdminUsersPage() {
  const [users, setUsers] = useState<any[]>([]);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState<string>("all");
  const [loading, setLoading] = useState(true);

  // Modal states
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  
  const [selectedUser, setSelectedUser] = useState<any>(null);
  
  // Form states
  const [formData, setFormData] = useState({
    email: "",
    password: "",
    role: "candidate",
    is_active: true
  });

  const fetchUsers = () => {
    setLoading(true);
    const params: any = {};
    if (search) params.search = search;
    if (roleFilter && roleFilter !== "all") params.role = roleFilter;
    
    adminApi.getUsers(params)
      .then((data: any) => setUsers(data))
      .catch(err => console.error(err))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchUsers();
  }, [roleFilter]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchUsers();
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await adminApi.createUser(formData);
      setIsCreateOpen(false);
      fetchUsers();
      setFormData({ email: "", password: "", role: "candidate", is_active: true });
    } catch (err) {
      console.error(err);
      alert("Failed to create user");
    }
  };

  const handleEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUser) return;
    try {
      await adminApi.updateUser(selectedUser.id, {
        email: formData.email,
        role: formData.role,
        is_active: formData.is_active
      });
      setIsEditOpen(false);
      fetchUsers();
    } catch (err) {
      console.error(err);
      alert("Failed to update user");
    }
  };

  const handleDelete = async () => {
    if (!selectedUser) return;
    try {
      await adminApi.deleteUser(selectedUser.id);
      setIsDeleteOpen(false);
      fetchUsers();
    } catch (err) {
      console.error(err);
      alert("Failed to delete user");
    }
  };

  const openEditModal = (user: any) => {
    setSelectedUser(user);
    setFormData({
      email: user.email,
      password: "",
      role: user.role,
      is_active: user.is_active !== false // default to true if undefined
    });
    setIsEditOpen(true);
  };

  const openDeleteModal = (user: any) => {
    setSelectedUser(user);
    setIsDeleteOpen(true);
  };

  return (
    <div className="p-8 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Users Management</h1>
          <p className="text-muted-foreground">Manage roles, subscriptions, and accounts across the platform.</p>
        </div>
        
        <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
          <DialogTrigger asChild>
            <Button className="gap-2">
              <Plus className="h-4 w-4" /> Create User
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create New User</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleCreate} className="space-y-4 pt-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Email</label>
                <input required type="email" value={formData.email} onChange={e => setFormData({...formData, email: e.target.value})} className="flex h-10 w-full rounded-md border border-border-soft bg-transparent px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-brand-blue" />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Password</label>
                <input required type="password" value={formData.password} onChange={e => setFormData({...formData, password: e.target.value})} className="flex h-10 w-full rounded-md border border-border-soft bg-transparent px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-brand-blue" />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Role</label>
                <select value={formData.role} onChange={e => setFormData({...formData, role: e.target.value})} className="flex h-10 w-full rounded-md border border-border-soft bg-transparent px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-brand-blue">
                  <option value="candidate">Candidate</option>
                  <option value="company">Company</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <div className="flex items-center gap-2 pt-2">
                <input type="checkbox" id="isActiveCreate" checked={formData.is_active} onChange={e => setFormData({...formData, is_active: e.target.checked})} className="h-4 w-4 rounded border-gray-300 text-brand-blue focus:ring-brand-blue" />
                <label htmlFor="isActiveCreate" className="text-sm font-medium">Active User</label>
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
                <th className="h-12 px-4 align-middle font-medium text-muted-foreground">Status</th>
                <th className="h-12 px-4 align-middle font-medium text-muted-foreground">Role</th>
                <th className="h-12 px-4 align-middle font-medium text-muted-foreground text-right">Actions</th>
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
                    <td className="p-4 align-middle">
                      <Badge variant={user.is_active !== false ? 'default' : 'secondary'}>
                        {user.is_active !== false ? 'Active' : 'Inactive'}
                      </Badge>
                    </td>
                    <td className="p-4 align-middle capitalize">{user.role}</td>
                    <td className="p-4 align-middle text-right">
                      <div className="flex justify-end gap-2">
                        <Button variant="secondary" size="icon" onClick={() => openEditModal(user)} className="h-8 w-8">
                          <Edit2 className="h-4 w-4" />
                        </Button>
                        <Button variant="destructive" size="icon" onClick={() => openDeleteModal(user)} className="h-8 w-8">
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
            <DialogTitle>Edit User</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleEdit} className="space-y-4 pt-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Email</label>
              <input required type="email" value={formData.email} onChange={e => setFormData({...formData, email: e.target.value})} className="flex h-10 w-full rounded-md border border-border-soft bg-transparent px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-brand-blue" />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Role</label>
              <select value={formData.role} onChange={e => setFormData({...formData, role: e.target.value})} className="flex h-10 w-full rounded-md border border-border-soft bg-transparent px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-brand-blue">
                <option value="candidate">Candidate</option>
                <option value="company">Company</option>
                <option value="admin">Admin</option>
              </select>
            </div>
            <div className="flex items-center gap-2 pt-2">
              <input type="checkbox" id="isActiveEdit" checked={formData.is_active} onChange={e => setFormData({...formData, is_active: e.target.checked})} className="h-4 w-4 rounded border-gray-300 text-brand-blue focus:ring-brand-blue" />
              <label htmlFor="isActiveEdit" className="text-sm font-medium">Active User</label>
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
            <DialogTitle>Delete User</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <p className="text-sm text-muted-foreground">Are you sure you want to delete the user <strong>{selectedUser?.email}</strong>? This action cannot be undone.</p>
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
