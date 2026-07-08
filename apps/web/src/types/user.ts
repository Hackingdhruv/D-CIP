import type { RoleReadSlim } from './role';

export interface UserRead {
  id: string;
  email: string;
  username: string;
  fullName: string;
  isActive: boolean;
  isLocked: boolean;
  avatarUrl: string | null;
  lastLoginAt: string | null;
  createdAt: string;
  updatedAt: string;
  roles: RoleReadSlim[];
  permissions: string[];
}

export interface UserReadSlim {
  id: string;
  email: string;
  username: string;
  fullName: string;
  isActive: boolean;
  isLocked: boolean;
  avatarUrl: string | null;
  lastLoginAt: string | null;
  createdAt: string;
  roles: RoleReadSlim[];
}

export interface UserListResponse {
  items: UserReadSlim[];
  total: number;
  page: number;
  pageSize: number;
  pages: number;
}

export interface UserCreate {
  email: string;
  username: string;
  fullName: string;
  password: string;
  roleIds?: string[];
}

export interface UserUpdate {
  email?: string;
  username?: string;
  fullName?: string;
  avatarUrl?: string;
}

export interface ProfileUpdate {
  fullName?: string;
  avatarUrl?: string;
}
