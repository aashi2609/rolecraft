"use client";

import React, { useState } from 'react';
import { Bell } from 'lucide-react';
import { useUser } from '@/context/UserContext';
import Link from 'next/link';

export function NotificationsDropdown() {
  const [isOpen, setIsOpen] = useState(false);
  const { role } = useUser();

  const mockCandidateNotifications = [
    { id: 1, text: "TechCorp Inc. viewed your application for Senior Frontend Engineer.", time: "2 hours ago", unread: true },
    { id: 2, text: "Your fitment score for Backend Developer was updated.", time: "1 day ago", unread: false }
  ];

  const mockCompanyNotifications = [
    { id: 1, text: "New 95% match found for Senior Frontend Engineer.", time: "1 hour ago", unread: true },
    { id: 2, text: "Your plan upgrade was successful.", time: "Yesterday", unread: false }
  ];

  const notifications = role === 'company' ? mockCompanyNotifications : mockCandidateNotifications;
  const unreadCount = notifications.filter(n => n.unread).length;

  return (
    <div className="relative">
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="p-2 text-ink-muted hover:text-ink transition-colors relative rounded-full hover:bg-surface-soft"
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
              <button className="text-xs text-primary hover:underline font-medium">Mark all as read</button>
            </div>
            <div className="max-h-[300px] overflow-y-auto">
              {notifications.length === 0 ? (
                <div className="p-8 text-center text-ink-muted text-sm">
                  No notifications yet.
                </div>
              ) : (
                notifications.map(n => (
                  <div key={n.id} className={`p-4 border-b border-border-soft hover:bg-surface-soft cursor-pointer transition-colors ${n.unread ? 'bg-brand-blue/10/30' : ''}`}>
                    <p className={`text-sm ${n.unread ? 'font-medium text-ink' : 'text-ink-muted'}`}>
                      {n.text}
                    </p>
                    <p className="text-xs text-ink-muted mt-1">{n.time}</p>
                  </div>
                ))
              )}
            </div>
            <div className="p-3 border-t border-border-soft text-center bg-surface-soft">
              <Link href={role === 'company' ? '/company/dashboard' : '/dashboard'} className="text-xs text-ink-muted hover:text-primary font-medium" onClick={() => setIsOpen(false)}>
                View Dashboard
              </Link>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
