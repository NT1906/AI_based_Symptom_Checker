/**
 * @file "Page not found" screen and the route-level error element.
 * Owner: Nisarg · Task: S2-NIS-25 · Issue: #338 · Requirements: NFR-05, NFR-09
 *
 * Without an error element, React Router shows its own developer screen
 * ("Unexpected Application Error! … Hey developer") for unknown URLs and for
 * any error thrown while rendering a route. This file replaces that:
 * - unknown URLs get a friendly page with links back into the app;
 * - every other route error is re-thrown, so the app-level `ErrorBoundary`
 * (S2-DIM-7) shows its recovery screen and reports it.
 */

import { ArrowLeft, Stethoscope } from "lucide-react";
import { isRouteErrorResponse, Link, useRouteError } from "react-router-dom";
import { AppLayout } from "../components/layout/AppLayout";

/** Shared look for the two links on the not-found page. */
const LINK_BASE =
  "inline-flex h-11 items-center justify-center gap-2 rounded-lg px-5 text-sm font-semibold transition focus:outline-none focus-visible:ring-2 focus-visible:ring-ring";

/**
 * Friendly page shown for a URL that matches no route.
 *
 * @returns The not-found page inside the normal layout (header, disclaimer).
 */
export function NotFoundPage(): React.JSX.Element {
  return (
    <AppLayout title="Page not found" showStartOver={false} narrow>
      <section className="py-10 text-center" aria-labelledby="not-found-heading">
        <p className="text-sm font-semibold text-primary-strong">404</p>
        <h2 id="not-found-heading" className="mt-2 text-2xl font-semibold tracking-tight">
          We couldn't find that page
        </h2>
        <p className="mx-auto mt-3 max-w-md text-muted-foreground">
          The link may be mistyped or out of date. You can go back to the home page or start a
          symptom check.
        </p>
        <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
          <Link
            to="/"
            className={`${LINK_BASE} border border-input bg-card text-foreground hover:bg-accent`}
          >
            <ArrowLeft className="size-4" aria-hidden="true" /> Back to home
          </Link>
          <Link
            to="/chat"
            className={`${LINK_BASE} bg-primary text-primary-foreground hover:bg-primary/90`}
          >
            <Stethoscope className="size-4" aria-hidden="true" /> Start symptom check
          </Link>
        </div>
      </section>
    </AppLayout>
  );
}

/**
 * Route `errorElement`: a 404 shows {@link NotFoundPage}; anything else is
 * re-thrown to the app-level `ErrorBoundary`.
 *
 * @returns The not-found page for 404 responses.
 * @throws The original route error for every other case.
 */
export function RouteErrorPage(): React.JSX.Element {
  const error = useRouteError();
  if (isRouteErrorResponse(error) && error.status === 404) {
    return <NotFoundPage />;
  }
  throw error;
}
