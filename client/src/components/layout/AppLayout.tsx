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
import { WifiOff } from "lucide-react";
import { cn } from "@/lib/utils";
import { PageTransition } from "./PageTransition";
import { SiteFooter } from "./SiteFooter";
import { SiteHeader } from "./SiteHeader";

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
  /** Narrow, centred column for reading and form pages (title aligns with content). */
  narrow?: boolean;
}

export { MANDATORY_DISCLAIMER_TEXT } from "./disclaimer";

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
  narrow = false,
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
              You are currently offline. Basic emergency information remains accessible, but active
              assessment features may be limited.
            </span>
          </span>
        </div>
      )}

      <SiteHeader
        emergencyNumber={emergencyNumber}
        showStartOver={showStartOver}
        onStartOver={onStartOver}
        requireConfirmation={requireConfirmation}
        headerActions={headerActions}
      />

      {/* Primary content */}
      <main
        id="main-content"
        role="main"
        tabIndex={-1}
        className="mx-auto flex w-full max-w-6xl flex-1 flex-col px-4 py-8 focus:outline-none sm:px-6 sm:py-10"
      >
        <div className={cn("mb-6 space-y-1 sm:mb-8", narrow && "mx-auto w-full max-w-3xl")}>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">
            {title}
          </h1>
          {subtitle && <p className="text-sm text-muted-foreground">{subtitle}</p>}
        </div>
        <PageTransition className="flex flex-1 flex-col">{children}</PageTransition>
      </main>

      <SiteFooter emergencyNumber={emergencyNumber} />
    </div>
  );
}

export default AppLayout;
