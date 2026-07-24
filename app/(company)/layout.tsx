import { ProtectedRoute } from "@/components/ProtectedRoute";
import { AppShell } from "@/components/layout/AppShell";

export default function CompanyLayout({ children }: { children: React.ReactNode }) {
  return (
    <ProtectedRoute allowedRoles={['company']}>
      <AppShell role="company">{children}</AppShell>
    </ProtectedRoute>
  );
}
