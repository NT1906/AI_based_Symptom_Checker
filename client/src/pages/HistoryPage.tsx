
/**
 * @file Authenticated assessment history list and detail page.
 * Owner: Rutva - Task: S2-RUT-2 - Issue: #181
 * Requirement: FR-02
 */

import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { AppLayout } from "../components/layout/AppLayout";
import { useAuthStore } from "../stores/authStore";
import {
  getAssessmentHistory,
  getAssessmentHistoryDetail,
} from "../services/historyApi";

/** Number of history records requested per page. */
const PAGE_SIZE = 20;

/**
 * Format an assessment timestamp for display.
 *
 * @param value - UTC timestamp returned by the API.
 * @returns Localized date or a fallback when unavailable.
 */
function formatDate(value?: string): string {
  if (!value) {
    return "Date unavailable";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "Date unavailable";
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

/**
 * Convert an assessment lifecycle state into readable text.
 *
 * @param state - Assessment lifecycle state.
 * @returns Human-readable state label.
 */
function formatState(state: string): string {
  return state
    .toLowerCase()
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

/** Render the authenticated user's assessment history and detail views. */
export default function HistoryPage(): React.JSX.Element {
  const navigate = useNavigate();
  const { assessmentId } = useParams<{ assessmentId: string }>();
  const { status, user, loadCurrentUser } = useAuthStore();
  const [offset, setOffset] = useState(0);

  useEffect(() => {
    if (status === "idle") {
      void loadCurrentUser().catch(() => undefined);
    }
  }, [status, loadCurrentUser]);

  const isAuthenticated = status === "authenticated" && Boolean(user);

  const historyQuery = useQuery({
    queryKey: ["assessment-history", offset],
    queryFn: () => getAssessmentHistory(PAGE_SIZE, offset),
    enabled: isAuthenticated && !assessmentId,
  });

  const detailQuery = useQuery({
    queryKey: ["assessment-history-detail", assessmentId],
    queryFn: () => getAssessmentHistoryDetail(assessmentId ?? ""),
    enabled: isAuthenticated && Boolean(assessmentId),
  });

  if (status === "idle" || status === "loading") {
    return (
      <AppLayout title="Assessment History" showStartOver={false}>
        <p role="status" className="py-12 text-center text-slate-600">
          Checking your session...
        </p>
      </AppLayout>
    );
  }

  if (status === "error") {
    return (
      <AppLayout title="Assessment History" showStartOver={false}>
        <section className="mx-auto max-w-xl py-12 text-center">
          <h2 className="text-xl font-bold">Unable to verify your session</h2>
          <p className="mt-2 text-slate-600">
            Please try again. Your assessment history has not been loaded.
          </p>
          <button
            type="button"
            onClick={() => void loadCurrentUser().catch(() => undefined)}
            className="mt-5 rounded-lg bg-teal-700 px-5 py-3 font-semibold text-white hover:bg-teal-800"
          >
            Retry
          </button>
        </section>
      </AppLayout>
    );
  }

  if (!isAuthenticated) {
    return (
      <AppLayout title="Assessment History" showStartOver={false}>
        <section className="mx-auto max-w-xl py-12 text-center">
          <h2 className="text-xl font-bold">Log in to view your history</h2>
          <p className="mt-2 text-slate-600">
            Your previous assessments are available after you log in.
          </p>
          <Link
            to="/login"
            className="mt-5 inline-flex rounded-lg bg-teal-700 px-5 py-3 font-semibold text-white hover:bg-teal-800"
          >
            Log in
          </Link>
        </section>
      </AppLayout>
    );
  }

  if (assessmentId) {
    return (
      <AppLayout title="Assessment Details" showStartOver={false}>
        <section className="space-y-6">
          <button
            type="button"
            onClick={() => navigate("/history")}
            className="text-sm font-semibold text-teal-800 underline hover:text-teal-950"
          >
            Back to history
          </button>

          {detailQuery.isPending && (
            <p role="status" className="py-8 text-slate-600">
              Loading assessment details...
            </p>
          )}

          {detailQuery.isError && (
            <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-5 text-rose-900">
              <h2 className="font-bold">Unable to load this assessment</h2>
              <p className="mt-1 text-sm">
                It may not exist or may not be available to your account.
              </p>
              <button
                type="button"
                onClick={() => void detailQuery.refetch()}
                className="mt-4 font-semibold underline"
              >
                Try again
              </button>
            </div>
          )}

          {detailQuery.data && (
            <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-bold">Assessment information</h2>
              <dl className="mt-5 divide-y divide-slate-100">
                <div className="py-3">
                  <dt className="text-sm text-slate-500">Assessment ID</dt>
                  <dd className="mt-1 break-all font-medium">
                    {detailQuery.data.id}
                  </dd>
                </div>
                <div className="py-3">
                  <dt className="text-sm text-slate-500">Status</dt>
                  <dd className="mt-1 font-medium">
                    {formatState(detailQuery.data.state)}
                  </dd>
                </div>
                <div className="py-3">
                  <dt className="text-sm text-slate-500">Created</dt>
                  <dd className="mt-1 font-medium">
                    {formatDate(detailQuery.data.createdAt)}
                  </dd>
                </div>
                <div className="py-3">
                  <dt className="text-sm text-slate-500">Last updated</dt>
                  <dd className="mt-1 font-medium">
                    {formatDate(detailQuery.data.updatedAt)}
                  </dd>
                </div>
              </dl>
              <p className="mt-5 text-sm text-slate-600">
                This page displays assessment metadata currently provided by
                the history service. It does not provide a medical diagnosis.
              </p>
            </article>
          )}
        </section>
      </AppLayout>
    );
  }

  return (
    <AppLayout title="Assessment History" subtitle="Your previous assessments" showStartOver={false}>
      <section className="space-y-6">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">History</h2>
          <p className="mt-1 text-sm text-slate-600">
            Review the status and dates of your previous assessments.
          </p>
        </div>

        {historyQuery.isPending && (
          <p role="status" className="py-10 text-center text-slate-600">
            Loading your assessment history...
          </p>
        )}

        {historyQuery.isError && (
          <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 p-5 text-rose-900">
            <h3 className="font-bold">Unable to load assessment history</h3>
            <p className="mt-1 text-sm">
              Please check your connection and try again.
            </p>
            <button
              type="button"
              onClick={() => void historyQuery.refetch()}
              className="mt-4 font-semibold underline"
            >
              Retry
            </button>
          </div>
        )}

        {historyQuery.data && historyQuery.data.items.length === 0 && (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center">
            <h3 className="text-lg font-bold">No assessments yet</h3>
            <p className="mt-2 text-sm text-slate-600">
              Your completed and ongoing assessments will appear here.
            </p>
            <Link
              to="/chat"
              className="mt-5 inline-flex rounded-lg bg-teal-700 px-5 py-3 font-semibold text-white hover:bg-teal-800"
            >
              Start an assessment
            </Link>
          </div>
        )}

        {historyQuery.data && historyQuery.data.items.length > 0 && (
          <>
            <ul className="space-y-3">
              {historyQuery.data.items.map((assessment) => (
                <li key={assessment.id}>
                  <Link
                    to={`/history/${encodeURIComponent(assessment.id)}`}
                    className="block rounded-xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-teal-400 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-teal-600"
                  >
                    <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
                      <div className="min-w-0">
                        <p className="break-all font-semibold text-slate-900">
                          Assessment {assessment.id}
                        </p>
                        <p className="mt-1 text-sm text-slate-500">
                          {formatDate(assessment.createdAt)}
                        </p>
                      </div>
                      <span className="w-fit rounded-full bg-teal-50 px-3 py-1 text-sm font-semibold text-teal-800">
                        {formatState(assessment.state)}
                      </span>
                    </div>
                    <span className="mt-3 inline-block text-sm font-semibold text-teal-800">
                      View details
                    </span>
                  </Link>
                </li>
              ))}
            </ul>

            <div className="flex items-center justify-between gap-4 border-t border-slate-200 pt-5">
              <button
                type="button"
                disabled={offset === 0 || historyQuery.isFetching}
                onClick={() => setOffset((current) => Math.max(0, current - PAGE_SIZE))}
                className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-40"
              >
                Previous
              </button>
              <span className="text-sm text-slate-500">
                Showing {offset + 1}-{offset + historyQuery.data.items.length}
              </span>
              <button
                type="button"
                disabled={historyQuery.data.nextOffset === null || historyQuery.isFetching}
                onClick={() => setOffset(historyQuery.data?.nextOffset ?? offset)}
                className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </>
        )}
      </section>
    </AppLayout>
  );
}
