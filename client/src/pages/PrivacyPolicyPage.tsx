/**
 * @file Privacy Policy page presenting data practices, compliance, and user controls.
 * Owner: Dimple · Task: S2-DIM-3, S2-NIS-21 (#322 redesign) · Requirements: DR-06, DR-08
 *
 * Implements statutory notice requirements under India's DPDP Act 2023:
 * - Data inventory, processing purposes, and security safeguards.
 * - 24-hour guest retention TTL policy (DR-06).
 * - Zero persistence for uploaded symptom images (in-memory only).
 * - Self-service data export and permanent deletion controls.
 * - Active policy version display and mandatory medical disclaimers.
 */

import React from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Ban, Camera, History, Info, MessageSquareText } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { DataExportDelete } from "../components/privacy/DataExportDelete";
import { AppLayout } from "../components/layout/AppLayout";
import { CURRENT_POLICY_VERSION } from "../services/consentApi";

/** Mandatory medical disclaimer text per AI_RULES.md §2 rule 8. */
const DISCLAIMER_TEXT =
  "This is not a medical diagnosis. Always consult a qualified healthcare professional. This application is an informational triage aid and does not substitute for clinical evaluation.";

/** What we keep, for how long, and what we never collect. */
const INVENTORY = [
  {
    Icon: MessageSquareText,
    title: "Symptom conversations & triage output",
    tone: "default",
    text: (
      <>
        Text descriptions and confirmed symptoms are scrubbed of personal identifiers (names,
        phone numbers, emails) before processing. Unregistered guest sessions are{" "}
        <strong className="text-foreground">automatically purged after 24 hours</strong>.
      </>
    ),
  },
  {
    Icon: History,
    title: "Saved results (accounts only)",
    tone: "default",
    text: (
      <>
        If you are logged in, the result of each finished assessment is saved to your private
        history so you can reopen it. Guest results are never saved. Delete your account below to
        erase them.
      </>
    ),
  },
  {
    Icon: Camera,
    title: "Symptom photos (zero persistence)",
    tone: "default",
    text: (
      <>
        Photos uploaded for visual triage (e.g. rashes) are processed{" "}
        <strong className="text-foreground">strictly in volatile memory</strong> with EXIF
        metadata stripped. Images are <strong className="text-foreground">never stored</strong> on
        disk, in databases, or in backups, and are discarded immediately after analysis.
      </>
    ),
  },
  {
    Icon: Ban,
    title: "Strictly excluded data",
    tone: "danger",
    text: (
      <>
        We never collect government identifiers (Aadhaar, PAN), financial information,
        third-party medical records, or doctor directories.
      </>
    ),
  },
] as const;

/** Card wrapper for one policy section. */
function PolicySection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}): React.JSX.Element {
  return (
    <section className="space-y-4 rounded-xl border border-border bg-card p-6 text-card-foreground shadow-xs sm:p-8">
      <h2 className="text-lg font-semibold tracking-tight sm:text-xl">{title}</h2>
      {children}
    </section>
  );
}

/**
 * Full privacy policy document and self-service data management page.
 *
 * @returns Rendered Privacy Policy page element.
 */
export default function PrivacyPolicyPage(): React.JSX.Element {
  return (
    <AppLayout
      title="Privacy Policy & Data Rights"
      subtitle="Effective October 2026 · Digital Personal Data Protection Act, 2023 (India)"
      showStartOver={false}
      narrow
    >
      <div className="mx-auto w-full max-w-3xl space-y-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <Link
            to="/"
            aria-label="Back to home"
            className="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
          >
            <ArrowLeft className="size-4" aria-hidden="true" />
            Back to Home
          </Link>
          <Badge
            role="status"
            variant="outline"
            className="rounded-full border-primary/30 bg-primary/10 px-3 py-1 text-xs font-medium text-primary"
          >
            Policy Version {CURRENT_POLICY_VERSION}
          </Badge>
        </div>

        {/* Top disclaimer banner */}
        <div
          role="note"
          aria-label="Medical disclaimer"
          className="flex gap-3 rounded-xl border border-primary/20 bg-primary/5 p-4 text-sm"
        >
          <Info className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden="true" />
          <p className="text-muted-foreground">
            <strong className="font-medium text-foreground">Clinical triage notice: </strong>
            {DISCLAIMER_TEXT}
          </p>
        </div>

        <PolicySection title="1. Purpose & Statutory Principles">
          <p className="text-sm leading-relaxed text-muted-foreground">
            The <strong className="text-foreground">AI-Based Symptom Checker</strong> operates as an
            informational health-guidance aid. We enforce strict data minimization under
            India&apos;s{" "}
            <strong className="text-foreground">
              Digital Personal Data Protection Act, 2023 (DPDP Act 2023)
            </strong>
            . We collect only the minimum data necessary to conduct your symptom triage
            conversation.
          </p>
          <div className="rounded-lg bg-muted/60 p-4 text-sm">
            <p className="font-medium">Core guarantees</p>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-muted-foreground">
              <li>Your health data is never sold, monetized, or shared with third parties.</li>
              <li>Your personal conversations are never used to train public AI models.</li>
              <li>You may withdraw consent and erase your records at any time.</li>
            </ul>
          </div>
        </PolicySection>

        <PolicySection title="2. Data Inventory & Retention (DR-06)">
          <p className="text-sm text-muted-foreground">
            We categorize all processed information into clear boundaries:
          </p>
          <div className="space-y-3">
            {INVENTORY.map(({ Icon, title, text, tone }) => (
              <div
                key={title}
                className={
                  tone === "danger"
                    ? "flex gap-3 rounded-lg border border-danger/30 bg-danger/5 p-4"
                    : "flex gap-3 rounded-lg border border-border p-4"
                }
              >
                <Icon
                  className={tone === "danger" ? "mt-0.5 size-4 shrink-0 text-danger" : "mt-0.5 size-4 shrink-0 text-primary"}
                  aria-hidden="true"
                />
                <div className="space-y-1 text-sm">
                  <h3 className="font-medium">{title}</h3>
                  <p className="leading-relaxed text-muted-foreground">{text}</p>
                </div>
              </div>
            ))}
          </div>
        </PolicySection>

        <PolicySection title="3. Exercise Your Statutory Rights">
          <p className="-mt-2 text-sm text-muted-foreground">
            Under Sections 6(4) and 11 of the DPDP Act 2023, you hold the absolute right to download
            a complete copy of your records or permanently erase them at any time.
          </p>
          <DataExportDelete />
        </PolicySection>

        <div className="space-y-1 border-t border-border pt-5 pb-2 text-center text-xs leading-relaxed text-muted-foreground">
          <p>{DISCLAIMER_TEXT}</p>
          <p>
            Questions regarding privacy compliance? Contact our Data Protection Lead at{" "}
            <code className="rounded bg-muted px-1 py-0.5">privacy@symptomchecker.example</code>.
          </p>
        </div>
      </div>
    </AppLayout>
  );
}
