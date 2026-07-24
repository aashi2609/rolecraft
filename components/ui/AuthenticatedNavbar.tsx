"use client";

import React, { useState } from 'react';
import Link from 'next/link';
import { useUser } from '@/context/UserContext';
import { LogOut, Settings, Building2, User, RefreshCcw } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { NotificationsDropdown } from '@/components/ui/NotificationsDropdown';

export function AuthenticatedNavbar() {
  const { role, logout, switchRole } = useUser();
  const router = useRouter();
  const [dropdownOpen, setDropdownOpen] = useState(false);

  const handleLogout = () => {
    logout();
    router.push('/');
  };

  const handleSwitchView = () => {
    if (role === 'company') {
      switchRole('candidate');
      router.push('/dashboard');
    } else {
      switchRole('company');
      router.push('/company/dashboard');
    }
  };

  return (
    <nav className="bg-white border-b border-border-soft sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex">
            <div className="flex-shrink-0 flex items-center">
              <Link href={role === 'company' ? '/company/dashboard' : '/dashboard'} className="text-xl font-bold text-ink tracking-tight">
                RoleCraft
              </Link>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <NotificationsDropdown />
            
            <div className="ml-3 relative">
              <div>
                <button 
                  onClick={() => setDropdownOpen(!dropdownOpen)}
                  className="flex text-sm border-2 border-transparent rounded-full focus:outline-none focus:border-border-soft transition duration-150 ease-in-out" 
                  id="user-menu" 
                  aria-label="User menu" 
                  aria-haspopup="true"
                >
                  <div className="w-8 h-8 rounded-full bg-border-soft flex items-center justify-center text-ink-muted font-bold">
                    {role === 'company' ? 'C' : 'U'}
                  </div>
                </button>
              </div>
              
              {dropdownOpen && (
                <>
                  <div className="fixed inset-0 z-10" onClick={() => setDropdownOpen(false)}></div>
                  <div className="origin-top-right absolute right-0 mt-2 w-56 rounded-md shadow-lg z-20">
                    <div className="py-1 rounded-md bg-white shadow-xs border border-border-soft" role="menu" aria-orientation="vertical" aria-labelledby="user-menu">
                      <div className="px-4 py-3 border-b border-border-soft">
                        <p className="text-sm leading-5">Signed in as</p>
                        <p className="text-sm leading-5 font-medium text-ink truncate">
                          user@example.com
                        </p>
                      </div>
                      
                      {role === 'company' ? (
                        <Link href="/onboarding/company-profile" className="flex items-center px-4 py-2 text-sm text-ink hover:bg-surface-soft hover:text-ink" role="menuitem">
                          <Building2 className="mr-3 h-4 w-4 text-ink-muted" /> Company Profile
                        </Link>
                      ) : (
                        <Link href="/profile/personal-details" className="flex items-center px-4 py-2 text-sm text-ink hover:bg-surface-soft hover:text-ink" role="menuitem">
                          <User className="mr-3 h-4 w-4 text-ink-muted" /> My Profile
                        </Link>
                      )}
                      
                      <Link href="#" className="flex items-center px-4 py-2 text-sm text-ink hover:bg-surface-soft hover:text-ink" role="menuitem">
                        <Settings className="mr-3 h-4 w-4 text-ink-muted" /> Settings
                      </Link>

                      <div className="border-t border-border-soft my-1"></div>

                      <button onClick={handleSwitchView} className="w-full flex items-center px-4 py-2 text-sm text-ink hover:bg-surface-soft hover:text-ink text-left" role="menuitem">
                        <RefreshCcw className="mr-3 h-4 w-4 text-ink-muted" /> 
                        Switch to {role === 'company' ? 'Job Seeker' : 'Hiring'} view
                      </button>

                      <div className="border-t border-border-soft my-1"></div>

                      <button onClick={handleLogout} className="w-full flex items-center px-4 py-2 text-sm text-red-600 hover:bg-red-50 hover:text-red-700 text-left" role="menuitem">
                        <LogOut className="mr-3 h-4 w-4 text-red-400" /> Sign out
                      </button>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
}
