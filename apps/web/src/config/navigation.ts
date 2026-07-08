import {
  LayoutDashboard,
  FolderKanban,
  FileBox,
  Clock,
  Share2,
  FileText,
  Search,
  Bell,
  BellRing,
  ListChecks,
  ShieldCheck,
  Settings,
  ScrollText,
  Users,
  KeyRound,
  type LucideIcon,
} from 'lucide-react';
import { PERMISSIONS, type Permission } from '@dcip/types';

export interface NavItem {
  key: string;
  label: string;
  to: string;
  icon: LucideIcon;
  requires?: Permission;
}

export interface NavGroup {
  key: string;
  label?: string;
  items: NavItem[];
}

export const NAVIGATION: NavGroup[] = [
  {
    key: 'workspace',
    items: [
      { key: 'dashboard', label: 'Dashboard', to: '/', icon: LayoutDashboard },
      { key: 'cases', label: 'Cases', to: '/cases', icon: FolderKanban, requires: PERMISSIONS.CASE_READ },
      { key: 'evidence', label: 'Evidence', to: '/evidence', icon: FileBox, requires: PERMISSIONS.EVIDENCE_READ },
      { key: 'timeline', label: 'Timeline', to: '/timeline', icon: Clock },
      { key: 'graph', label: 'Relationships', to: '/graph', icon: Share2 },
      { key: 'reports', label: 'Reports', to: '/reports', icon: FileText, requires: PERMISSIONS.REPORT_READ },
      { key: 'search', label: 'Search', to: '/search', icon: Search },
      { key: 'watchlists', label: 'Watchlists', to: '/watchlists', icon: ListChecks, requires: PERMISSIONS.WATCHLIST_READ },
      { key: 'alerts', label: 'Alert Center', to: '/alerts', icon: BellRing, requires: PERMISSIONS.ALERT_READ },
    ],
  },
  {
    key: 'oversight',
    label: 'Oversight',
    items: [
      { key: 'notifications', label: 'Notifications', to: '/notifications', icon: Bell },
      { key: 'audit', label: 'Audit', to: '/audit', icon: ScrollText, requires: PERMISSIONS.AUDIT_READ },
      { key: 'settings', label: 'Settings', to: '/settings', icon: Settings },
    ],
  },
  {
    key: 'admin',
    label: 'Administration',
    items: [
      { key: 'admin-users', label: 'Users', to: '/admin/users', icon: Users, requires: PERMISSIONS.USER_MANAGE },
      { key: 'admin-roles', label: 'Roles', to: '/admin/roles', icon: ShieldCheck, requires: PERMISSIONS.USER_MANAGE },
      { key: 'admin-permissions', label: 'Permissions', to: '/admin/permissions', icon: KeyRound, requires: PERMISSIONS.USER_MANAGE },
    ],
  },
];
