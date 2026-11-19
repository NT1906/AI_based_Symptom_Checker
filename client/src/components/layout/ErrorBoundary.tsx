/**
 * @file Application-level React error boundary for graceful crash recovery and Sentry telemetry.
 * Owner: Dimple · Task: S2-DIM-7 · Requirements: NFR-03, NFR-05, DR-01, DR-02
 * Restyle (design tokens, lucide icons, dark mode): Nisarg · S2-NIS-22 (#323)
 *
 * Implements NFR-05 (Graceful degradation) and NFR-03 (Security & Zero-PII):
 * - Traps unhandled React rendering exceptions and reports them to Sentry.
 * - Scrubs all PII before dispatching error events.
 * - Displays an accessible fallback screen with session restart and emergency cues (112).
 * - Enforces the mandatory medical disclaimer (DR-01).
 */

import { Siren, TriangleAlert } from "lucide-react";
import { Component, type ErrorInfo, type ReactNode } from "react";
import { captureException } from "../../services/sentry";

/** Props for the ErrorBoundary component. */
export interface ErrorBoundaryProps {
  /** Child component tree to protect against rendering crashes. */
  children: ReactNode;
  /** Optional custom fallback element. */
  fallback?: ReactNode;
  /** Optional callback invoked when an error is caught. */
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

/** State tracking whether an error has been caught. */
interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * Catches unhandled component render errors, logs them to Sentry, and renders an accessible fallback UI.
 */
export class ErrorBoundary extends Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  public override state: ErrorBoundaryState = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  public override componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    // Dispatch to Sentry with scrubbed component stack
    captureException(error, {
      componentStack: errorInfo.componentStack || undefined,
    });

    this.props.onError?.(error, errorInfo);
  }

  private handleRestart = () => {
    // Reset state and return to root landing page
    this.setState({ hasError: false, error: null });
    window.location.href = "/";
  };

  private handleTryAgain = () => {
    this.setState({ hasError: false, error: null });
  };

  public override render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div
          role="alert"
          aria-labelledby="error-boundary-title"
          aria-describedby="error-boundary-body"
          className="flex min-h-screen flex-col items-center justify-center bg-muted/60 px-4 py-12 text-foreground"
        >
          <div className="w-full max-w-lg overflow-hidden rounded-xl border border-border bg-card p-6 shadow-xl sm:p-8">
            <div className="text-center">
              <div
                className="mx-auto flex h-16 w-16 items-center justify-center rounded-xl bg-warning/15 text-3xl"
                aria-hidden="true"
              >
                <TriangleAlert className="size-5" aria-hidden="true" />
              </div>

              <h1
                id="error-boundary-title"
                className="mt-4 text-2xl font-extrabold tracking-tight text-foreground sm:text-3xl"
              >
                Something went wrong
              </h1>

              <p
                id="error-boundary-body"
                className="mt-2 text-sm leading-relaxed text-muted-foreground"
              >
                We encountered an unexpected error while loading this page.
                Your personal health information remains secure and uncompromised.
              </p>

              {/* Action Buttons */}
              <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:justify-center">
                <button
                  type="button"
                  onClick={this.handleRestart}
                  className="inline-flex min-h-[44px] items-center justify-center rounded-xl bg-primary px-6 py-2.5 text-xs font-bold text-primary-foreground shadow-xs transition hover:bg-primary/90 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                >
                  Start New Assessment
                </button>
                <button
                  type="button"
                  onClick={this.handleTryAgain}
                  className="inline-flex min-h-[44px] items-center justify-center rounded-xl border border-input bg-card px-5 py-2.5 text-xs font-bold text-muted-foreground shadow-xs transition hover:bg-muted/60 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-ring"
                >
                  Try Again
                </button>
              </div>

              {/* Emergency Escalation Notice (DR-02) */}
              <div className="mt-8 rounded-xl border border-danger/25 bg-danger/10 p-4 text-left">
                <div className="flex items-center gap-2">
                  <Siren className="size-4 shrink-0" aria-hidden="true" />
                  <p className="text-xs font-bold text-danger-strong">
                    Experiencing a medical emergency?
                  </p>
                </div>
                <p className="mt-1 text-xs text-danger-strong">
                  Call <strong>112 (Unified Emergency)</strong> or go to the nearest emergency department immediately.
                </p>
              </div>

              {/* Mandatory Non-Diagnostic Disclaimer (DR-01) */}
              <div className="mt-4 border-t border-border pt-4 text-center">
                <p className="text-[11px] leading-relaxed text-muted-foreground">
                  This application is an informational triage aid and does not provide a medical diagnosis. Always consult a qualified healthcare professional.
                </p>
              </div>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
