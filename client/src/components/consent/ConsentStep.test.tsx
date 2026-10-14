/**
 * @file Tests for the ConsentStep component.
 * Owner: Dimple · Task: S1-DIM-1 · Requirements: DR-08
 *
 * Covers: happy path (user agrees → POST /consents → onConsented called),
 * decline path (user clicks Decline → onDeclined called, no API call),
 * API error path (server fails → error message shown, onConsented NOT called),
 * checkbox gate (Agree button disabled until checkbox is ticked).
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { server } from "../../test/server";
import { useConsentStore } from "../../stores/consentStore";
import { ConsentStep } from "./ConsentStep";

/** Wraps component with a fresh QueryClient per test. */
function renderConsentStep(
  onConsented = vi.fn(),
  onDeclined = vi.fn()
) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return {
    onConsented,
    onDeclined,
    ...render(
      <QueryClientProvider client={qc}>
        <ConsentStep onConsented={onConsented} onDeclined={onDeclined} />
      </QueryClientProvider>
    ),
  };
}

/** Tick the checkbox, then click "I Agree". */
async function agreeToConsent(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("checkbox"));
  await user.click(screen.getByRole("button", { name: /i agree/i }));
}

describe("ConsentStep", () => {
  beforeEach(() => {
    // Reset Zustand store between tests
    useConsentStore.setState({
      consentId: null,
      consentedAt: null,
      policyVersion: null,
    });
  });

  it("renders the consent dialog with title and consent text", () => {
    renderConsentStep();
    expect(
      screen.getByRole("dialog", { name: /your consent is required/i })
    ).toBeInTheDocument();
    expect(screen.getByText(/not a medical diagnosis/i)).toBeInTheDocument();
    expect(screen.getByText(/112/i)).toBeInTheDocument(); // emergency number present
  });

  it("Agree button is disabled until checkbox is ticked", async () => {
    const user = userEvent.setup();
    renderConsentStep();
    const agreeBtn = screen.getByRole("button", { name: /i agree/i });
    expect(agreeBtn).toBeDisabled();
    await user.click(screen.getByRole("checkbox"));
    expect(agreeBtn).toBeEnabled();
  });

  it("happy path: records consent and calls onConsented", async () => {
    const FAKE_ID = "consent-uuid-abc";
    server.use(
      http.post("/api/v1/consents", () =>
        HttpResponse.json({ consentId: FAKE_ID })
      )
    );

    const user = userEvent.setup();
    const { onConsented } = renderConsentStep();

    await agreeToConsent(user);

    await waitFor(() => expect(onConsented).toHaveBeenCalledOnce());
    // Zustand store updated
    expect(useConsentStore.getState().consentId).toBe(FAKE_ID);
    expect(useConsentStore.getState().policyVersion).toBe("1.0.0");
  });

  it("decline path: calls onDeclined and does NOT hit the API", async () => {
    let apiHit = false;
    server.use(
      http.post("/api/v1/consents", () => {
        apiHit = true;
        return HttpResponse.json({ consentId: "x" });
      })
    );

    const user = userEvent.setup();
    const { onDeclined, onConsented } = renderConsentStep();

    await user.click(screen.getByRole("button", { name: /decline/i }));

    expect(onDeclined).toHaveBeenCalledOnce();
    expect(onConsented).not.toHaveBeenCalled();
    expect(apiHit).toBe(false);
  });

  it("API error: shows error message and does NOT call onConsented", async () => {
    server.use(
      http.post("/api/v1/consents", () =>
        HttpResponse.json({ detail: "Server error" }, { status: 500 })
      )
    );

    const user = userEvent.setup();
    const { onConsented } = renderConsentStep();

    await agreeToConsent(user);

    await waitFor(() =>
      expect(screen.getByRole("alert")).toBeInTheDocument()
    );
    expect(screen.getByRole("alert")).toHaveTextContent(/unable to record/i);
    expect(onConsented).not.toHaveBeenCalled();
    expect(useConsentStore.getState().consentId).toBeNull();
  });
});
