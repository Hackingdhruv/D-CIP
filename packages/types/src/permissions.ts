/**
 * Permissions are expressed as `resource:action` strings. This is the single
 * vocabulary shared by backend enforcement and frontend UI gating.
 */
export const PERMISSIONS = {
  CASE_READ: 'case:read',
  CASE_CREATE: 'case:create',
  CASE_UPDATE: 'case:update',
  CASE_DELETE: 'case:delete',
  CASE_ASSIGN: 'case:assign',
  EVIDENCE_READ: 'evidence:read',
  EVIDENCE_UPLOAD: 'evidence:upload',
  EVIDENCE_DELETE: 'evidence:delete',
  TIMELINE_READ: 'timeline:read',
  TIMELINE_WRITE: 'timeline:write',
  TIMELINE_MANAGE: 'timeline:manage',
  REPORT_READ: 'report:read',
  REPORT_CREATE: 'report:create',
  REPORT_PUBLISH: 'report:publish',
  AI_RUN: 'ai:run',
  AI_REVIEW: 'ai:review',
  WATCHLIST_READ: 'watchlist:read',
  WATCHLIST_WRITE: 'watchlist:write',
  ALERT_READ: 'alert:read',
  ALERT_WRITE: 'alert:write',
  USER_MANAGE: 'user:manage',
  AUDIT_READ: 'audit:read',
  SETTINGS_MANAGE: 'settings:manage',
} as const;

export type Permission = (typeof PERMISSIONS)[keyof typeof PERMISSIONS];
