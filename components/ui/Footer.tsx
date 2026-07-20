import React from 'react';
import Link from 'next/link';

export function Footer() {
  return (
    <footer className="bg-white border-t border-slate-200 mt-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex flex-col md:flex-row justify-between items-center">
          <div className="flex items-center mb-4 md:mb-0">
            <span className="text-xl font-bold text-slate-900 tracking-tight">RoleCraft</span>
            <span className="text-sm text-slate-500 ml-4">© 2026 RoleCraft Inc.</span>
          </div>
          <div className="flex gap-6">
            <Link href="/terms" className="text-sm text-slate-500 hover:text-primary">Terms of Service</Link>
            <Link href="/privacy" className="text-sm text-slate-500 hover:text-primary">Privacy Policy</Link>
            <Link href="#" className="text-sm text-slate-500 hover:text-primary">Contact</Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
