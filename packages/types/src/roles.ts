/**
 * Canonical role identifiers. These are the architectural contract for RBAC
 * and must stay in sync with the backend `Role` enum (app/core/security/rbac).
 */
export const ROLES = {
  ADMINISTRATOR: 'administrator',
  SENIOR_INVESTIGATOR: 'senior_investigator',
  INVESTIGATOR: 'investigator',
  ANALYST: 'analyst',
  READ_ONLY: 'read_only',
} as const;

export type Role = (typeof ROLES)[keyof typeof ROLES];

/** Display metadata for rendering roles in the UI. */
export interface RoleMeta {
  readonly id: Role;
  readonly label: string;
  readonly description: string;
  /** Lower numbers outrank higher numbers (0 = highest authority). */
  readonly rank: number;
}

export const ROLE_META: Record<Role, RoleMeta> = {
  [ROLES.ADMINISTRATOR]: {
    id: ROLES.ADMINISTRATOR,
    label: 'Administrator',
    description: 'Full platform control, user and system administration.',
    rank: 0,
  },
  [ROLES.SENIOR_INVESTIGATOR]: {
    id: ROLES.SENIOR_INVESTIGATOR,
    label: 'Senior Investigator',
    description: 'Leads cases, manages teams, approves reports.',
    rank: 1,
  },
  [ROLES.INVESTIGATOR]: {
    id: ROLES.INVESTIGATOR,
    label: 'Investigator',
    description: 'Works cases, manages evidence and findings.',
    rank: 2,
  },
  [ROLES.ANALYST]: {
    id: ROLES.ANALYST,
    label: 'Analyst',
    description: 'Analyzes evidence and contributes findings.',
    rank: 3,
  },
  [ROLES.READ_ONLY]: {
    id: ROLES.READ_ONLY,
    label: 'Read Only',
    description: 'Views assigned cases without making changes.',
    rank: 4,
  },
};
