import { NavLink } from 'react-router-dom';
import { motion } from 'framer-motion';

// framer-motion v11 + @types/react v19 type incompatibility — cast to bypass inference
const MotionSpan = motion.span as any; // eslint-disable-line @typescript-eslint/no-explicit-any
import { cn } from '@/lib/utils';
import dcipMark from '@/assets/dcip-mark.svg';
import { NAVIGATION } from '@/config/navigation';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useAuth } from '@/contexts/auth-context';

export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const { user } = useAuth();
  const userPermissions = user?.permissions ?? [];

  return (
    <aside aria-label="Main sidebar" className="flex h-full w-64 shrink-0 flex-col border-r border-border bg-surface-2/60">
      <div className="flex h-16 items-center gap-2.5 px-5">
        <img src={dcipMark} alt="D-CIP" className="h-9 w-9" />
        <div className="leading-tight">
          <p className="text-sm font-semibold tracking-tight">D-CIP</p>
          <p className="text-2xs uppercase tracking-wider text-muted-foreground">Intelligence Platform</p>
        </div>
      </div>

      <ScrollArea className="flex-1 px-3 pb-4">
        <nav aria-label="Main navigation" className="flex flex-col gap-6 pt-2">
          {NAVIGATION.map((group) => {
            const visibleItems = group.items.filter(
              (item) => !item.requires || userPermissions.includes(item.requires),
            );
            if (visibleItems.length === 0) return null;
            return (
              <div key={group.key} className="flex flex-col gap-1">
                {group.label && (
                  <p className="px-2.5 pb-1 text-2xs font-medium uppercase tracking-wider text-muted-foreground">
                    {group.label}
                  </p>
                )}
                {visibleItems.map((item) => {
                  const Icon = item.icon;
                  return (
                    <NavLink
                      key={item.key}
                      to={item.to}
                      end={item.to === '/'}
                      onClick={onNavigate}
                      className={({ isActive }) =>
                        cn(
                          'group relative flex items-center gap-3 rounded-md px-2.5 py-2 text-sm transition-colors',
                          isActive
                            ? 'bg-surface-3 font-medium text-foreground'
                            : 'text-muted-foreground hover:bg-surface-3/60 hover:text-foreground',
                        )
                      }
                    >
                      {({ isActive }) => (
                        <>
                          {isActive && (
                            <MotionSpan
                              layoutId="sidebar-active-rail"
                              className="absolute inset-y-1.5 left-0 w-0.5 rounded-full bg-primary"
                              transition={{ type: 'spring', stiffness: 500, damping: 40 }}
                            />
                          )}
                          <Icon className="h-4 w-4 shrink-0" />
                          <span>{item.label}</span>
                        </>
                      )}
                    </NavLink>
                  );
                })}
              </div>
            );
          })}
        </nav>
      </ScrollArea>

      <div className="border-t border-border px-5 py-3">
        <p className="font-mono text-2xs text-muted-foreground">v1.0.0</p>
      </div>
    </aside>
  );
}
