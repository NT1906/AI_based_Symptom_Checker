/**
 * @file Application shell layout with accessible navigation landmarks, always-visible start over control, and a persistent medical disclaimer footer.
 *
 * Enforces requirement DR-01 (mandatory persistent medical disclaimer on every screen),
 * FR-25 (always-visible "Start new assessment" button with confirm dialog),
 * and NFR-06 (accessible landmarks, high-contrast typography, and responsive layout).
 *
 * Owner: Mann (Frontend + Deployment · Testing) · Tasks: S0-MAN-1, S1-MAN-4 · Requirements: DR-01, FR-25, NFR-06
 */

import React from "react";
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
    <div className="flex min-h-screen flex-col bg-slate-50 text-slate-900 antialiased selection:bg-teal-100 selection:text-teal-900">
      {/* Accessibility: Skip to main content link for keyboard navigation */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-teal-800 focus:px-4 focus:py-2 focus:text-white focus:shadow-lg focus:outline-none focus:ring-2 focus:ring-white"
      >
        Skip to main content
      </a>

      {/* Offline Status Warning Banner (FR-07, NFR-06) */}
      {isOffline && (
        <div
          role="status"
          aria-live="polite"
          className="border-b border-amber-300 bg-amber-50 px-4 py-2 text-center text-xs font-semibold text-amber-900 sm:text-sm"
        >
          <span className="inline-flex items-center gap-1.5">
            <span aria-hidden="true">⚠️</span>
            <span>
              You are currently offline. Basic emergency information remains
              accessible, but active assessment features may be limited.
            </span>
          </span>
        </div>
      )}

      {/* Primary Header Navigation Landmark */}
      <header
        role="banner"
        className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/95 backdrop-blur-sm shadow-xs transition-colors"
      >
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3 sm:px-6">
          {/* Brand Logo & Landmark Title */}
          <div className="flex items-center gap-3">
            <div
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-teal-700 text-white shadow-xs"
              aria-hidden="true"
            >
              <svg
                className="h-6 w-6"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                strokeWidth={2.5}
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M12 6v12M6 12h12" />
              </svg>
            </div>
            <div>
              <span className="block text-xs font-semibold tracking-wider text-teal-800 uppercase">
                Informational Triage Aid
              </span>
              <h1 className="text-lg font-bold tracking-tight text-slate-900 sm:text-xl">
                {title}
              </h1>
              {subtitle && <p className="text-xs text-slate-500">{subtitle}</p>}
            </div>
          </div>

          {/* Header Action Controls */}
          <div className="flex items-center gap-2 sm:gap-3">
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

            {/* Emergency Hotline Quick Dial Button */}
            <a
              href={`tel:${emergencyNumber}`}
              className="inline-flex min-h-[44px] items-center gap-1.5 rounded-lg bg-rose-600 px-3 py-2 text-xs font-bold text-white shadow-xs transition hover:bg-rose-700 focus:outline-none focus:ring-2 focus:ring-rose-600 focus:ring-offset-2 sm:px-3.5"
              aria-label={`Call emergency services at ${emergencyNumber}`}
            >
              <span aria-hidden="true">🚨</span>
              <span>Call {emergencyNumber}</span>
            </a>
          </div>
        </div>
      </header>

      {/* Primary Content Landmark */}
      <main
        id="main-content"
        role="main"
        tabIndex={-1}
        className="mx-auto flex w-full max-w-5xl flex-1 flex-col px-4 py-6 sm:px-6 sm:py-8 focus:outline-none"
      >
        {children}
      </main>

      {/* Persistent Medical Disclaimer Footer (Mandated by DR-01) */}
      <footer
        role="contentinfo"
        aria-label="Medical safety disclaimer and informational notices"
        className="mt-auto border-t border-slate-200 bg-white py-6"
      >
        <div className="mx-auto max-w-5xl px-4 sm:px-6">
          <div className="rounded-xl border border-teal-100 bg-teal-50/50 p-4 shadow-xs sm:p-5">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:gap-4">
              <div
                className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-teal-700 text-white"
                aria-hidden="true"
              >
                <span className="text-sm font-bold">i</span>
              </div>
              <div className="space-y-1.5 text-xs text-slate-600 sm:text-sm">
                <p className="font-semibold text-slate-900">
                  Important Informational Use Notice (DR-01)
                </p>
                <p className="leading-relaxed text-slate-700">{MANDATORY_DISCLAIMER_TEXT}</p>
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 pt-1 text-xs text-slate-500">
                  <span>
                    Emergency Contact:{" "}
                    <a
                      href={`tel:${emergencyNumber}`}
                      className="font-semibold text-rose-700 underline hover:text-rose-900 focus:outline-none focus:ring-2 focus:ring-rose-600"
                    >
                      {emergencyNumber}
                    </a>
                  </span>
                  <span>•</span>
                  <span>Data is processed in-memory and not shared with third parties.</span>
                  <span>•</span>
                  <span>WCAG 2.1 AA Compliant</span>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-4 flex flex-col items-center justify-between gap-2 border-t border-slate-100 pt-4 text-xs text-slate-500 sm:flex-row">
            <p>© 2026 AI-Based Symptom Checker · Group 14</p>
            <nav aria-label="Footer links" className="flex items-center gap-4">
              <span className="hover:text-slate-800">Privacy &amp; Data Policy</span>
              <span>•</span>
              <span className="hover:text-slate-800">Terms of Informational Use</span>
            </nav>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default AppLayout;
