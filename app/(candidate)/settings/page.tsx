"use client";

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { FormField, Input } from '@/components/ui/FormField';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { useUser } from '@/context/UserContext';
import { planDisplayName, isFreePlan, getPlanById } from '@/lib/plans';
import { getDisplayName } from '@/lib/profile';
import { authApi, candidateApi } from '@/lib/api';

export default function CandidateSettingsPage() {
  const { plan, candidateProfile, refreshSession } = useUser();
  const planDef = getPlanById(plan);

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [emailApplications, setEmailApplications] = useState(true);
  const [emailMessages, setEmailMessages] = useState(true);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [accountMsg, setAccountMsg] = useState('');
  const [passwordMsg, setPasswordMsg] = useState('');
  const [saving, setSaving] = useState(false);

  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [deleteConfirmation, setDeleteConfirmation] = useState('');
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteMsg, setDeleteMsg] = useState('');

  const router = useRouter();

  useEffect(() => {
    setFullName(getDisplayName(candidateProfile));
    setEmail((candidateProfile?.email as string) || '');
    const prefs = (candidateProfile?.notification_prefs as Record<string, boolean>) || {};
    setEmailApplications(prefs.email_applications !== false);
    setEmailMessages(prefs.email_messages !== false);
  }, [candidateProfile]);

  const saveAccount = async () => {
    setSaving(true);
    setAccountMsg('');
    try {
      await candidateApi.updateMe({
        full_name: fullName,
        notification_prefs: {
          email_applications: emailApplications,
          email_messages: emailMessages,
        },
      });
      await refreshSession();
      setAccountMsg('Account settings saved.');
    } catch (err: any) {
      setAccountMsg(err?.detail || err?.message || 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const updatePassword = async () => {
    setPasswordMsg('');
    if (newPassword !== confirmPassword) {
      setPasswordMsg('New passwords do not match.');
      return;
    }
    try {
      await authApi.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      setPasswordMsg('Password updated successfully.');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err: any) {
      setPasswordMsg(err?.detail || err?.message || 'Password update failed');
    }
  };

  const handleDeleteAccount = async () => {
    if (deleteConfirmation !== 'DELETE') return;
    setIsDeleting(true);
    setDeleteMsg('');
    try {
      await authApi.deleteAccount();
      // Use the logout method from UserContext if available, or just redirect and let layout handle it
      // Since logout is typically inside useUser, we need to extract it
      // Let's assume it has logout or we can just clear storage
      localStorage.removeItem('rolecraft_token');
      window.location.href = '/';
    } catch (err: any) {
      setDeleteMsg(err?.detail || err?.message || 'Failed to delete account');
      setIsDeleting(false);
    }
  };

  return (
    <div className="min-h-screen bg-surface-soft py-10">
      <div className="max-w-4xl mx-auto px-4">
        <h1 className="text-3xl font-bold text-ink mb-8">Settings</h1>

        <div className="space-y-8">
          <Card className="p-6">
            <h2 className="text-xl font-bold text-ink mb-6 border-b pb-2">Account Info</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <FormField label="Full Name">
                <Input value={fullName} onChange={(e) => setFullName(e.target.value)} />
              </FormField>
              <FormField label="Email Address">
                <Input value={email} disabled />
              </FormField>
            </div>
            <div className="mt-6 space-y-3">
              <h3 className="font-semibold text-ink text-sm">Email notifications</h3>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={emailApplications}
                  onChange={(e) => setEmailApplications(e.target.checked)}
                />
                Application status updates
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={emailMessages}
                  onChange={(e) => setEmailMessages(e.target.checked)}
                />
                New messages from employers
              </label>
            </div>
            {accountMsg && <p className="text-sm text-ink-muted mt-3">{accountMsg}</p>}
            <div className="mt-4">
              <Button onClick={saveAccount} disabled={saving}>
                {saving ? 'Saving…' : 'Save Changes'}
              </Button>
            </div>
          </Card>

          <Card className="p-6">
            <h2 className="text-xl font-bold text-ink mb-6 border-b pb-2">Subscription & Billing</h2>
            <div className="flex justify-between items-center bg-surface-soft p-4 rounded-lg border border-border-soft mb-4">
              <div>
                <div className="font-bold text-ink">Current Plan: {planDisplayName(plan)}</div>
                <div className="text-sm text-ink-muted">
                  {planDef?.description || (isFreePlan(plan) ? 'Basic features included' : 'Premium features active')}
                </div>
              </div>
              <Link href="/subscribe?role=candidate">
                <Button variant="outline">Change Plan</Button>
              </Link>
            </div>
          </Card>

          <Card className="p-6">
            <h2 className="text-xl font-bold text-ink mb-6 border-b pb-2">Change Password</h2>
            <div className="space-y-4 max-w-md">
              <FormField label="Current Password">
                <Input type="password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} />
              </FormField>
              <FormField label="New Password">
                <Input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />
              </FormField>
              <FormField label="Confirm New Password">
                <Input type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} />
              </FormField>
              {passwordMsg && <p className="text-sm text-ink-muted">{passwordMsg}</p>}
              <Button onClick={updatePassword}>Update Password</Button>
            </div>
          </Card>

          <Card className="p-6 border-red-200">
            <h2 className="text-xl font-bold text-red-600 mb-2">Danger Zone</h2>
            <p className="text-ink-muted mb-4 text-sm">Once you delete your account, there is no going back. Please be certain.</p>
            <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
              <DialogTrigger asChild>
                <Button variant="outline" className="text-red-600 border-red-200 hover:bg-red-50 hover:text-red-700">Delete Account</Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Are you absolutely sure?</DialogTitle>
                  <DialogDescription>
                    This action cannot be undone. This will permanently delete your account
                    and remove your data from our servers.
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <p className="text-sm font-medium">To confirm, please type "DELETE" below:</p>
                  <Input 
                    value={deleteConfirmation} 
                    onChange={(e) => setDeleteConfirmation(e.target.value)} 
                    placeholder="DELETE"
                  />
                  {deleteMsg && <p className="text-sm text-red-600">{deleteMsg}</p>}
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setIsDeleteDialogOpen(false)}>Cancel</Button>
                  <Button 
                    variant="default" 
                    className="bg-red-600 hover:bg-red-700 text-white"
                    onClick={handleDeleteAccount} 
                    disabled={deleteConfirmation !== 'DELETE' || isDeleting}
                  >
                    {isDeleting ? 'Deleting...' : 'Delete Account'}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </Card>
        </div>
      </div>
    </div>
  );
}
