import { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface ErrorBoundaryProps {
  children: ReactNode;
  /** Optional custom fallback renderer. */
  fallback?: (error: Error, reset: () => void) => ReactNode;
  /** When true, renders a compact inline fallback instead of a full-page takeover. */
  inline?: boolean;
}

interface ErrorBoundaryState {
  error: Error | null;
}

/**
 * Catches render-time errors anywhere in the subtree and shows a recoverable
 * fallback instead of a blank screen. Errors are surfaced to the console so
 * they reach the browser's error reporting in development and production.
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  override state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  override componentDidCatch(error: Error, info: ErrorInfo): void {
    // eslint-disable-next-line no-console
    console.error('Unhandled UI error:', error, info.componentStack);
  }

  reset = (): void => this.setState({ error: null });

  override render(): ReactNode {
    const { error } = this.state;
    const { children, fallback, inline } = this.props;

    if (error) {
      if (fallback) return fallback(error, this.reset);

      if (inline) {
        return (
          <div className="flex h-full flex-col items-center justify-center gap-4 p-12 text-center">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-destructive/40 bg-destructive/10 text-destructive">
              <AlertTriangle className="h-5 w-5" />
            </div>
            <div>
              <p className="font-semibold">This page encountered an error</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Navigate away and return, or try again below.
              </p>
            </div>
            <Button size="sm" variant="outline" onClick={this.reset}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Try again
            </Button>
          </div>
        );
      }

      return (
        <div className="flex min-h-dvh w-full items-center justify-center bg-background p-6">
          <div className="glass-panel max-w-md rounded-lg p-8 text-center">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-lg border border-destructive/40 bg-destructive/10 text-destructive">
              <AlertTriangle className="h-5 w-5" />
            </div>
            <h2 className="text-lg font-semibold">Something went wrong</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              An unexpected error interrupted this view. You can retry, or reload the application if
              the problem persists.
            </p>
            <div className="mt-6 flex justify-center gap-2">
              <Button variant="outline" onClick={() => window.location.reload()}>
                Reload
              </Button>
              <Button onClick={this.reset}>Try again</Button>
            </div>
          </div>
        </div>
      );
    }

    return children;
  }
}

/**
 * Inline error boundary for wrapping individual routes. Keeps the app shell
 * (sidebar, nav) visible so users can navigate away from the broken page.
 */
export function RouteErrorBoundary({ children }: { children: ReactNode }) {
  return <ErrorBoundary inline>{children}</ErrorBoundary>;
}
