import { ProtectedRoute } from "@/components/ProtectedRoute";
import { AuthenticatedNavbar } from "@/components/ui/AuthenticatedNavbar";

export default function CandidateLayout({ children }: { children: React.ReactNode }) {
  return (
    <ProtectedRoute allowedRoles={['candidate']}>
      <div className="flex flex-col min-h-screen">
        <AuthenticatedNavbar />
        <main className="flex-1">{children}</main>
      </div>
    </ProtectedRoute>
  );
}
