/**
 * @file Unit tests for ProfilePage — happy path, edge cases, and failures.
 * Owner: Dimple · Task: S2-DIM-1 · Requirements: FR-02
 */

import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { MemoryRouter } from "react-router-dom";

import { server } from "../test/server";
import { useProfileStore } from "../stores/profileStore";
import ProfilePage from "./ProfilePage";

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

/** Render the ProfilePage inside a MemoryRouter. */
function renderPage(): ReturnType<typeof render> {
  return render(
    <MemoryRouter initialEntries={["/profile"]}>
      <ProfilePage />
    </MemoryRouter>,
  );
}

/** Default mock GET response returning an empty profile. */
const emptyProfileHandler = http.get("/api/v1/profile", () =>
  HttpResponse.json({}, { status: 200 }),
);

/** Default mock PUT response acknowledging the save. */
const saveProfileHandler = http.put("/api/v1/profile", () =>
  HttpResponse.json({ profileId: "test-profile-id" }, { status: 200 }),
);

/** Mock GET that returns a pre-populated profile. */
const populatedProfileHandler = http.get("/api/v1/profile", () =>
  HttpResponse.json(
    {
      ageBand: "adult",
      biologicalSex: "female",
      chronicConditions: ["Diabetes", "Asthma"],
    },
    { status: 200 },
  ),
);

/* ------------------------------------------------------------------ */
/*  Setup / Teardown                                                   */
/* ------------------------------------------------------------------ */

beforeEach(() => {
  useProfileStore.getState().reset();
});

afterEach(() => {
  cleanup();
});

/* ------------------------------------------------------------------ */
/*  Tests                                                              */
/* ------------------------------------------------------------------ */

