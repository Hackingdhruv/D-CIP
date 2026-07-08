import * as React from 'react';
import { CommandPaletteProvider } from './command-palette-provider';

/**
 * Router-scoped providers that require useNavigate or other React Router hooks.
 * Non-router providers (Auth, Query, Theme, etc.) are lifted above RouterProvider
 * in App.tsx so that ALL routes — public and protected — share the same context.
 */
export function AppProviders({ children }: { children: React.ReactNode }) {
  return (
    <CommandPaletteProvider>
      {children}
    </CommandPaletteProvider>
  );
}
