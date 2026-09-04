"use client";

import React, { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { FormField, Input } from '@/components/ui/FormField';
import { useUser } from '@/context/UserContext';
import { planDisplayName, isFreePlan, getPlanById } from '@/lib/plans';
import { authApi, companyApi } from '@/lib/api';

interface CompanyProfile {
  name?: string;
  email?: string;
}

export default function CompanySettingsPage() {
  const { plan, companyProfile, refreshSession } = useUser();
  const planDef = getPlanById(plan);

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [accountMsg, setAccountMsg] = useState('');
  const [passwordMsg, setPasswordMsg] = useState('');
  const [saving, setSaving] = useState(false);

  const updateFormData = useCallback(() => {
    const profile = companyProfile as CompanyProfile | null;
    setFullName(String(profile?.name || ''));
    setEmail(String(profile?.email || ''));
  }, [companyProfile]);

  useEffect(() => {
    updateFormData();
  }, [updateFormData]);

  const saveAccount = async () => {
    setSaving(true);
    setAccountMsg('');
    try {
      await companyApi.updateMe({ name: fullName.trim() });
      await refreshSession();
      setAccountMsg('Account details saved.');
    } catch (e: unknown) {
      setAccountMsg(e instanceof Error ? e.message : 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  const updatePassword = async () => {
    setPasswordMsg('');
    if (!currentPassword || !newPassword) {
      setPasswordMsg('Enter current and new password.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordMsg('New passwords do not match.');
      return;
    }
    try {
      await authApi.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setPasswordMsg('Password updated.');
    } catch (e: unknown) {
      setPasswordMsg(e instanceof Error ? e.message : 'Failed to update password');
    }
  };

  return (
    <div className="min-h-screen bg-surface-soft py-10">
      <div className="max-w-4xl mx-auto px-4">
        <h1 className="text-3xl font-bold text-ink mb-8">Company Settings</h1>

        <div className="space-y-8">
          <Card className="p-6">
            <h2 className="text-xl font-bold text-ink mb-6 border-b pb-2">Admin Account</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <FormField label="Company Name">
                <Input value={fullName} onChange={(e) => setFullName(e.target.value)} />
              </FormField>
              <FormField label="Email Address">
                <Input value={email} disabled />
              </FormField>
            </div>
            {accountMsg && <p className="mt-3 text-sm text-ink-muted">{accountMsg}</p>}
            <div className="mt-4">
              <Button onClick={saveAccount} disabled={saving}>
                {saving ? 'Saving…' : 'Save Changes'}
              </Button>
            </div>
          </Card>

          <Card className="p-6">
            <h2 className="text-xl font-bold text-ink mb-6 border-b pb-2">Billing & Plan</h2>
            <div className="flex justify-between items-center bg-surface-soft p-4 rounded-lg border border-border-soft mb-4">
              <div>
                <div className="font-bold text-ink">Current Plan: {planDisplayName(plan)}</div>
                <div className="text-sm text-ink-muted">
                  {planDef?.description || (isFreePlan(plan) ? '2 active jobs limit' : 'Unlimited job postings')}
                </div>
              </div>
              <Link href="/company/pricing">
                <Button variant="outline">
                  {isFreePlan(plan) ? 'Upgrade Plan' : 'Change Plan'}
                </Button>
              </Link>
            </div>
          </Card>

          <Card className="p-6">
            <h2 className="text-xl font-bold text-ink mb-6 border-b pb-2">Change Password</h2>
            <div className="space-y-4 max-w-md">
              <FormField label="Current Password">
                <Input
                  type="password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                />
              </FormField>
              <FormField label="New Password">
                <Input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                />
              </FormField>
              <FormField label="Confirm New Password">
                <Input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                />
              </FormField>
              {passwordMsg && <p className="text-sm text-ink-muted">{passwordMsg}</p>}
              <Button onClick={updatePassword}>Update Password</Button>
            </div>
          </Card>

          <Card className="p-6 border-red-200">
            <h2 className="text-xl font-bold text-red-600 mb-2">Danger Zone</h2>
            <p className="text-ink-muted mb-4 text-sm">
              Deleting your company account will permanently remove all job postings and candidate data.
            </p>
            <Button
              variant="outline"
              className="text-red-600 border-red-200 hover:bg-red-50 hover:text-red-700"
            >
              Delete Account
            </Button>
          </Card>
        </div>
      </div>
    </div>
  );
}
