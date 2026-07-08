import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';

// framer-motion v11 + @types/react v19 type incompatibility — cast to bypass inference
const MotionDiv = motion.div as any; // eslint-disable-line @typescript-eslint/no-explicit-any
import { Sidebar } from './sidebar';
import { TopNav } from './top-nav';

/**
 * The application shell: a fixed sidebar on large screens, a slide-in drawer on
 * small screens, the top navigation bar, and the routed page content. Every
 * top-level page renders inside this layout.
 */
export function AppLayout() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="flex h-dvh w-full overflow-hidden bg-background">
      {/* Persistent sidebar (large screens). */}
      <div className="hidden lg:block">
        <Sidebar />
      </div>

      {/* Mobile drawer. */}
      <AnimatePresence>
        {mobileOpen && (
          <div className="fixed inset-0 z-40 lg:hidden">
            <MotionDiv
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 bg-black/60 backdrop-blur-sm"
              onClick={() => setMobileOpen(false)}
            />
            <MotionDiv
              initial={{ x: -288 }}
              animate={{ x: 0 }}
              exit={{ x: -288 }}
              transition={{ type: 'spring', stiffness: 400, damping: 40 }}
              className="absolute inset-y-0 left-0"
            >
              <Sidebar onNavigate={() => setMobileOpen(false)} />
            </MotionDiv>
          </div>
        )}
      </AnimatePresence>

      <div className="flex min-w-0 flex-1 flex-col">
        <TopNav onOpenSidebar={() => setMobileOpen(true)} />
        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto w-full max-w-[1400px] px-4 py-6 sm:px-6 lg:px-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
