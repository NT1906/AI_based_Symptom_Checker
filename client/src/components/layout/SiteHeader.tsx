/**
 * @file Site header: brand, Start Over, theme, account and emergency call.
 * Owner: Nisarg · Task: S2-NIS-19, S2-NIS-20 · Issues: #320, #321 · Requirements: FR-25, NFR-06
 *
 * Shared by AppLayout and the landing page so every screen has the same header.
 */
import { Activity, Phone } from "lucide-react";
import { ThemeToggle } from "@/components/theme/ThemeToggle";
import { AccountMenu } from "../account/AccountMenu";
import { RouterLink } from "./RouterLink";
import { StartNewAssessmentButton } from "./StartNewAssessmentButton";

/** Props for SiteHeader. */
export type SiteHeaderProps = {
  /** Emergency number for the call button. */
  emergencyNumber?: string;
  /** Show the Start Over control (FR-25). */
  showStartOver?: boolean;
  /** Called when Start Over is confirmed. */
  onStartOver?: () => void;
  /** Ask before starting over. */
  requireConfirmation?: boolean;
  /** Extra controls shown before the theme toggle. */
  headerActions?: React.ReactNode;
};

/**
 * Sticky translucent header.
 *
 * @param props - Header options.
 * @returns The header landmark.
 */
export function SiteHeader({
  emergencyNumber = "112",
  showStartOver = false,
  onStartOver,
  requireConfirmation = true,
  headerActions,
}: SiteHeaderProps): React.JSX.Element {
  return (
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
  );
}
