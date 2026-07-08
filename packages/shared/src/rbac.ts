import { ROLES, type Role } from '@dcip/types';
import { PERMISSIONS, type Permission } from '@dcip/types';

/**
 * The single source of truth for which permissions each role holds.
 * The backend mirrors this exact matrix; the frontend imports it to gate UI.
 * Higher roles are NOT auto-granted lower-role permissions implicitly — the
 * matrix is explicit so it can be audited line by line.
 */
export const ROLE_PERMISSIONS: Record<Role, ReadonlyArray<Permission>> = {
  [ROLES.ADMINISTRATOR]: Object.values(PERMISSIONS),
  [ROLES.SENIOR_INVESTIGATOR]: [
    PERMISSIONS.CASE_READ,
    PERMISSIONS.CASE_CREATE,
    PERMISSIONS.CASE_UPDATE,
    PERMISSIONS.CASE_DELETE,
    PERMISSIONS.CASE_ASSIGN,
    PERMISSIONS.EVIDENCE_READ,
    PERMISSIONS.EVIDENCE_UPLOAD,
    PERMISSIONS.EVIDENCE_DELETE,
    PERMISSIONS.TIMELINE_READ,
    PERMISSIONS.TIMELINE_WRITE,
    PERMISSIONS.TIMELINE_MANAGE,
    PERMISSIONS.REPORT_READ,
    PERMISSIONS.REPORT_CREATE,
    PERMISSIONS.REPORT_PUBLISH,
    PERMISSIONS.AI_RUN,
    PERMISSIONS.AI_REVIEW,
    PERMISSIONS.AUDIT_READ,
  ],
  [ROLES.INVESTIGATOR]: [
    PERMISSIONS.CASE_READ,
    PERMISSIONS.CASE_CREATE,
    PERMISSIONS.CASE_UPDATE,
    PERMISSIONS.EVIDENCE_READ,
    PERMISSIONS.EVIDENCE_UPLOAD,
    PERMISSIONS.TIMELINE_READ,
    PERMISSIONS.TIMELINE_WRITE,
    PERMISSIONS.REPORT_READ,
    PERMISSIONS.REPORT_CREATE,
    PERMISSIONS.AI_RUN,
    PERMISSIONS.AI_REVIEW,
  ],
  [ROLES.ANALYST]: [
    PERMISSIONS.CASE_READ,
    PERMISSIONS.EVIDENCE_READ,
    PERMISSIONS.EVIDENCE_UPLOAD,
    PERMISSIONS.TIMELINE_READ,
    PERMISSIONS.TIMELINE_WRITE,
    PERMISSIONS.REPORT_READ,
    PERMISSIONS.AI_RUN,
    PERMISSIONS.AI_REVIEW,
  ],
  [ROLES.READ_ONLY]: [
    PERMISSIONS.CASE_READ,
    PERMISSIONS.EVIDENCE_READ,
    PERMISSIONS.TIMELINE_READ,
    PERMISSIONS.REPORT_READ,
  ],
};

/** Returns true if the given role holds the given permission. */
export function roleHasPermission(role: Role, permission: Permission): boolean {
  return ROLE_PERMISSIONS[role]?.includes(permission) ?? false;
}

/** Returns true if any of the supplied roles holds the permission. */
export function hasPermission(roles: readonly Role[], permission: Permission): boolean {
  return roles.some((role) => roleHasPermission(role, permission));
}
