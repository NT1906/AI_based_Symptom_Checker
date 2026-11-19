/**
 * @file Unit tests for ConsentReAskModal component.
 * Owner: Dimple · Task: S2-DIM-3 · Requirements: DR-06, DR-08
 *
 * Verifies:
 * - Policy version checking: renders modal when consent version is outdated or missing.
 * - Does not render when consent version is current.
 * - Re-consent happy path: records updated consent and updates store.
 * - Decline flow: clears session consent on decline.
 * - Error handling: displays user-friendly error on failed network request.
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { server } from "../../test/server";
import { useConsentStore } from "../../stores/consentStore";
import { CURRENT_POLICY_VERSION } from "../../services/consentApi";
import { ConsentReAskModal } from "./ConsentReAskModal";

describe("ConsentReAskModal", () => {
  beforeEach(() => {
    useConsentStore.getState().clearConsent();
  });

  it("does not render when user has already consented to the current policy version", () => {
    useConsentStore.getState().recordConsent("c-current", CURRENT_POLICY_VERSION);

    const { container } = render(<ConsentReAskModal />);
    expect(container.firstChild).toBeNull();
  });

  it("renders when stored policy version is outdated (version mismatch)", () => {
    // User consented to old version 0.9.0
    useConsentStore.getState().recordConsent("c-old", "0.9.0");

    render(<ConsentReAskModal />);

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /updated privacy & data notice/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(`Version ${CURRENT_POLICY_VERSION}`)).toBeInTheDocument();
  });

  it("renders when forced open via forceOpen prop", () => {
    useConsentStore.getState().recordConsent("c-curr", CURRENT_POLICY_VERSION);

    render(<ConsentReAskModal forceOpen={true} />);

    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("records updated consent and calls onReConsented on accept", async () => {
    const user = userEvent.setup();
    const handleReConsented = vi.fn();

    useConsentStore.getState().recordConsent("c-old", "0.9.0");

    server.use(
      http.post("/api/v1/consents", () =>
        HttpResponse.json({ consentId: "new-consent-id" }, { status: 201 }),
      ),
    );

    render(<ConsentReAskModal onReConsented={handleReConsented} />);

    const acceptBtn = screen.getByRole("button", {
      name: /i agree & continue/i,
    });
    await user.click(acceptBtn);

    await waitFor(() => {
      expect(handleReConsented).toHaveBeenCalledWith("new-consent-id");
    });

    expect(useConsentStore.getState().consentId).toBe("new-consent-id");
    expect(useConsentStore.getState().policyVersion).toBe(CURRENT_POLICY_VERSION);
  });

  it("clears consent and calls onDeclined when user declines", async () => {
    const user = userEvent.setup();
    const handleDeclined = vi.fn();

    useConsentStore.getState().recordConsent("c-old", "0.9.0");

    render(<ConsentReAskModal onDeclined={handleDeclined} />);

    const declineBtn = screen.getByRole("button", {
      name: /decline & clear session/i,
    });
    await user.click(declineBtn);

    expect(useConsentStore.getState().consentId).toBeNull();
    expect(handleDeclined).toHaveBeenCalledTimes(1);
  });

  it("handles consent API failure with an alert within the modal", async () => {
    const user = userEvent.setup();

    useConsentStore.getState().recordConsent("c-old", "0.9.0");

    server.use(
      http.post("/api/v1/consents", () =>
        HttpResponse.json({ message: "Network timeout" }, { status: 500 }),
      ),
    );

    render(<ConsentReAskModal />);

    const acceptBtn = screen.getByRole("button", {
      name: /i agree & continue/i,
    });
    await user.click(acceptBtn);

    await waitFor(() => {
      expect(
        screen.getByText(/unable to record your updated consent/i),
      ).toBeInTheDocument();
    });
  });
});
