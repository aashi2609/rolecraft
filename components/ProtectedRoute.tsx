"use client";

import { useUser } from '@/context/UserContext';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

export function ProtectedRoute({ children, allowedRoles }: { children: React.ReactNode, allowedRoles?: ('candidate' | 'company')[] }) {
  const { isAuthenticated, role, loading } = useUser();
  const router = useRouter();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted || loading) return;
    if (!isAuthenticated) {
      router.push('/signin');
    } else if (allowedRoles && role && !allowedRoles.includes(role)) {
      router.push('/');
    }
  }, [isAuthenticated, role, allowedRoles, router, mounted, loading]);

  if (!mounted || loading) {
    return <div className="min-h-screen flex items-center justify-center">
      <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin"></div>
    </div>; // Simple loading spinner
  }

  if (!isAuthenticated) {
    return null;
  }

  if (allowedRoles && role && !allowedRoles.includes(role)) {
    return null; 
  }

  return <>{children}</>;
}
