/**
 * @file Unit tests for DataExportDelete component.
 * Owner: Dimple · Task: S2-DIM-3 · Requirements: DR-06, DR-08
 *
 * Verifies:
 * - Happy path: export data triggers download and renders success status banner.
 * - Deletion confirmation: delete action opens warning modal and confirms cancellation.
 * - Permanent erasure: confirmed deletion clears stores and renders success confirmation.
 * - Error handling: API errors for export or deletion display user-friendly alerts.
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { server } from "../../test/server";
import { useConsentStore } from "../../stores/consentStore";
import { useAssessmentStore } from "../../stores/assessmentStore";
import { DataExportDelete } from "./DataExportDelete";

describe("DataExportDelete", () => {
  beforeEach(() => {
    useConsentStore.getState().clearConsent();
    useAssessmentStore.getState().clearAssessment();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  /* ------------------------------------------------------------------ */
  /*  Data Export Tests                                                 */
  /* ------------------------------------------------------------------ */

  it("renders export and delete action cards with DPDP Act references", () => {
    render(<DataExportDelete />);

    expect(
      screen.getByRole("heading", { name: /export my data/i, level: 3 }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /delete all my data/i, level: 3 }),
    ).toBeInTheDocument();
    expect(
      screen.getAllByText(/Section 11, DPDP Act 2023/i).length,
    ).toBe(2);
  });

  it("exports data successfully and displays success status", async () => {
    const user = userEvent.setup();
    const handleExported = vi.fn();

    server.use(
      http.get("/api/v1/privacy/export", () =>
        HttpResponse.json(
          {
            exportedAt: "2026-10-30T10:00:00Z",
            policyVersion: "1.0.0",
            consentId: "test-consent-uuid",
            consentedAt: "2026-10-30T09:00:00Z",
            activeAssessmentId: null,
            symptomsCount: 2,
            dataRetentionNotice: "Retained for 24 hours.",
            rightsNotice: "Right to access and erase.",
          },
          { status: 200 },
        ),
      ),
    );

    render(<DataExportDelete onDataExported={handleExported} />);

    const exportBtn = screen.getByRole("button", {
      name: /download data export/i,
    });
    await user.click(exportBtn);

    await waitFor(() => {
      expect(
        screen.getByText(/data has been successfully exported/i),
      ).toBeInTheDocument();
    });

    expect(handleExported).toHaveBeenCalledTimes(1);
  });

  it("handles export API error with a clear error alert", async () => {
    const user = userEvent.setup();

    server.use(
      http.get("/api/v1/privacy/export", () =>
        HttpResponse.json({ message: "Export service unavailable" }, { status: 500 }),
      ),
    );

    render(<DataExportDelete />);

    const exportBtn = screen.getByRole("button", {
      name: /download data export/i,
    });
    await user.click(exportBtn);

    await waitFor(() => {
      expect(
        screen.getByText(/unable to generate your data export/i),
      ).toBeInTheDocument();
    });
  });

  /* ------------------------------------------------------------------ */
  /*  Data Deletion Tests                                               */
  /* ------------------------------------------------------------------ */

  it("opens confirmation dialog with warning before deleting", async () => {
    const user = userEvent.setup();
    render(<DataExportDelete />);

    const deleteBtn = screen.getByRole("button", {
      name: /permanently delete all data/i,
    });
    await user.click(deleteBtn);

    // Modal dialog is open
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /confirm permanent deletion/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/all conversation history and symptom entries/i),
    ).toBeInTheDocument();
  });

  it("closes confirmation modal when Cancel is clicked without deleting", async () => {
    const user = userEvent.setup();
    render(<DataExportDelete />);

    const deleteBtn = screen.getByRole("button", {
      name: /permanently delete all data/i,
    });
    await user.click(deleteBtn);

    const cancelBtn = screen.getByRole("button", { name: /cancel/i });
    await user.click(cancelBtn);

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("permanently erases data, clears stores, and displays success banner", async () => {
    const user = userEvent.setup();
    const handleDeleted = vi.fn();

    // Populate stores before deletion
    useConsentStore.getState().recordConsent("c-123", "1.0.0");

    server.use(
      http.delete("/api/v1/privacy/data", () =>
        HttpResponse.json(
          {
            success: true,
            deletedAt: new Date().toISOString(),
            message: "All data erased.",
          },
          { status: 200 },
        ),
      ),
    );

    render(<DataExportDelete onDataDeleted={handleDeleted} />);

    const deleteBtn = screen.getByRole("button", {
      name: /permanently delete all data/i,
    });
    await user.click(deleteBtn);

    const confirmBtn = screen.getByRole("button", {
      name: /yes, permanently delete/i,
    });
    await user.click(confirmBtn);

    await waitFor(() => {
      expect(
        screen.getByText(/all your data has been permanently deleted/i),
      ).toBeInTheDocument();
    });

    // Verify stores were wiped
    expect(useConsentStore.getState().consentId).toBeNull();
    expect(handleDeleted).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("handles deletion API error with a safe alert notice", async () => {
    const user = userEvent.setup();

    server.use(
      http.delete("/api/v1/privacy/data", () =>
        HttpResponse.json({ message: "Database lock" }, { status: 500 }),
      ),
    );

    render(<DataExportDelete />);

    const deleteBtn = screen.getByRole("button", {
      name: /permanently delete all data/i,
    });
    await user.click(deleteBtn);

    const confirmBtn = screen.getByRole("button", {
      name: /yes, permanently delete/i,
    });
    await user.click(confirmBtn);

    await waitFor(() => {
      expect(
        screen.getByText(/unable to complete data deletion/i),
      ).toBeInTheDocument();
    });
  });
});
