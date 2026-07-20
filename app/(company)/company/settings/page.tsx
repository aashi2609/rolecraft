"use client";

import React from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { FormField, Input } from '@/components/ui/FormField';

export default function CompanySettingsPage() {
  return (
    <div className="min-h-screen bg-slate-50 py-10">
      <div className="max-w-4xl mx-auto px-4">
        
        <h1 className="text-3xl font-bold text-slate-900 mb-8">Company Settings</h1>

        <div className="space-y-8">
          <Card className="p-6">
            <h2 className="text-xl font-bold text-slate-900 mb-6 border-b pb-2">Admin Account</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <FormField label="Full Name"><Input defaultValue="Company Admin" /></FormField>
              <FormField label="Email Address"><Input defaultValue="admin@company.com" disabled /></FormField>
            </div>
            <div className="mt-4"><Button>Save Changes</Button></div>
          </Card>

          <Card className="p-6">
            <h2 className="text-xl font-bold text-slate-900 mb-6 border-b pb-2">Change Password</h2>
            <div className="space-y-4 max-w-md">
              <FormField label="Current Password"><Input type="password" /></FormField>
              <FormField label="New Password"><Input type="password" /></FormField>
              <FormField label="Confirm New Password"><Input type="password" /></FormField>
              <Button>Update Password</Button>
            </div>
          </Card>

          <Card className="p-6">
            <h2 className="text-xl font-bold text-slate-900 mb-6 border-b pb-2">Billing & Plan</h2>
            <div className="flex justify-between items-center bg-slate-50 p-4 rounded-lg border border-slate-200">
              <div>
                <div className="font-bold text-slate-900">Current Plan: Free</div>
                <div className="text-sm text-slate-500">2 active jobs limit</div>
              </div>
              <Button variant="outline">Upgrade Plan</Button>
            </div>
          </Card>

          <Card className="p-6 border-red-200">
            <h2 className="text-xl font-bold text-red-600 mb-2">Danger Zone</h2>
            <p className="text-slate-600 mb-4 text-sm">Deleting your company account will permanently remove all job postings and candidate data.</p>
            <Button variant="outline" className="text-red-600 border-red-200 hover:bg-red-50 hover:text-red-700">Delete Account</Button>
          </Card>
        </div>

      </div>
    </div>
  );
}