describe("ProfilePage", () => {
  /* ---- Rendering ---- */

  it("renders the heading and optional-field notice", async () => {
    server.use(emptyProfileHandler, saveProfileHandler);
    renderPage();

    expect(
      await screen.findByRole("heading", { name: /your profile/i }),
    ).toBeInTheDocument();

    expect(screen.getByText(/all fields are/i)).toBeInTheDocument();
  });

  it("renders all three field groups with 'Why we ask' explanations", async () => {
    server.use(emptyProfileHandler, saveProfileHandler);
    renderPage();

    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.queryByText(/loading your profile/i)).not.toBeInTheDocument();
    });

    expect(screen.getByLabelText(/age range/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/biological sex/i)).toBeInTheDocument();
    expect(
      screen.getByRole("group", { name: /pre-existing conditions/i }),
    ).toBeInTheDocument();

    // "Why we ask" hints
    const hints = screen.getAllByText(/why we ask/i);
    expect(hints.length).toBe(3);
  });

  it("shows the mandatory medical disclaimer", async () => {
    server.use(emptyProfileHandler, saveProfileHandler);
    renderPage();

    await waitFor(() => {
      expect(screen.queryByText(/loading your profile/i)).not.toBeInTheDocument();
    });

    expect(
      screen.getByText(/this is not a medical diagnosis/i),
    ).toBeInTheDocument();
  });

  /* ---- Happy path: save valid profile ---- */

  it("saves a completed profile and shows success banner", async () => {
    server.use(emptyProfileHandler, saveProfileHandler);
    const user = userEvent.setup();
    renderPage();

    await waitFor(() => {
      expect(screen.queryByText(/loading your profile/i)).not.toBeInTheDocument();
    });

    // Fill age band
    const ageSelect = screen.getByLabelText(/age range/i);
    await user.selectOptions(ageSelect, "adult");

    // Fill biological sex
    const sexSelect = screen.getByLabelText(/biological sex/i);
    await user.selectOptions(sexSelect, "female");

    // Toggle a chronic condition
    const diabetesCheckbox = screen.getByRole("checkbox", {
      name: /diabetes/i,
    });
    await user.click(diabetesCheckbox);

    // Save
    const saveButton = screen.getByRole("button", { name: /save profile/i });
    await user.click(saveButton);

    // Success message
    await waitFor(() => {
      expect(
        screen.getByText(/profile saved successfully/i),
      ).toBeInTheDocument();
    });
  });

  /* ---- Edge case: empty / partial submission ---- */

  it("saves successfully with all fields empty", async () => {
    server.use(emptyProfileHandler, saveProfileHandler);
    const user = userEvent.setup();
    renderPage();

    await waitFor(() => {
      expect(screen.queryByText(/loading your profile/i)).not.toBeInTheDocument();
    });

    const saveButton = screen.getByRole("button", { name: /save profile/i });
    await user.click(saveButton);

    await waitFor(() => {
      expect(
        screen.getByText(/profile saved successfully/i),
      ).toBeInTheDocument();
    });
  });

  it("saves with only one field filled", async () => {
    server.use(emptyProfileHandler, saveProfileHandler);
    const user = userEvent.setup();
    renderPage();

    await waitFor(() => {
      expect(screen.queryByText(/loading your profile/i)).not.toBeInTheDocument();
    });

    const ageSelect = screen.getByLabelText(/age range/i);
    await user.selectOptions(ageSelect, "senior");

    const saveButton = screen.getByRole("button", { name: /save profile/i });
    await user.click(saveButton);

    await waitFor(() => {
      expect(
        screen.getByText(/profile saved successfully/i),
      ).toBeInTheDocument();
    });
  });

  /* ---- Edge case: pre-populated profile loads correctly ---- */

  it("loads existing profile data into the form", async () => {
    server.use(populatedProfileHandler, saveProfileHandler);
    renderPage();

    await waitFor(() => {
      expect(screen.queryByText(/loading your profile/i)).not.toBeInTheDocument();
    });

    const ageSelect = screen.getByLabelText(
      /age range/i,
    ) as HTMLSelectElement;
    expect(ageSelect.value).toBe("adult");

    const sexSelect = screen.getByLabelText(
      /biological sex/i,
    ) as HTMLSelectElement;
    expect(sexSelect.value).toBe("female");

    const diabetesCheckbox = screen.getByRole("checkbox", {
      name: /diabetes/i,
    }) as HTMLInputElement;
    expect(diabetesCheckbox.checked).toBe(true);

    const asthmaCheckbox = screen.getByRole("checkbox", {
      name: /asthma/i,
    }) as HTMLInputElement;
    expect(asthmaCheckbox.checked).toBe(true);
  });

  /* ---- Clear All resets the form ---- */

  it("clears all fields when Clear All is clicked", async () => {
    server.use(populatedProfileHandler, saveProfileHandler);
    const user = userEvent.setup();
    renderPage();

    await waitFor(() => {
      expect(screen.queryByText(/loading your profile/i)).not.toBeInTheDocument();
    });

    const clearButton = screen.getByRole("button", { name: /clear all/i });
    await user.click(clearButton);

    const ageSelect = screen.getByLabelText(
      /age range/i,
    ) as HTMLSelectElement;
    expect(ageSelect.value).toBe("");

    const sexSelect = screen.getByLabelText(
      /biological sex/i,
    ) as HTMLSelectElement;
    expect(sexSelect.value).toBe("");

    const checkboxes = screen.getAllByRole("checkbox") as HTMLInputElement[];
    for (const cb of checkboxes) {
      expect(cb.checked).toBe(false);
    }
  });

  /* ---- Failure case: network error on load ---- */

  it("shows an error when loading profile fails", async () => {
    server.use(
      http.get("/api/v1/profile", () =>
        HttpResponse.json(null, { status: 500 }),
      ),
      saveProfileHandler,
    );

    renderPage();

    await waitFor(() => {
      expect(screen.queryByText(/loading your profile/i)).not.toBeInTheDocument();
    });

    expect(
      screen.getByRole("alert"),
    ).toHaveTextContent(/could not load profile/i);
  });

  /* ---- Failure case: save fails ---- */

  it("shows error message when save fails", async () => {
    server.use(
      emptyProfileHandler,
      http.put("/api/v1/profile", () =>
        HttpResponse.json(null, { status: 500 }),
      ),
    );
    const user = userEvent.setup();
    renderPage();

    await waitFor(() => {
      expect(screen.queryByText(/loading your profile/i)).not.toBeInTheDocument();
    });

    const saveButton = screen.getByRole("button", { name: /save profile/i });
    await user.click(saveButton);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        /unable to save your profile/i,
      );
    });
  });

  /* ---- 404 fallback (S2-VIV-3 not merged yet) ---- */

  it("handles 404 on load gracefully (backend not ready)", async () => {
    server.use(
      http.get("/api/v1/profile", () =>
        HttpResponse.json(null, { status: 404 }),
      ),
      saveProfileHandler,
    );
    renderPage();

    await waitFor(() => {
      expect(screen.queryByText(/loading your profile/i)).not.toBeInTheDocument();
    });

    // Should render the form without error
    expect(screen.getByLabelText(/age range/i)).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("handles 404 on save gracefully (backend not ready)", async () => {
    server.use(
      emptyProfileHandler,
      http.put("/api/v1/profile", () =>
        HttpResponse.json(null, { status: 404 }),
      ),
    );
    const user = userEvent.setup();
    renderPage();

    await waitFor(() => {
      expect(screen.queryByText(/loading your profile/i)).not.toBeInTheDocument();
    });

    const saveButton = screen.getByRole("button", { name: /save profile/i });
    await user.click(saveButton);

    await waitFor(() => {
      expect(
        screen.getByText(/profile saved successfully/i),
      ).toBeInTheDocument();
    });
  });

  /* ---- Accessibility: back link ---- */

  it("renders a back-to-home link", async () => {
    server.use(emptyProfileHandler, saveProfileHandler);
    renderPage();

    await waitFor(() => {
      expect(screen.queryByText(/loading your profile/i)).not.toBeInTheDocument();
    });

    const backLink = screen.getByRole("link", { name: /back to home/i });
    expect(backLink).toBeInTheDocument();
    expect(backLink).toHaveAttribute("href", "/");
  });
});
