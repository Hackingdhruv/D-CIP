import { Suspense } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import {
  Activity,
  Bot,
  HardDrive,
  KeyRound,
  LayoutDashboard,
  ListTodo,
  Lock,
  ScrollText,
  Settings2,
  ShieldAlert,
  ShieldCheck,
  Users,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAdminStats } from '@/hooks/use-admin'
import { Skeleton } from '@/components/ui/skeleton'

interface NavItem {
  to: string
  label: string
  icon: React.ReactNode
  end?: boolean
  badge?: number | null
}

function SidebarLink({ to, label, icon, end, badge }: NavItem) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        cn(
          'flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors',
          isActive
            ? 'bg-primary/10 text-primary'
            : 'text-muted-foreground hover:bg-accent hover:text-foreground'
        )
      }
    >
      <span className="size-4 shrink-0">{icon}</span>
      <span className="flex-1">{label}</span>
      {badge != null && badge > 0 && (
        <span className="rounded-full bg-destructive/10 px-1.5 py-0.5 text-xs font-semibold text-destructive">
          {badge}
        </span>
      )}
    </NavLink>
  )
}

function SidebarGroup({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-0.5">
      <p className="px-3 py-1 text-xs font-semibold uppercase tracking-widest text-muted-foreground/60">{title}</p>
      {children}
    </div>
  )
}

export function AdminLayout() {
  const { data: stats } = useAdminStats()

  return (
    <div className="flex h-full min-h-0">
      {/* Sidebar */}
      <aside className="flex w-56 shrink-0 flex-col gap-4 border-r bg-card px-3 py-4">
        <div className="px-3 pb-2">
          <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            Enterprise Admin
          </p>
        </div>

        <SidebarGroup title="Overview">
          <SidebarLink to="/admin" end icon={<LayoutDashboard />} label="Dashboard" />
        </SidebarGroup>

        <SidebarGroup title="Identity">
          <SidebarLink to="/admin/users" icon={<Users />} label="Users" />
          <SidebarLink to="/admin/sessions" icon={<Lock />} label="Sessions" />
          <SidebarLink to="/admin/roles" icon={<ShieldCheck />} label="Roles" />
          <SidebarLink to="/admin/permissions" icon={<KeyRound />} label="Permissions" />
        </SidebarGroup>

        <SidebarGroup title="Operations">
          <SidebarLink
            to="/admin/system"
            icon={<Activity />}
            label="System Health"
          />
          <SidebarLink to="/admin/queue" icon={<ListTodo />} label="Queue Monitor" />
          <SidebarLink to="/admin/storage" icon={<HardDrive />} label="Storage Center" />
        </SidebarGroup>

        <SidebarGroup title="Intelligence">
          <SidebarLink to="/admin/ai" icon={<Bot />} label="AI Administration" />
        </SidebarGroup>

        <SidebarGroup title="Compliance">
          <SidebarLink
            to="/admin/audit"
            icon={<ScrollText />}
            label="Audit Center"
          />
          <SidebarLink
            to="/admin/security"
            icon={<ShieldAlert />}
            label="Security Center"
            badge={stats?.lockedUsers ?? null}
          />
        </SidebarGroup>

        <SidebarGroup title="Platform">
          <SidebarLink to="/admin/config" icon={<Settings2 />} label="Configuration" />
        </SidebarGroup>
      </aside>

      {/* Content */}
      <main className="flex-1 overflow-auto">
        <Suspense fallback={<div className="p-8"><Skeleton className="h-8 w-64 mb-4" /><Skeleton className="h-48 w-full" /></div>}>
          <Outlet />
        </Suspense>
      </main>
    </div>
  )
}
