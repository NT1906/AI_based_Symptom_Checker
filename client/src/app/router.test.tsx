/**
 * @file Tests for lazy-loaded application routes.
 * Owner: Rutva - Task: S2-RUT-7 - Issue: #216
 * Requirements: NFR-01, NFR-06
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { RouterProvider, createMemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { router } from "./router";

describe("application router", () => {
  it("defines all application routes with lazy-loaded components", () => {
    const paths = router.routes.map((route) => route.path);

    expect(paths).toEqual([
      "/",
      "/chat",
      "/profile",
      "/login",
      "/register",
      "/history",
      "/history/:assessmentId",
      "/privacy",
    ]);

    expect(router.routes.every((route) => typeof route.lazy === "function")).toBe(true);
  });

  it("loads the landing page when the root route is visited", async () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });

    const testRouter = createMemoryRouter(router.routes, {
      initialEntries: ["/"],
    });

    render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={testRouter} />
      </QueryClientProvider>,
    );

    expect(await screen.findByRole("button", { name: /start symptom check/i })).toBeInTheDocument();
  });
});
