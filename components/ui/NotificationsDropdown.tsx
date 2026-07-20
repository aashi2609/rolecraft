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
        className="p-2 text-slate-500 hover:text-slate-900 transition-colors relative rounded-full hover:bg-slate-100"
      >
        <Bell className="w-5 h-5" />
        {unreadCount > 0 && (
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full border-2 border-white"></span>
        )}
      </button>

      {isOpen && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)}></div>
          <div className="absolute right-0 mt-2 w-80 bg-white rounded-xl shadow-lg border border-slate-200 z-50 overflow-hidden">
            <div className="p-4 border-b border-slate-100 flex justify-between items-center bg-slate-50">
              <h3 className="font-bold text-slate-900">Notifications</h3>
              <button className="text-xs text-primary hover:underline font-medium">Mark all as read</button>
            </div>
            <div className="max-h-[300px] overflow-y-auto">
              {notifications.length === 0 ? (
                <div className="p-8 text-center text-slate-500 text-sm">
                  No notifications yet.
                </div>
              ) : (
                notifications.map(n => (
                  <div key={n.id} className={`p-4 border-b border-slate-100 hover:bg-slate-50 cursor-pointer transition-colors ${n.unread ? 'bg-blue-50/30' : ''}`}>
                    <p className={`text-sm ${n.unread ? 'font-medium text-slate-900' : 'text-slate-600'}`}>
                      {n.text}
                    </p>
                    <p className="text-xs text-slate-400 mt-1">{n.time}</p>
                  </div>
                ))
              )}
            </div>
            <div className="p-3 border-t border-slate-100 text-center bg-slate-50">
              <Link href={role === 'company' ? '/company/dashboard' : '/dashboard'} className="text-xs text-slate-500 hover:text-primary font-medium" onClick={() => setIsOpen(false)}>
                View Dashboard
              </Link>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
