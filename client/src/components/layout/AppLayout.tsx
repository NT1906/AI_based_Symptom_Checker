/**
 * @file Application shell layout with accessible navigation landmarks, always-visible start over control, and a persistent medical disclaimer footer.
 *
 * Enforces requirement DR-01 (mandatory persistent medical disclaimer on every screen),
 * FR-25 (always-visible "Start new assessment" button with confirm dialog),
 * and NFR-06 (accessible landmarks, high-contrast typography, and responsive layout).
 *
 * Owner: Mann (Frontend + Deployment · Testing) · Tasks: S0-MAN-1, S1-MAN-4, S2-NIS-15 (#312), S2-NIS-19 (#320 redesign) · Requirements: DR-01, FR-25, NFR-06
 */

import React from "react";
import { Activity, Info, Phone, WifiOff } from "lucide-react";
import { ThemeToggle } from "@/components/theme/ThemeToggle";
import { AccountMenu } from "../account/AccountMenu";
import { PageTransition } from "./PageTransition";
import { RouterLink } from "./RouterLink";
import { StartNewAssessmentButton } from "./StartNewAssessmentButton";

/** Props for the AppLayout component. */
export interface AppLayoutProps {
  /** Page content rendered inside the primary semantic main landmark. */
  children: React.ReactNode;
  /** Optional custom title displayed in the header banner. Defaults to "AI-Based Symptom Checker". */
  title?: string;
  /** Optional subtitle or step descriptor displayed beneath the title. */
  subtitle?: string;
  /** Emergency phone number displayed prominently across banners and footers. Defaults to "112". */
  emergencyNumber?: string;
  /** Whether the application is currently detected as offline. */
  isOffline?: boolean;
  /** Optional action slot displayed on the right side of the navigation header. */
  headerActions?: React.ReactNode;
  /** Optional callback triggered when the user confirms the "Start Over" action. */
  onStartOver?: () => void;
  /** Whether to show the "Start Over" button in the navigation header. Defaults to true (FR-25). */
  showStartOver?: boolean;
  /** Whether starting over opens a confirmation modal dialog. Defaults to true (FR-25). */
  requireConfirmation?: boolean;
}

/** Standard non-diagnostic medical disclaimer text mandated by DR-01. */
export const MANDATORY_DISCLAIMER_TEXT =
  "This application is an informational triage aid and does not provide a medical diagnosis or treatment plan. Always consult a qualified healthcare professional for medical concerns. If you think you may be experiencing a life-threatening medical emergency, call emergency services immediately.";

/**
 * Root application shell providing header landmarks, responsive container,
 * always-visible "Start Over" control with confirm dialog (FR-25), and a
 * persistent medical disclaimer footer (DR-01).
 *
 * @param props Component properties.
 * @returns The rendered layout element.
 */
