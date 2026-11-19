/**
 * @file Profile page with optional health context fields and privacy explanations.
 * Owner: Dimple · Task: S2-DIM-1, S2-NIS-18 (#315 account settings), S2-NIS-21 (#322 redesign) · Requirements: FR-02
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
import { AlertCircle, ArrowLeft, CheckCircle2, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { AccountSettings } from "../components/account/AccountSettings";
import { AppLayout } from "../components/layout/AppLayout";
import {
  type AgeBand,
  type BiologicalSex,
  CHRONIC_CONDITION_OPTIONS,
  type ProfileData,
  getProfile,
  saveProfile,
} from "../services/profileApi";
import { useProfileStore } from "../stores/profileStore";

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

// The DR-01 disclaimer is shown by the shared site footer (AppLayout).

/** Shared classes for the native selects (kept native for accessibility). */
const SELECT_CLASS =
  "h-11 w-full rounded-lg border border-input bg-background px-3 text-sm text-foreground shadow-xs transition focus-visible:border-ring focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/40";

/**
 * One titled section of the health-context card.
 *
 * @param props - Section content.
 * @param props.children - Fields.
 * @returns The section.
 */
function Section({ children }: { children: React.ReactNode }): React.JSX.Element {
  return <div className="space-y-3 py-6 first:pt-0 last:pb-0">{children}</div>;
}

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

  /* ---------- Render ---------- */
  const isSaving = store.status === "loading";

  return (
    <AppLayout
      title="Your Profile"
      subtitle="Optional health context and account settings"
      showStartOver={false}
      narrow
    >
      <div className="mx-auto w-full max-w-3xl space-y-8">
        <div className="space-y-2">
          <Link
            to="/"
            aria-label="Back to home"
            className="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
          >
            <ArrowLeft className="size-4" aria-hidden="true" />
            Back to Home
          </Link>
          <p className="text-sm text-muted-foreground">
            All fields are <strong className="text-foreground">optional</strong>. Sharing health
            context helps our triage system provide more relevant information, but is never
            required.
          </p>
        </div>

        <section
          aria-labelledby="health-context-heading"
          className="rounded-xl border border-border bg-card p-6 text-card-foreground shadow-xs sm:p-8"
        >
          <h2 id="health-context-heading" className="text-lg font-semibold tracking-tight">
            Health context
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Used only to interpret your symptoms. It never changes the warning-sign checks.
          </p>

          {!isLoaded && (
            <div role="status" aria-label="Loading profile" className="mt-6 space-y-3">
              <span className="sr-only">Loading your profile…</span>
              <Skeleton className="h-11 w-full" />
              <Skeleton className="h-11 w-full" />
              <Skeleton className="h-24 w-full" />
            </div>
          )}

          {isLoaded && (
            <div className="mt-6 divide-y divide-border">
              {/* ---------- Age Band ---------- */}
              <Section>
                <label htmlFor="age-band" className="block text-sm font-medium">
                  Age Range
                </label>
                <p id="age-band-hint" className="text-sm text-muted-foreground">
                  <strong className="font-medium text-foreground">Why we ask:</strong> Certain
                  conditions are more common in specific age groups. This helps prioritise relevant
                  information. Your exact age is never collected.
                </p>
                <select
                  id="age-band"
                  aria-describedby="age-band-hint"
                  value={store.ageBand ?? ""}
                  onChange={(e) =>
                    store.setAgeBand((e.target.value || undefined) as AgeBand | undefined)
                  }
                  className={SELECT_CLASS}
                >
                  <option value="">— Select (optional) —</option>
                  {(Object.entries(AGE_BAND_LABELS) as [AgeBand, string][]).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </Section>

              {/* ---------- Biological Sex ---------- */}
              <Section>
                <label htmlFor="biological-sex" className="block text-sm font-medium">
                  Biological Sex
                </label>
                <p id="biological-sex-hint" className="text-sm text-muted-foreground">
                  <strong className="font-medium text-foreground">Why we ask:</strong> Some symptoms
                  present differently based on biological sex. This is used only for clinical
                  context and does not represent your gender identity.
                </p>
                <select
                  id="biological-sex"
                  aria-describedby="biological-sex-hint"
                  value={store.biologicalSex ?? ""}
                  onChange={(e) =>
                    store.setBiologicalSex(
                      (e.target.value || undefined) as BiologicalSex | undefined,
                    )
                  }
                  className={SELECT_CLASS}
                >
                  <option value="">— Select (optional) —</option>
                  {(Object.entries(BIOLOGICAL_SEX_LABELS) as [BiologicalSex, string][]).map(
                    ([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ),
                  )}
                </select>
              </Section>

              {/* ---------- Chronic Conditions ---------- */}
              <Section>
                <p className="text-sm font-medium">Pre-existing Conditions</p>
                <p id="conditions-hint" className="text-sm text-muted-foreground">
                  <strong className="font-medium text-foreground">Why we ask:</strong> Pre-existing
                  conditions can influence symptom interpretation. Select any that apply, or leave
                  blank if you prefer not to share.
                </p>
                <div
                  role="group"
                  aria-describedby="conditions-hint"
                  aria-label="Pre-existing conditions"
                  className="grid grid-cols-1 gap-2 sm:grid-cols-2"
                >
                  {CHRONIC_CONDITION_OPTIONS.map((condition) => {
                    const isChecked = store.chronicConditions.includes(condition);
                    return (
                      <label
                        key={condition}
                        className={cn(
                          "flex min-h-11 cursor-pointer items-center gap-3 rounded-lg border px-3 py-2 text-sm transition",
                          isChecked
                            ? "border-primary/40 bg-primary/10"
                            : "border-border hover:bg-accent/50",
                        )}
                      >
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => store.toggleCondition(condition)}
                          className="size-4 shrink-0 accent-primary"
                        />
                        <span>{condition}</span>
                      </label>
                    );
                  })}
                </div>
              </Section>
            </div>
          )}

          {isLoaded && (
            <>
              {/* ---------- Status feedback ---------- */}
              {store.status === "success" && (
                <div
                  role="status"
                  aria-live="polite"
                  className="mt-6 flex items-center gap-2 rounded-lg border border-success/30 bg-success/10 px-3 py-2.5 text-sm"
                >
                  <CheckCircle2 className="size-4 text-success" aria-hidden="true" />
                  Profile saved successfully.
                </div>
              )}
              {store.status === "error" && store.errorMessage && (
                <div
                  role="alert"
                  className="mt-6 flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2.5 text-sm text-destructive"
                >
                  <AlertCircle className="size-4" aria-hidden="true" />
                  {store.errorMessage}
                </div>
              )}

              {/* ---------- Actions ---------- */}
              <div className="mt-6 flex flex-col-reverse gap-2 border-t border-border pt-6 sm:flex-row sm:justify-end">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => store.reset()}
                  disabled={isSaving}
                  className="h-10 px-4"
                >
                  Clear All
                </Button>
                <Button
                  type="button"
                  onClick={() => void handleSave()}
                  disabled={isSaving}
                  aria-busy={isSaving}
                  className="h-10 px-5"
                >
                  {isSaving && <Loader2 className="size-4 animate-spin" aria-hidden="true" />}
                  {isSaving ? "Saving…" : "Save Profile"}
                </Button>
              </div>
            </>
          )}
        </section>

        {/* ---------- Account settings (logged-in only, S2-NIS-18) ---------- */}
        <AccountSettings />
      </div>
    </AppLayout>
  );
}
