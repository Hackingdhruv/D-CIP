import { motion } from 'framer-motion';

// framer-motion v11 + @types/react v19 type incompatibility — cast to bypass inference
const MotionDiv = motion.div as any; // eslint-disable-line @typescript-eslint/no-explicit-any

/** Full-viewport loading state shown during initial app/route bootstrapping. */
export function LoadingScreen({ label = 'Loading workspace' }: { label?: string }) {
  return (
    <div className="flex h-dvh w-full flex-col items-center justify-center gap-5 bg-background">
      <MotionDiv
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.3 }}
        className="relative flex h-14 w-14 items-center justify-center"
      >
        <span className="absolute inset-0 animate-ping rounded-xl bg-primary/20" />
        <span className="flex h-14 w-14 items-center justify-center rounded-xl border border-primary/40 bg-primary/10 font-mono text-lg font-semibold text-primary">
          D
        </span>
      </MotionDiv>
      <p className="text-sm text-muted-foreground">{label}…</p>
    </div>
  );
}
