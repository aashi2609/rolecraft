"use client";

import React, { useState, useEffect } from 'react';
import { Command } from 'cmdk';
import { Search, Settings, FileText, Briefcase, User, MessageSquare } from 'lucide-react';

export function CommandPalette() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((open) => !open);
      }
    };
    document.addEventListener('keydown', down);
    return () => document.removeEventListener('keydown', down);
  }, []);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-start justify-center pt-[15vh]">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg overflow-hidden border border-gray-200">
        <Command label="Global Command Menu" shouldFilter={true} className="flex flex-col h-full w-full">
          <div className="flex items-center px-4 border-b border-gray-100">
            <Search className="w-5 h-5 text-gray-400 mr-2" />
            <Command.Input 
              autoFocus 
              placeholder="Search actions, candidates, or jobs..." 
              className="w-full bg-transparent py-4 outline-none text-base text-gray-900 placeholder:text-gray-400"
            />
            <button 
              onClick={() => setOpen(false)}
              className="text-xs bg-gray-100 text-gray-500 px-2 py-1 rounded hover:bg-gray-200"
            >
              ESC
            </button>
          </div>

          <Command.List className="max-h-[300px] overflow-y-auto p-2">
            <Command.Empty className="py-6 text-center text-sm text-gray-500">No results found.</Command.Empty>

            <Command.Group heading="Candidate Actions" className="px-2 text-xs font-semibold text-gray-500 mb-2 mt-2">
              <Command.Item className="flex items-center px-3 py-2.5 text-sm rounded-md cursor-pointer hover:bg-blue-50 hover:text-blue-700 aria-selected:bg-blue-50 aria-selected:text-blue-700 data-[selected=true]:bg-blue-50 data-[selected=true]:text-blue-700">
                <Briefcase className="w-4 h-4 mr-2" /> Jump to Saved Jobs
              </Command.Item>
              <Command.Item className="flex items-center px-3 py-2.5 text-sm rounded-md cursor-pointer hover:bg-blue-50 hover:text-blue-700 aria-selected:bg-blue-50 aria-selected:text-blue-700 data-[selected=true]:bg-blue-50 data-[selected=true]:text-blue-700">
                <FileText className="w-4 h-4 mr-2" /> View Resume Versions
              </Command.Item>
              <Command.Item className="flex items-center px-3 py-2.5 text-sm rounded-md cursor-pointer hover:bg-blue-50 hover:text-blue-700 aria-selected:bg-blue-50 aria-selected:text-blue-700 data-[selected=true]:bg-blue-50 data-[selected=true]:text-blue-700">
                <MessageSquare className="w-4 h-4 mr-2" /> Open Messages
              </Command.Item>
            </Command.Group>

            <Command.Group heading="Company Actions" className="px-2 text-xs font-semibold text-gray-500 mb-2 mt-4">
              <Command.Item className="flex items-center px-3 py-2.5 text-sm rounded-md cursor-pointer hover:bg-blue-50 hover:text-blue-700 aria-selected:bg-blue-50 aria-selected:text-blue-700 data-[selected=true]:bg-blue-50 data-[selected=true]:text-blue-700">
                <User className="w-4 h-4 mr-2" /> Search Candidates
              </Command.Item>
              <Command.Item className="flex items-center px-3 py-2.5 text-sm rounded-md cursor-pointer hover:bg-blue-50 hover:text-blue-700 aria-selected:bg-blue-50 aria-selected:text-blue-700 data-[selected=true]:bg-blue-50 data-[selected=true]:text-blue-700">
                <Briefcase className="w-4 h-4 mr-2" /> View Job Postings
              </Command.Item>
              <Command.Item className="flex items-center px-3 py-2.5 text-sm rounded-md cursor-pointer hover:bg-blue-50 hover:text-blue-700 aria-selected:bg-blue-50 aria-selected:text-blue-700 data-[selected=true]:bg-blue-50 data-[selected=true]:text-blue-700">
                <Settings className="w-4 h-4 mr-2" /> Company Settings
              </Command.Item>
            </Command.Group>
          </Command.List>
        </Command>
      </div>
    </div>
  );
}