export function AppLayout({
  children,
  title = "AI-Based Symptom Checker",
  subtitle,
  emergencyNumber = "112",
  isOffline = false,
  headerActions,
  onStartOver,
  showStartOver = true,
  requireConfirmation = true,
}: AppLayoutProps): React.ReactElement {
  return (
    <div className="relative flex min-h-screen flex-col bg-background text-foreground antialiased selection:bg-primary/15">
      {/* Accessibility: skip to main content for keyboard users */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-primary focus:px-4 focus:py-2 focus:text-primary-foreground focus:shadow-lg focus:outline-none"
      >
        Skip to main content
      </a>

      {/* Offline status banner (FR-07, NFR-06) */}
      {isOffline && (
        <div
          role="status"
          aria-live="polite"
          className="border-b border-warning/40 bg-warning/15 px-4 py-2 text-center text-xs font-medium text-foreground sm:text-sm"
        >
          <span className="inline-flex items-center gap-2">
            <WifiOff className="size-4" aria-hidden="true" />
            <span>
              You are currently offline. Basic emergency information remains
              accessible, but active assessment features may be limited.
            </span>
          </span>
        </div>
      )}

      {/* Top navigation */}
      <header
        role="banner"
        className="sticky top-0 z-40 border-b border-border/70 bg-background/80 backdrop-blur-md supports-[backdrop-filter]:bg-background/70"
      >
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-3 px-4 sm:px-6">
          <RouterLink
            to="/"
            className="group flex min-w-0 items-center gap-2.5 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            aria-label="Symptom Checker home"
          >
            <span
              className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm transition-transform group-hover:scale-105"
              aria-hidden="true"
            >
              <Activity className="size-5" strokeWidth={2.25} />
            </span>
            <span className="hidden min-w-0 leading-tight sm:block">
              <span className="block truncate text-sm font-semibold tracking-tight">
                Symptom Checker
              </span>
              <span className="block truncate text-xs text-muted-foreground">
                Informational triage aid
              </span>
            </span>
          </RouterLink>

          <div className="flex items-center gap-1.5 sm:gap-2">
            {/* Always-visible Start New Assessment button with confirm dialog (FR-25) */}
            {showStartOver && (
              <StartNewAssessmentButton
                onConfirm={onStartOver}
                variant="header"
                label="Start Over"
                skipConfirm={!requireConfirmation}
              />
            )}

            {headerActions}

            <ThemeToggle />
            <AccountMenu />

            {/* Emergency quick dial */}
            <a
              href={`tel:${emergencyNumber}`}
              className="inline-flex h-10 items-center gap-1.5 rounded-md bg-danger px-3 text-sm font-semibold text-danger-foreground shadow-sm transition hover:bg-danger/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-danger focus-visible:ring-offset-2 focus-visible:ring-offset-background"
              aria-label={`Call emergency services at ${emergencyNumber}`}
            >
              <Phone className="size-4" aria-hidden="true" />
              <span>
                <span className="hidden sm:inline">Call </span>
                {emergencyNumber}
              </span>
            </a>
          </div>
        </div>
      </header>

      {/* Primary content */}
      <main
        id="main-content"
        role="main"
        tabIndex={-1}
        className="mx-auto flex w-full max-w-6xl flex-1 flex-col px-4 py-8 focus:outline-none sm:px-6 sm:py-10"
      >
        <div className="mb-6 space-y-1 sm:mb-8">
          <h1 className="text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">
            {title}
          </h1>
          {subtitle && <p className="text-sm text-muted-foreground">{subtitle}</p>}
        </div>
        <PageTransition className="flex flex-1 flex-col">{children}</PageTransition>
      </main>

      {/* Persistent medical disclaimer footer (DR-01) */}
      <footer
        role="contentinfo"
        aria-label="Medical safety disclaimer and informational notices"
        className="mt-auto border-t border-border/70 bg-muted/40"
      >
        <div className="mx-auto max-w-6xl space-y-5 px-4 py-8 sm:px-6">
          <div className="flex gap-3 rounded-xl border border-border bg-card p-4 text-card-foreground shadow-xs sm:p-5">
            <Info className="mt-0.5 size-5 shrink-0 text-primary" aria-hidden="true" />
            <div className="space-y-1.5 text-sm">
              <p className="font-medium">Important: informational use only</p>
              <p className="leading-relaxed text-muted-foreground">{MANDATORY_DISCLAIMER_TEXT}</p>
              <p className="text-xs text-muted-foreground">
                Emergency contact:{" "}
                <a
                  href={`tel:${emergencyNumber}`}
                  className="font-semibold text-danger underline-offset-4 hover:underline"
                >
                  {emergencyNumber}
                </a>
              </p>
            </div>
          </div>

          <div className="flex flex-col items-center justify-between gap-3 text-xs text-muted-foreground sm:flex-row">
            <p>© 2026 AI-Based Symptom Checker · Group 14</p>
            <nav aria-label="Footer links" className="flex items-center gap-5">
              <RouterLink to="/privacy" className="transition-colors hover:text-foreground">
                Privacy &amp; data
              </RouterLink>
              <RouterLink to="/history" className="transition-colors hover:text-foreground">
                History
              </RouterLink>
            </nav>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default AppLayout;
