import { Navigate, useLocation } from 'react-router-dom'
import { ReactNode } from 'react'
import { useAuthStore } from '@/store/authStore'

interface ProtectedRouteProps {
  children?: ReactNode
  allowedRoles?: string[]
  requiredPermission?: string
  requireTenant?: boolean
}

export function ProtectedRoute({
  children,
  allowedRoles,
  requiredPermission,
  requireTenant = true,
}: ProtectedRouteProps) {
  const location = useLocation()
  const { user, is_authenticated, hasRole, hasPermission } = useAuthStore()

  // 1. Authentication check
  if (!is_authenticated || !user) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  // 2. Platform Super Admin bypasses tenant and role constraints
  if (user.is_superadmin) {
    return <>{children}</>
  }

  // 3. Institutional tenant context check
  if (requireTenant && !user.current_tenant_id) {
    if (user.institutions && user.institutions.length > 0) {
      return <Navigate to="/select-institution" replace />
    }
  }

  // 4. Role check
  if (allowedRoles && allowedRoles.length > 0) {
    if (!hasRole(allowedRoles)) {
      return <Navigate to="/unauthorized" replace />
    }
  }

  // 5. Permission check
  if (requiredPermission) {
    if (!hasPermission(requiredPermission)) {
      return <Navigate to="/unauthorized" replace />
    }
  }

  return <>{children}</>
}
