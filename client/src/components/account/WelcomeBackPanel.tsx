/**
 * @file Home-page panel for logged-in users: greeting and recent assessments.
 * Owner: Nisarg · Task: S2-NIS-15 · Issue: #312 · Requirements: FR-02
 *
 * Responsibilities:
 * - Greet the logged-in user and show their last few saved assessments.
 * - Link to the full history and to the optional health profile.
 * - Render nothing for guests, so the guest home page is unchanged.
 */
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { getAssessmentHistory } from "../../services/historyApi";
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
      className="mx-auto mt-8 max-w-3xl rounded-2xl border border-teal-100 bg-white p-5 text-left shadow-sm sm:p-6"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 id="welcome-back-heading" className="text-lg font-bold text-slate-900">
            Welcome back, {name}
          </h2>
          <p className="text-xs text-slate-500">
            Assessments you complete while logged in are saved to your history.
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            to="/history"
            className="inline-flex min-h-[40px] items-center rounded-lg bg-teal-700 px-3.5 text-xs font-semibold text-white transition hover:bg-teal-800"
          >
            View all history
          </Link>
          <Link
            to="/profile"
            className="inline-flex min-h-[40px] items-center rounded-lg border border-slate-300 px-3.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-50"
          >
            My profile
          </Link>
        </div>
      </div>

      <h3 className="mt-5 text-xs font-bold uppercase tracking-wider text-slate-500">
        Recent assessments
      </h3>
      {recent.isPending && (
        <p role="status" className="mt-2 text-sm text-slate-500">
          Loading your recent assessments...
        </p>
      )}
      {recent.isError && (
        <p role="alert" className="mt-2 text-sm text-rose-700">
          Could not load your recent assessments.
        </p>
      )}
      {recent.isSuccess && recent.data.items.length === 0 && (
        <p className="mt-2 text-sm text-slate-600">
          No saved assessments yet. Start a symptom check above and it will appear here.
        </p>
      )}
      {recent.isSuccess && recent.data.items.length > 0 && (
        <ul className="mt-2 divide-y divide-slate-100">
          {recent.data.items.map((item) => (
            <li key={item.id}>
              <Link
                to={`/history/${encodeURIComponent(item.id)}`}
                className="flex items-center justify-between gap-3 py-2.5 text-sm transition hover:text-teal-800"
              >
                <span className="text-slate-700">{formatDate(item.createdAt)}</span>
                <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-700">
                  {stateLabel(item.state)}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default WelcomeBackPanel;
