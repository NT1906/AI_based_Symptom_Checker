/**
 * @file Profile page with optional health context fields and privacy explanations.
 * Owner: Dimple · Task: S2-DIM-1 · Requirements: FR-02
 *
 * Every field is strictly optional. Explanatory "Why we ask" microcopy
 * helps users understand why each datum improves triage accuracy without
 * pressuring them to share personal information.
 *
 * Medical-safety: this page never diagnoses, prescribes, or stores data
 * outside the current session (DR-06). The mandatory disclaimer is shown
 * at the bottom (AI_RULES.md §2 rule 8).
 */

import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import {
  type AgeBand,
  type BiologicalSex,
  CHRONIC_CONDITION_OPTIONS,
  type ProfileData,
  getProfile,
  saveProfile,
} from "../services/profileApi";
import { useProfileStore } from "../stores/profileStore";
import {
  ACCESSIBILITY_TOKENS,
  COLOR_TOKENS,
  SHADOW_TOKENS,
} from "../theme/tokens";

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

/** Human-readable labels for the AgeBand enum. */
const AGE_BAND_LABELS: Record<AgeBand, string> = {
  child: "Child (0–12)",
  teen: "Teenager (13–17)",
  young_adult: "Young Adult (18–35)",
  adult: "Adult (36–64)",
  senior: "Senior (65+)",
};

/** Human-readable labels for the BiologicalSex enum. */
const BIOLOGICAL_SEX_LABELS: Record<BiologicalSex, string> = {
  female: "Female",
  male: "Male",
  other: "Other",
  prefer_not_to_say: "Prefer not to say",
};

/** Mandatory medical-safety disclaimer (AI_RULES.md §2, rule 8). */
const DISCLAIMER_TEXT =
  "This is not a medical diagnosis. Always consult a qualified healthcare professional.";

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

/**
 * Profile page allowing users to optionally provide health context.
 *
 * @returns The rendered profile page.
 */
