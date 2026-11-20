/**
 * @file Site footer with the persistent medical disclaimer (DR-01).
 * Owner: Nisarg · Task: S2-NIS-19, S2-NIS-20 · Issues: #320, #321 · Requirements: DR-01, NFR-06
 */
import { Info } from "lucide-react";
import { MANDATORY_DISCLAIMER_TEXT } from "./disclaimer";
import { RouterLink } from "./RouterLink";

/**
 * Footer landmark with the disclaimer and site links.
 *
 * @param props - Footer options.
 * @param props.emergencyNumber - Emergency number to show.
 * @returns The footer.
 */
export function SiteFooter({
  emergencyNumber = "112",
}: {
  emergencyNumber?: string;
}): React.JSX.Element {
  return (
    <footer
      role="contentinfo"
      aria-label="Medical safety disclaimer and informational notices"
      className="mt-auto border-t border-border/70 bg-muted/40"
    >
      <div className="mx-auto max-w-6xl space-y-5 px-4 py-8 sm:px-6">
        <div className="flex gap-3 rounded-xl border border-border bg-card p-4 text-card-foreground shadow-xs sm:p-5">
          <Info className="mt-0.5 size-5 shrink-0 text-primary" aria-hidden="true" />
          <div className="space-y-1.5 text-sm">
            <p className="font-medium">This is not a medical diagnosis.</p>
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
  );
}
