import { describe, expect, it } from 'vitest';
import { ROLES, PERMISSIONS } from '@dcip/types';
import { hasPermission, roleHasPermission } from './rbac';

describe('rbac matrix', () => {
  it('grants administrators every permission', () => {
    for (const perm of Object.values(PERMISSIONS)) {
      expect(roleHasPermission(ROLES.ADMINISTRATOR, perm)).toBe(true);
    }
  });

  it('does not let read-only users delete cases', () => {
    expect(roleHasPermission(ROLES.READ_ONLY, PERMISSIONS.CASE_DELETE)).toBe(false);
  });

  it('aggregates permissions across multiple roles', () => {
    expect(hasPermission([ROLES.READ_ONLY, ROLES.INVESTIGATOR], PERMISSIONS.CASE_CREATE)).toBe(true);
  });
});
