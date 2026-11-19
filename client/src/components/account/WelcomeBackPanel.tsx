/**
 * @file Home-page panel for logged-in users: greeting and recent assessments.
 * Owner: Nisarg · Task: S2-NIS-15, S2-NIS-16, S2-NIS-20 · Issues: #312, #313, #321 · Requirements: FR-02
 *
 * Responsibilities:
 * - Greet the logged-in user and show their last few saved assessments.
 * - Link to the full history and to the optional health profile.
 * - Render nothing for guests, so the guest home page is unchanged.
 */
import { useQuery } from "@tanstack/react-query";
import { ChevronRight, History, UserRound } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { getAssessmentHistory } from "../../services/historyApi";
import { RiskBadge } from "../risk/RiskBadge";
import { useAuthStore } from "../../stores/authStore";

/** How many recent assessments the panel lists. */
export const RECENT_COUNT = 3;

/** Plain-language labels for assessment states. */
const STATE_LABELS: Record<string, string> = {
  COMPLETED: "Completed",
  ERROR: "Did not finish",
};

/**
 * Plain-language label for an assessment state.
 *
 * @param state - Assessment state from the API.
 * @returns A short label, "In progress" for any unfinished state.
 */
export function stateLabel(state: string): string {
  return STATE_LABELS[state] ?? "In progress";
}

/**
 * Format an ISO timestamp for the panel.
 *
 * @param value - ISO timestamp, possibly missing.
 * @returns A local date and time, or "Date unavailable".
 */
function formatDate(value?: string): string {
  if (!value) return "Date unavailable";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Date unavailable";
  return date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

/**
 * Welcome panel with the user's recent assessments.
 *
 * @returns The panel for a logged-in user, otherwise null.
 */
export function WelcomeBackPanel(): React.JSX.Element | null {
  const user = useAuthStore((s) => s.user);
  const isAuthenticated = useAuthStore((s) => s.status === "authenticated");

  const recent = useQuery({
    queryKey: ["assessment-history-recent", user?.id],
    queryFn: () => getAssessmentHistory(RECENT_COUNT, 0),
    enabled: isAuthenticated && Boolean(user),
  });

  if (!user || !isAuthenticated) return null;

  const name = user.email.split("@")[0];

  return (
    <section
      aria-labelledby="welcome-back-heading"
      className="mx-auto max-w-3xl rounded-xl border border-border bg-card p-5 text-left text-card-foreground shadow-sm sm:p-6"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 id="welcome-back-heading" className="text-lg font-semibold tracking-tight">
            Welcome back, {name}
          </h2>
          <p className="text-sm text-muted-foreground">
            Assessments you complete while logged in are saved to your history.
          </p>
        </div>
        <div className="flex gap-2">
          <Button asChild size="lg" className="h-9 px-3.5">
            <Link to="/history">
              <History className="size-4" aria-hidden="true" />
              View all history
            </Link>
          </Button>
          <Button asChild variant="outline" size="lg" className="h-9 px-3.5">
            <Link to="/profile">
              <UserRound className="size-4" aria-hidden="true" />
              My profile
            </Link>
          </Button>
        </div>
      </div>

      <h3 className="mt-6 text-xs font-medium uppercase tracking-wider text-muted-foreground">
        Recent assessments
      </h3>
      {recent.isPending && (
        <div role="status" className="mt-3 space-y-2">
          <span className="sr-only">Loading your recent assessments...</span>
          <Skeleton className="h-11 w-full" />
          <Skeleton className="h-11 w-full" />
        </div>
      )}
      {recent.isError && (
        <p role="alert" className="mt-2 text-sm text-destructive">
          Could not load your recent assessments.
        </p>
      )}
      {recent.isSuccess && recent.data.items.length === 0 && (
        <p className="mt-2 text-sm text-muted-foreground">
          No saved assessments yet. Start a symptom check above and it will appear here.
        </p>
      )}
      {recent.isSuccess && recent.data.items.length > 0 && (
        <ul className="mt-2 divide-y divide-border">
          {recent.data.items.map((item) => (
            <li key={item.id}>
              <Link
                to={`/history/${encodeURIComponent(item.id)}`}
                className="group -mx-2 flex items-center justify-between gap-3 rounded-md px-2 py-2.5 text-sm transition hover:bg-accent/60"
              >
                <span className="min-w-0">
                  <span className="block font-medium">{formatDate(item.createdAt)}</span>
                  {item.topCondition && (
                    <span className="block truncate text-xs text-muted-foreground">
                      Top possible condition: {item.topCondition}
                    </span>
                  )}
                </span>
                {item.riskLevel ? (
                  <RiskBadge level={item.riskLevel} className="shrink-0" />
                ) : (
                  <span className="shrink-0 rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium text-muted-foreground">
                    {stateLabel(item.state)}
                  </span>
                )}
                <ChevronRight
                  className="size-4 shrink-0 text-muted-foreground transition group-hover:translate-x-0.5"
                  aria-hidden="true"
                />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default WelcomeBackPanel;
