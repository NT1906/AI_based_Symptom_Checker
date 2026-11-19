/**
 * @file Privacy Policy page presenting data practices, compliance, and user controls.
 * Owner: Dimple · Task: S2-DIM-3 · Requirements: DR-06, DR-08
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
import { CURRENT_POLICY_VERSION } from "../services/consentApi";
import { DataExportDelete } from "../components/privacy/DataExportDelete";
import {
  COLOR_TOKENS,
  SHADOW_TOKENS,
} from "../theme/tokens";

/** Mandatory medical disclaimer text per AI_RULES.md §2 rule 8. */
const DISCLAIMER_TEXT =
  "This is not a medical diagnosis. Always consult a qualified healthcare professional. This application is an informational triage aid and does not substitute for clinical evaluation.";

/**
 * Full privacy policy document and self-service data management page.
 *
 * @returns Rendered Privacy Policy page element.
 */
export default function PrivacyPolicyPage(): React.JSX.Element {
  const cardStyle: React.CSSProperties = {
    background: COLOR_TOKENS.neutral.surface,
    border: `1px solid ${COLOR_TOKENS.neutral.border}`,
    borderRadius: "1rem",
    padding: "1.75rem",
    boxShadow: SHADOW_TOKENS.sm,
  };

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
          maxWidth: "800px",
          margin: "0 auto",
          display: "flex",
          flexDirection: "column",
          gap: "2rem",
        }}
      >
        {/* Navigation & Header */}
        <header className="space-y-3">
          <Link
            to="/"
            className="text-xs font-semibold text-teal-800 hover:text-teal-900 transition"
            aria-label="Back to home"
          >
            ← Back to Home
          </Link>

          <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
              Privacy Policy &amp; Data Rights
            </h1>
            <span
              role="status"
              className="inline-flex items-center rounded-full border border-teal-300 bg-teal-50 px-3 py-1 text-xs font-bold text-teal-800"
            >
              Policy Version {CURRENT_POLICY_VERSION}
            </span>
          </div>

          <p className="text-xs text-slate-500 sm:text-sm">
            Effective Date: October 2026 · Compliant with the Digital Personal Data
            Protection Act, 2023 (India).
          </p>
        </header>

        {/* Top Disclaimer Banner */}
        <div
          role="note"
          aria-label="Medical disclaimer"
          className="rounded-2xl border border-teal-200 bg-teal-50/70 p-4 text-xs text-slate-700 sm:text-sm"
        >
          <strong className="font-semibold text-teal-900">
            Clinical Triage Notice:{" "}
          </strong>
          {DISCLAIMER_TEXT}
        </div>

        {/* Section 1: Overview & DPDP Act Compliance */}
        <section style={cardStyle} className="space-y-3">
          <h2 className="text-lg font-bold text-slate-900 sm:text-xl">
            1. Purpose &amp; Statutory Principles
          </h2>
          <p className="text-xs leading-relaxed text-slate-600 sm:text-sm">
            The <strong>AI-Based Symptom Checker</strong> operates as an
            informational health-guidance aid. We enforce strict data minimization
            under India&apos;s <strong>Digital Personal Data Protection Act, 2023 (DPDP Act 2023)</strong>.
            We collect only the minimum data necessary to conduct your symptom triage
            conversation.
          </p>
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-3.5 text-xs text-slate-700 space-y-1">
            <p className="font-bold text-slate-900">Core Guarantees:</p>
            <ul className="list-disc pl-5 space-y-0.5">
              <li>Your health data is never sold, monetized, or shared with third parties.</li>
              <li>Your personal conversations are never used to train public AI models.</li>
              <li>You may withdraw consent and erase your records at any time.</li>
            </ul>
          </div>
        </section>

        {/* Section 2: Data Inventory & Retention */}
        <section style={cardStyle} className="space-y-4">
          <h2 className="text-lg font-bold text-slate-900 sm:text-xl">
            2. Data Inventory &amp; Retention (DR-06)
          </h2>
          <p className="text-xs text-slate-600 sm:text-sm leading-relaxed">
            We categorize all processed information into clear boundaries:
          </p>

          <div className="space-y-3 text-xs sm:text-sm">
            <div className="rounded-xl border border-slate-200 p-3.5 space-y-1">
              <h3 className="font-bold text-slate-900">
                💬 Symptom Conversations &amp; Triage Output
              </h3>
              <p className="text-slate-600">
                Text descriptions and confirmed symptoms are scrubbed of personal
                identifiers (names, phone numbers, emails) before processing.
                Unregistered guest sessions are <strong>automatically purged after 24 hours</strong>.
              </p>
            </div>

            <div className="rounded-xl border border-slate-200 p-3.5 space-y-1">
              <h3 className="font-bold text-slate-900">
                📷 Symptom Photos (Zero Persistence)
              </h3>
              <p className="text-slate-600">
                Photos uploaded for visual triage (e.g. rashes) are processed
                <strong> strictly in volatile memory</strong> with EXIF metadata
                stripped. Images are <strong>never stored</strong> on disk, in
                databases, or in backups, and are discarded immediately after analysis.
              </p>
            </div>

            <div className="rounded-xl border border-rose-200 bg-rose-50/30 p-3.5 space-y-1">
              <h3 className="font-bold text-rose-950">
                🚫 Strictly Excluded Data
              </h3>
              <p className="text-rose-900">
                We never collect government identifiers (Aadhaar, PAN), financial
                information, third-party medical records, or doctor directories.
              </p>
            </div>
          </div>
        </section>

        {/* Section 3: Interactive Privacy Controls (Export & Delete) */}
        <section style={cardStyle} className="space-y-4">
          <div className="border-b border-slate-100 pb-3">
            <h2 className="text-lg font-bold text-slate-900 sm:text-xl">
              3. Exercise Your Statutory Rights
            </h2>
            <p className="text-xs text-slate-600 sm:text-sm">
              Under Sections 6(4) and 11 of the DPDP Act 2023, you hold the absolute
              right to download a complete copy of your records or permanently erase
              them at any time.
            </p>
          </div>

          <DataExportDelete />
        </section>

        {/* Bottom Medical Disclaimer */}
        <footer className="text-center text-xs leading-relaxed text-slate-500 border-t border-slate-200 pt-4 pb-8">
          <p>{DISCLAIMER_TEXT}</p>
          <p className="mt-1">
            Questions regarding privacy compliance? Contact our Data Protection
            Lead at <code>privacy@symptomchecker.example</code>.
          </p>
        </footer>
      </div>
    </main>
  );
}
