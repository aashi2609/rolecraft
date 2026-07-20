import { ProtectedRoute } from "@/components/ProtectedRoute";

export default function CompanyLayout({ children }: { children: React.ReactNode }) {
  return (
    <ProtectedRoute allowedRoles={['company']}>
      {children}
    </ProtectedRoute>
  );
}
