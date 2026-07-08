export interface PermissionRead {
  id: string;
  resource: string;
  action: string;
  description: string | null;
  codename: string;
  createdAt: string;
}
