"use client";

import { useUser } from '@/context/UserContext';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

export function ProtectedRoute({ children, allowedRoles }: { children: React.ReactNode, allowedRoles?: ('candidate' | 'company')[] }) {
  const { isAuthenticated, role } = useUser();
  const router = useRouter();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted) return;
    if (!isAuthenticated) {
      router.push('/signin');
    } else if (allowedRoles && role && !allowedRoles.includes(role)) {
      router.push('/');
    }
  }, [isAuthenticated, role, allowedRoles, router, mounted]);

  if (!mounted || !isAuthenticated) {
    return null; // or a loading spinner
  }

  if (allowedRoles && role && !allowedRoles.includes(role)) {
    return null; 
  }

  return <>{children}</>;
}
