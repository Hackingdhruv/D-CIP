// Audit page in the main nav — redirects to Admin Audit Center
import { Navigate } from 'react-router-dom'

export function AuditPage() {
  return <Navigate to="/admin/audit" replace />
}
