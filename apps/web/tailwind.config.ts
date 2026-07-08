import type { Config } from 'tailwindcss';
import preset from '@dcip/ui/preset';

export default {
  presets: [preset],
  content: [
    './index.html',
    './src/**/*.{ts,tsx}',
    // Pick up any classes used inside the shared UI package.
    '../../packages/ui/src/**/*.{ts,tsx}',
  ],
} satisfies Config;