export default function ProfilePage(): React.JSX.Element {
  const store = useProfileStore();
  const [isLoaded, setIsLoaded] = useState(false);

  /* ---------- Load existing profile on mount ---------- */
  useEffect(() => {
    let cancelled = false;

    async function load(): Promise<void> {
      store.setStatus("loading");
      try {
        const data: ProfileData = await getProfile();
        if (cancelled) return;

        if (data.ageBand) store.setAgeBand(data.ageBand);
        if (data.biologicalSex) store.setBiologicalSex(data.biologicalSex);
        if (data.chronicConditions) {
          for (const c of data.chronicConditions) {
            if (!store.chronicConditions.includes(c)) {
              store.toggleCondition(c);
            }
          }
        }
        store.setStatus("idle");
      } catch {
        if (!cancelled) store.setStatus("error", "Could not load profile.");
      } finally {
        if (!cancelled) setIsLoaded(true);
      }
    }

    void load();

    return () => {
      cancelled = true;
    };
    // Run only on mount
  }, []);

  /* ---------- Save handler ---------- */
  const handleSave = useCallback(async () => {
    store.setStatus("loading");
    try {
      await saveProfile({
        ageBand: store.ageBand,
        biologicalSex: store.biologicalSex,
        chronicConditions:
          store.chronicConditions.length > 0
            ? store.chronicConditions
            : undefined,
      });
      store.setStatus("success");
    } catch {
      store.setStatus(
        "error",
        "Unable to save your profile. Please try again.",
      );
    }
  }, [store]);

  /* ---------- Shared styles ---------- */
  const cardStyle: React.CSSProperties = {
    background: COLOR_TOKENS.neutral.surface,
    border: `1px solid ${COLOR_TOKENS.neutral.border}`,
    borderRadius: "0.75rem",
    padding: "1.5rem",
    boxShadow: SHADOW_TOKENS.sm,
  };

  const labelStyle: React.CSSProperties = {
    display: "block",
    fontWeight: 600,
    color: COLOR_TOKENS.neutral.textPrimary,
    marginBottom: "0.25rem",
  };

  const hintStyle: React.CSSProperties = {
    fontSize: "0.875rem",
    color: COLOR_TOKENS.neutral.textSecondary,
    marginBottom: "0.75rem",
    lineHeight: "1.25rem",
  };

  const selectStyle: React.CSSProperties = {
    width: "100%",
    padding: "0.625rem 0.75rem",
    border: `1px solid ${COLOR_TOKENS.neutral.borderStrong}`,
    borderRadius: "0.5rem",
    fontSize: "1rem",
    color: COLOR_TOKENS.neutral.textPrimary,
    background: COLOR_TOKENS.neutral.surface,
    outline: "none",
  };

  /* ---------- Render ---------- */
  return (
    <main
      style={{
        minHeight: "100vh",
        background: COLOR_TOKENS.neutral.background,
        padding: "2rem 1rem",
      }}
    >
      <div
        style={{
          maxWidth: "640px",
          margin: "0 auto",
          display: "flex",
          flexDirection: "column",
          gap: "1.5rem",
        }}
      >
        {/* ---------- Header ---------- */}
        <header>
          <Link
            to="/"
            style={{
              color: COLOR_TOKENS.brand.primary,
              fontSize: "0.875rem",
              textDecoration: "none",
            }}
            aria-label="Back to home"
          >
            ← Back to Home
          </Link>
          <h1
            style={{
              fontSize: "1.875rem",
              fontWeight: 700,
              color: COLOR_TOKENS.neutral.textPrimary,
              marginTop: "0.75rem",
            }}
          >
            Your Profile
          </h1>
          <p style={hintStyle}>
            All fields are <strong>optional</strong>. Sharing health context
            helps our triage system provide more relevant information, but is
            never required.
          </p>
        </header>

        {/* ---------- Loading skeleton ---------- */}
        {!isLoaded && (
          <div
            role="status"
            aria-label="Loading profile"
            style={{
              ...cardStyle,
              textAlign: "center",
              color: COLOR_TOKENS.neutral.textMuted,
            }}
          >
            Loading your profile…
          </div>
        )}

        {isLoaded && (
          <>
            {/* ---------- Age Band ---------- */}
            <fieldset style={{ ...cardStyle, border: "none" }}>
              <div style={cardStyle}>
                <label htmlFor="age-band" style={labelStyle}>
                  Age Range
                </label>
                <p id="age-band-hint" style={hintStyle}>
                  <strong>Why we ask:</strong> Certain conditions are more
                  common in specific age groups. This helps prioritise relevant
                  information. Your exact age is never collected.
                </p>
                <select
                  id="age-band"
                  aria-describedby="age-band-hint"
                  value={store.ageBand ?? ""}
                  onChange={(e) =>
                    store.setAgeBand(
                      (e.target.value || undefined) as
                        | AgeBand
                        | undefined,
                    )
                  }
                  style={selectStyle}
                  onFocus={(e) => {
                    e.currentTarget.style.boxShadow =
                      `0 0 0 ${ACCESSIBILITY_TOKENS.focusOffset} ${COLOR_TOKENS.brand.primary}`;
                  }}
                  onBlur={(e) => {
                    e.currentTarget.style.boxShadow = "none";
                  }}
                >
                  <option value="">— Select (optional) —</option>
                  {(Object.entries(AGE_BAND_LABELS) as [AgeBand, string][]).map(
                    ([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ),
                  )}
                </select>
              </div>
            </fieldset>

            {/* ---------- Biological Sex ---------- */}
            <fieldset style={{ ...cardStyle, border: "none" }}>
              <div style={cardStyle}>
                <label htmlFor="biological-sex" style={labelStyle}>
                  Biological Sex
                </label>
                <p id="biological-sex-hint" style={hintStyle}>
                  <strong>Why we ask:</strong> Some symptoms present differently
                  based on biological sex. This is used only for clinical
                  context and does not represent your gender identity.
                </p>
                <select
                  id="biological-sex"
                  aria-describedby="biological-sex-hint"
                  value={store.biologicalSex ?? ""}
                  onChange={(e) =>
                    store.setBiologicalSex(
                      (e.target.value || undefined) as
                        | BiologicalSex
                        | undefined,
                    )
                  }
                  style={selectStyle}
                  onFocus={(e) => {
                    e.currentTarget.style.boxShadow =
                      `0 0 0 ${ACCESSIBILITY_TOKENS.focusOffset} ${COLOR_TOKENS.brand.primary}`;
                  }}
                  onBlur={(e) => {
                    e.currentTarget.style.boxShadow = "none";
                  }}
                >
                  <option value="">— Select (optional) —</option>
                  {(
                    Object.entries(BIOLOGICAL_SEX_LABELS) as [
                      BiologicalSex,
                      string,
                    ][]
                  ).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </div>
            </fieldset>

            {/* ---------- Chronic Conditions ---------- */}
            <fieldset style={{ ...cardStyle, border: "none" }}>
              <div style={cardStyle}>
                <legend style={labelStyle}>Pre-existing Conditions</legend>
                <p id="conditions-hint" style={hintStyle}>
                  <strong>Why we ask:</strong> Pre-existing conditions can
                  influence symptom interpretation. Select any that apply, or
                  leave blank if you prefer not to share.
                </p>
                <div
                  role="group"
                  aria-describedby="conditions-hint"
                  aria-label="Pre-existing conditions"
                  style={{
                    display: "grid",
                    gridTemplateColumns:
                      "repeat(auto-fill, minmax(180px, 1fr))",
                    gap: "0.5rem",
                  }}
                >
                  {CHRONIC_CONDITION_OPTIONS.map((condition) => {
                    const isChecked =
                      store.chronicConditions.includes(condition);
                    return (
                      <label
                        key={condition}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "0.5rem",
                          padding: "0.5rem 0.75rem",
                          borderRadius: "0.5rem",
                          cursor: "pointer",
                          border: `1px solid ${isChecked ? COLOR_TOKENS.brand.primary : COLOR_TOKENS.neutral.border}`,
                          background: isChecked
                            ? COLOR_TOKENS.brand.subtle
                            : COLOR_TOKENS.neutral.surface,
                          transition: "all 0.15s ease",
                          minHeight: ACCESSIBILITY_TOKENS.minTouchTarget,
                        }}
                      >
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => store.toggleCondition(condition)}
                          style={{
                            accentColor: COLOR_TOKENS.brand.primary,
                            width: "1.125rem",
                            height: "1.125rem",
                          }}
                        />
                        <span
                          style={{
                            fontSize: "0.9375rem",
                            color: COLOR_TOKENS.neutral.textPrimary,
                          }}
                        >
                          {condition}
                        </span>
                      </label>
                    );
                  })}
                </div>
              </div>
            </fieldset>

            {/* ---------- Status feedback ---------- */}
            {store.status === "success" && (
              <div
                role="status"
                aria-live="polite"
                style={{
                  padding: "0.75rem 1rem",
                  borderRadius: "0.5rem",
                  background: "#ecfdf5",
                  color: "#065f46",
                  fontWeight: 500,
                  border: "1px solid #a7f3d0",
                }}
              >
                ✓ Profile saved successfully.
              </div>
            )}

            {store.status === "error" && store.errorMessage && (
              <div
                role="alert"
                style={{
                  padding: "0.75rem 1rem",
                  borderRadius: "0.5rem",
                  background: "#fff1f2",
                  color: "#9f1239",
                  fontWeight: 500,
                  border: "1px solid #fecdd3",
                }}
              >
                {store.errorMessage}
              </div>
            )}

            {/* ---------- Actions ---------- */}
            <div
              style={{
                display: "flex",
                gap: "0.75rem",
                justifyContent: "flex-end",
              }}
            >
              <button
                type="button"
                onClick={() => store.reset()}
                disabled={store.status === "loading"}
                style={{
                  padding: "0.625rem 1.25rem",
                  borderRadius: "0.5rem",
                  border: `1px solid ${COLOR_TOKENS.neutral.borderStrong}`,
                  background: COLOR_TOKENS.neutral.surface,
                  color: COLOR_TOKENS.neutral.textSecondary,
                  cursor:
                    store.status === "loading" ? "not-allowed" : "pointer",
                  fontWeight: 500,
                  minHeight: ACCESSIBILITY_TOKENS.minTouchTarget,
                }}
              >
                Clear All
              </button>
              <button
                type="button"
                onClick={() => void handleSave()}
                disabled={store.status === "loading"}
                aria-busy={store.status === "loading"}
                style={{
                  padding: "0.625rem 1.5rem",
                  borderRadius: "0.5rem",
                  border: "none",
                  background:
                    store.status === "loading"
                      ? COLOR_TOKENS.neutral.borderStrong
                      : COLOR_TOKENS.brand.primary,
                  color: "#ffffff",
                  cursor:
                    store.status === "loading" ? "not-allowed" : "pointer",
                  fontWeight: 600,
                  minHeight: ACCESSIBILITY_TOKENS.minTouchTarget,
                }}
                onFocus={(e) => {
                  e.currentTarget.style.boxShadow =
                    `0 0 0 ${ACCESSIBILITY_TOKENS.focusOffset} ${COLOR_TOKENS.brand.primary}`;
                }}
                onBlur={(e) => {
                  e.currentTarget.style.boxShadow = "none";
                }}
              >
                {store.status === "loading" ? "Saving…" : "Save Profile"}
              </button>
            </div>

            {/* ---------- Disclaimer ---------- */}
            <p
              style={{
                fontSize: "0.8125rem",
                color: COLOR_TOKENS.neutral.textMuted,
                textAlign: "center",
                borderTop: `1px solid ${COLOR_TOKENS.neutral.border}`,
                paddingTop: "1rem",
              }}
            >
              {DISCLAIMER_TEXT}
            </p>
          </>
        )}
      </div>
    </main>
  );
}
