import { ProtectedRoute } from "@/components/ProtectedRoute";
import { AppShell } from "@/components/layout/AppShell";

export default function CandidateLayout({ children }: { children: React.ReactNode }) {
  return (
    <ProtectedRoute allowedRoles={['candidate']}>
      <AppShell role="candidate">{children}</AppShell>
    </ProtectedRoute>
  );
}
