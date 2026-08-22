"use client";

import React, { useEffect, useState } from 'react';
import { Card } from '@/components/ui/Card';
import { adminApi } from '@/lib/api';

export default function AdminDashboardPage() {
  const [stats, setStats] = useState({ users: 0, subscriptions: 0 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const users = await adminApi.getUsers(0, 1000) as any[];
        const subs = await adminApi.getSubscriptions(0, 1000) as any[];
        setStats({
          users: users.length,
          subscriptions: subs.length,
        });
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  return (
    <div className="p-6 md:p-8 max-w-5xl">
      <h1 className="text-2xl font-bold text-foreground mb-6">Dashboard Overview</h1>
      
      {loading ? (
        <div className="text-muted-foreground">Loading statistics...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Card className="p-6 flex flex-col gap-2">
            <span className="text-sm font-medium text-muted-foreground">Total Users</span>
            <span className="text-3xl font-bold text-foreground">{stats.users}</span>
          </Card>
          <Card className="p-6 flex flex-col gap-2">
            <span className="text-sm font-medium text-muted-foreground">Total Subscriptions</span>
            <span className="text-3xl font-bold text-foreground">{stats.subscriptions}</span>
          </Card>
          <Card className="p-6 flex flex-col gap-2 bg-primary/5 border-primary/20">
            <span className="text-sm font-medium text-primary">System Status</span>
            <span className="text-xl font-bold text-primary">All systems operational</span>
          </Card>
        </div>
      )}
    </div>
  );
}
