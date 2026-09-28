"use client";

import React, { useCallback, useEffect, useState } from 'react';
import { Bell } from 'lucide-react';
import { useUser } from '@/context/UserContext';
import { notificationsApi } from '@/lib/api';
import Link from 'next/link';

type NotificationRow = {
  id: string;
  body: string;
  is_read: boolean;
  created_at: string;
};

function formatTime(iso?: string) {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    const diff = Date.now() - d.getTime();
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return d.toLocaleDateString();
  } catch {
    return '';
  }
}

export function NotificationsDropdown() {
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState<NotificationRow[]>([]);
  const [loading, setLoading] = useState(false);
  const { role } = useUser();

  const loadNotifications = useCallback(async () => {
    setLoading(true);
    try {
      const rows = await notificationsApi.mine();
      setNotifications((rows as NotificationRow[]) || []);
    } catch {
      setNotifications([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadNotifications();
    const interval = setInterval(loadNotifications, 30000);
    return () => clearInterval(interval);
  }, [loadNotifications]);

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  const markAllRead = async () => {
    const unread = notifications.filter((n) => !n.is_read);
    await Promise.all(unread.map((n) => notificationsApi.markRead(n.id).catch(() => null)));
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
  };

  const markOneRead = async (id: string) => {
    try {
      await notificationsApi.markRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
    } catch {
      /* ignore */
    }
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="p-2 text-ink-muted hover:text-ink transition-colors relative rounded-full hover:bg-surface-soft"
        aria-label="Notifications"
      >
        <Bell className="w-5 h-5" />
        {unreadCount > 0 && (
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full border-2 border-white"></span>
        )}
      </button>

      {isOpen && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)}></div>
          <div className="absolute right-0 mt-2 w-80 bg-white rounded-xl shadow-lg border border-border-soft z-50 overflow-hidden">
            <div className="p-4 border-b border-border-soft flex justify-between items-center bg-surface-soft">
              <h3 className="font-bold text-ink">Notifications</h3>
              {unreadCount > 0 && (
                <button
                  type="button"
                  onClick={markAllRead}
                  className="text-xs text-primary hover:underline font-medium"
                >
                  Mark all as read
                </button>
              )}
            </div>
            <div className="max-h-[300px] overflow-y-auto">
              {loading ? (
                <div className="p-8 text-center text-ink-muted text-sm">Loading…</div>
              ) : notifications.length === 0 ? (
                <div className="p-8 text-center text-ink-muted text-sm">
                  No notifications yet.
                </div>
              ) : (
                notifications.map((n) => (
                  <div
                    key={n.id}
                    onClick={() => !n.is_read && markOneRead(n.id)}
                    className={`p-4 border-b border-border-soft hover:bg-surface-soft cursor-pointer transition-colors ${
                      !n.is_read ? 'bg-brand-blue/10/30' : ''
                    }`}
                  >
                    <p
                      className={`text-sm ${
                        !n.is_read ? 'font-medium text-ink' : 'text-ink-muted'
                      }`}
                    >
                      {n.body}
                    </p>
                    <p className="text-xs text-ink-muted mt-1">{formatTime(n.created_at)}</p>
                  </div>
                ))
              )}
            </div>
            <div className="p-3 border-t border-border-soft text-center bg-surface-soft">
              <Link
                href={role === 'company' ? '/company/dashboard' : '/dashboard'}
                className="text-xs text-ink-muted hover:text-primary font-medium"
                onClick={() => setIsOpen(false)}
              >
                View Dashboard
              </Link>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
