import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";

interface AdminRouteProps {
  children: ReactNode;
}

/**
 * AdminRoute Component
 * Wraps routes to protect them from non-admin access
 * - Checks if user is superuser
 * - Redirects to dashboard if not admin
 * - Does not show anything to non-admin users
 */
export const AdminRoute = ({ children }: AdminRouteProps) => {
  const { user, isLoading } = useAuth();

  // Show loading while checking
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  // Not admin - redirect to dashboard
  const isAdmin = user?.is_superuser || user?.role === "admin" || user?.role === "super_admin";

  if (!isAdmin) {
    return <Navigate to="/dashboard" replace />;
  }

  return <>{children}</>;
};

export default AdminRoute;
