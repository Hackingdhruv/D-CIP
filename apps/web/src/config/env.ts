import { z } from 'zod';

/**
 * Validated, typed access to the build-time environment. Vite only exposes
 * variables prefixed with `VITE_`. Validation fails fast at module load so a
 * misconfigured build surfaces immediately rather than at request time.
 */
const schema = z.object({
  VITE_API_BASE_URL: z
    .string()
    .min(1)
    .refine((value) => value.startsWith('/') || /^https?:\/\//.test(value), {
      message: 'must be an absolute http(s) URL or a path beginning with "/"',
    })
    .default('http://localhost:8000/api'),
  VITE_APP_NAME: z.string().default('D-CIP'),
});

const parsed = schema.safeParse(import.meta.env);

if (!parsed.success) {
  // eslint-disable-next-line no-console
  console.error('Invalid frontend environment:', parsed.error.flatten().fieldErrors);
  throw new Error('Invalid frontend environment configuration.');
}

export const env = {
  apiBaseUrl: parsed.data.VITE_API_BASE_URL,
  appName: parsed.data.VITE_APP_NAME,
  isProd: import.meta.env.PROD,
  isDev: import.meta.env.DEV,
} as const;
