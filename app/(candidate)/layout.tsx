import { ProtectedRoute } from "@/components/ProtectedRoute";

export default function CandidateLayout({ children }: { children: React.ReactNode }) {
  return (
    <ProtectedRoute allowedRoles={['candidate']}>
      {children}
    </ProtectedRoute>
  );
}
