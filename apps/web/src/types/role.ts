import type { PermissionRead } from './permission';

export interface RoleRead {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  isSystem: boolean;
  permissions: PermissionRead[];
  createdAt: string;
  updatedAt: string;
}

export interface RoleReadSlim {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  isSystem: boolean;
}

export interface RoleCreate {
  name: string;
  description?: string;
  permissionIds?: string[];
}

export interface RoleUpdate {
  name?: string;
  description?: string;
}

export interface AssignPermissionsRequest {
  permissionIds: string[];
}

export interface AssignRolesRequest {
  roleIds: string[];
}
