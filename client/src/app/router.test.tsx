/**
 * @file Tests for the route table: not-found page, error hand-off, scroll root.
 * Owner: Nisarg · Task: S2-NIS-25 · Issue: #338 · Requirements: NFR-05, NFR-09
 */

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, Link, RouterProvider, type RouteObject } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ErrorBoundary } from "../components/layout/ErrorBoundary";
import { RouteErrorPage } from "../pages/NotFoundPage";
import { RootLayout, routes } from "./router";

/** Mounts the given routes at `path` in an in-memory router. */
function renderAt(path: string, table: RouteObject[] = routes) {
  const router = createMemoryRouter(table, { initialEntries: [path] });
  return render(
    <ErrorBoundary>
      <RouterProvider router={router} />
    </ErrorBoundary>,
  );
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("application routes", () => {
  it("shows a friendly not-found page for an unknown URL", async () => {
    renderAt("/this-page-does-not-exist");

    expect(
      await screen.findByRole("heading", { name: "We couldn't find that page" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Back to home/i })).toHaveAttribute("href", "/");
    expect(screen.getByRole("link", { name: /Start symptom check/i })).toHaveAttribute(
      "href",
      "/chat",
    );
    expect(screen.queryByText(/Unexpected Application Error/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Hey developer/i)).not.toBeInTheDocument();
  });

  it("treats a nested unknown path as not found too", async () => {
    renderAt("/history/abc/extra");

    expect(
      await screen.findByRole("heading", { name: "We couldn't find that page" }),
    ).toBeInTheDocument();
  });

  it("still renders known pages inside the root layout", async () => {
    renderAt("/privacy");

    expect(await screen.findAllByText(/Privacy/i)).not.toHaveLength(0);
    expect(screen.queryByText(/We couldn't find that page/)).not.toBeInTheDocument();
  });

  it("opens a newly visited page at the top, but not for in-page # links", async () => {
    const scrollTo = vi.spyOn(window, "scrollTo");
    renderAt("/", [
      {
        element: <RootLayout />,
        children: [
          {
            path: "/",
            element: (
              <>
                <Link to="/#section">Jump to section</Link>
                <Link to="/next">Next page</Link>
              </>
            ),
          },
          { path: "/next", element: <h1>Next page loaded</h1> },
        ],
      },
    ]);
    const user = userEvent.setup();

    await user.click(await screen.findByRole("link", { name: "Jump to section" }));
    expect(scrollTo).not.toHaveBeenCalled();

    await user.click(screen.getByRole("link", { name: "Next page" }));
    expect(await screen.findByRole("heading", { name: "Next page loaded" })).toBeInTheDocument();
    expect(scrollTo).toHaveBeenCalledWith(0, 0);
  });

  it("hands other route errors to the app ErrorBoundary instead of the developer screen", async () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    function Broken(): React.JSX.Element {
      throw new Error("render failed");
    }
    renderAt("/", [
      {
        element: <RootLayout />,
        errorElement: <RouteErrorPage />,
        children: [{ path: "/", element: <Broken /> }],
      },
    ]);

    expect(await screen.findByText("Something went wrong")).toBeInTheDocument();
    expect(screen.queryByText(/Hey developer/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/We couldn't find that page/)).not.toBeInTheDocument();
  });
});
