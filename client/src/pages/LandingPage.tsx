/**
 * @file Landing page — entry point of the app with medical disclaimer and start flow.
 * Owner: Dimple · Task: S1-DIM-2 · Requirements: DR-01
 *
 * Responsibilities:
 * - Show the verbatim medical disclaimer before the first user action (DR-01).
 * - Gate the start flow behind the ConsentStep (S1-DIM-1, DR-08).
 * - Route to the assessment chat once both steps are complete.
 * - Modern, welcoming healthcare UI inspired by Ubie symptom checker.
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ConsentStep } from "../components/consent/ConsentStep";
import { useConsentStore } from "../stores/consentStore";
import { FeatureCardHover } from "../components/feature/FeatureCardHover";

/** Step the landing page can be in. */
type LandingStep = "disclaimer" | "consent" | "declined";

/** Curated starter symptom chips for quick exploration. */
const STARTER_SYMPTOMS = [
  "Headache",
  "Fever & Chills",
  "Cough",
  "Sore throat",
  "Abdominal pain",
  "Fatigue",
  "Nausea",
  "Skin rash",
];

/** Curated body area chips. */
const BODY_AREAS = ["Head & Neck", "Chest", "Abdomen", "Limbs & Joints", "Skin"];

/**
 * Landing page shown to every new session.
 *
 * Flow: disclaimer accepted → consent modal → assessment chat.
 * If the user already has a consentId in the store, they skip straight to chat.
 *
 * @returns The landing page element.
 */
export default function LandingPage() {
  const navigate = useNavigate();
  const consentId = useConsentStore((s) => s.consentId);

  // If already consented this session, send straight to chat
  if (consentId) {
    navigate("/chat", { replace: true });
    return null;
  }

  const [step, setStep] = useState<LandingStep>("disclaimer");

  const handleStart = () => setStep("consent");
  const handleConsented = () => navigate("/chat", { replace: true });
  const handleDeclined = () => setStep("declined");

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 antialiased selection:bg-teal-100 selection:text-teal-900">
      {/* 1. Header / Top Navigation */}
      <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3 sm:px-6">
          <div className="flex items-center gap-2.5">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-teal-600 text-lg text-white shadow-sm shadow-teal-600/30">
              🩺
            </span>
            <div>
              <p className="text-sm font-bold tracking-tight text-slate-900 sm:text-base">
                AI Symptom Checker
              </p>
              <p className="text-[11px] font-medium text-teal-700">
                Informational Triage Aid
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="hidden items-center gap-1.5 rounded-full border border-teal-200 bg-teal-50 px-3 py-1 text-xs font-semibold text-teal-800 sm:inline-flex">
              <span className="h-1.5 w-1.5 rounded-full bg-teal-600"></span>
              DPDP Act 2023 Compliant
            </span>
            <a
              href="tel:112"
              className="inline-flex items-center gap-1.5 rounded-lg border border-red-200 bg-red-50 px-3 py-1.5 text-xs font-bold text-red-700 transition hover:bg-red-100"
              aria-label="Call 112 for medical emergency"
            >
              <span>🚨</span>
              <span>Emergency 112</span>
            </a>
          </div>
        </div>
      </header>

      {/* 2. Main Content Container */}
      <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6 sm:py-12">
        {/* Hero Section */}
        <div className="text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3.5 py-1 text-xs font-medium text-slate-600 shadow-sm">
            <span>✨</span>
            <span>Free · 3-minute check · Non-diagnostic clinical aid</span>
          </div>

          <h1 className="mt-4 text-3xl font-extrabold tracking-tight text-slate-900 sm:text-5xl sm:leading-tight">
            Check your symptoms &amp; <br />
            <span className="bg-gradient-to-r from-teal-700 to-teal-500 bg-clip-text text-transparent">
              receive triage guidance
            </span>
          </h1>

          <p className="mx-auto mt-4 max-w-2xl text-base text-slate-600 sm:text-lg">
            Describe how you are feeling in plain words. Our clinical decision-support
            engine suggests appropriate care levels: self-care, doctor consultation, or urgent care.
          </p>

          {/* Primary Action Button */}
          {step === "disclaimer" && (
            <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
              <button
                type="button"
                onClick={handleStart}
                className="group inline-flex items-center justify-center gap-2.5 rounded-full bg-teal-600 px-8 py-4 text-base font-bold text-white shadow-lg shadow-teal-700/20 transition-all hover:bg-teal-700 hover:shadow-xl focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-600 active:scale-[0.99]"
              >
                <span>Start Symptom Check</span>
                <span className="transition-transform group-hover:translate-x-0.5">
                  →
                </span>
              </button>
            </div>
          )}

          <p className="mt-3 text-xs text-slate-500">
            By starting the check, you agree to review our terms and privacy notice before assessment.
          </p>
        </div>

        {/* Mandatory Medical Disclaimer Card (DR-01) */}
        <div
          role="note"
          aria-label="Medical disclaimer"
          className="mx-auto mt-10 max-w-2xl rounded-2xl border border-amber-200/90 bg-amber-50/90 p-5 shadow-sm sm:p-6"
        >
          <div className="flex items-start gap-3.5">
            <span className="text-xl" aria-hidden="true">
              ⚠️
            </span>
            <div className="space-y-2 text-left">
              <p className="text-xs font-bold uppercase tracking-wider text-amber-800">
                Important Medical Safety Disclaimer (DR-01)
              </p>
              <p className="text-sm leading-relaxed text-amber-950">
                This tool provides <strong>general health information only</strong>.
                It is <strong>not a medical diagnosis</strong>, prescription, or
                substitute for professional medical advice. Always consult a qualified
                healthcare professional for any medical concern.
              </p>
              <p className="text-sm font-semibold text-amber-950">
                In an emergency, call <strong>112</strong> (Unified Emergency) or
                go to the nearest emergency department immediately.
              </p>
            </div>
          </div>
        </div>

        {/* Visual Symptom Exploration Grid (Inspired by Ubie UI) */}
        <div className="mx-auto mt-12 max-w-3xl rounded-2xl border border-slate-200/80 bg-white p-6 shadow-sm sm:p-8">
          <div className="flex items-center justify-between border-b border-slate-100 pb-4">
            <div>
              <h2 className="text-base font-bold text-slate-900 sm:text-lg">
                Common Symptoms
              </h2>
              <p className="text-xs text-slate-500">
                Click any symptom to start with a focused query
              </p>
            </div>
            <span className="text-xs font-semibold text-teal-700">
              Quick explore
            </span>
          </div>

          <div className="mt-4 flex flex-wrap gap-2.5">
            {STARTER_SYMPTOMS.map((symptom) => (
              <button
                key={symptom}
                type="button"
                onClick={handleStart}
                className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-slate-50/80 px-4 py-2 text-xs font-semibold text-slate-700 transition hover:border-teal-500 hover:bg-teal-50 hover:text-teal-900 hover:scale-105 focus-visible:outline focus-visible:outline-2 focus-visible:outline-teal-600 active:scale-95 motion-reduce:transition-none motion-reduce:hover:scale-100 sm:text-sm"
              >
                <span>+</span>
                <span>{symptom}</span>
              </button>
            ))}
          </div>

          <div className="mt-6 border-t border-slate-100 pt-4">
            <p className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Browse by Body Region
            </p>
            <div className="mt-2.5 flex flex-wrap gap-2">
              {BODY_AREAS.map((area) => (
                <button
                  key={area}
                  type="button"
                  onClick={handleStart}
                  className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 transition hover:border-teal-500 hover:bg-teal-50 hover:text-teal-900"
                >
                  {area}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* 3-Step Journey / How It Works Cards */}
        <section className="mx-auto mt-12 max-w-4xl" aria-label="How it works">
          <h2 className="text-center text-xl font-bold text-slate-900 sm:text-2xl">
            How the Symptom Checker Works
          </h2>
          <p className="mx-auto mt-1.5 text-center text-xs text-slate-500 sm:text-sm">
            Safe, structured informational support in three straightforward steps
          </p>

          <div className="mt-6 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
  <FeatureCardHover
    title="AI‑Powered Symptom Analysis"
    description="Describe your symptoms and receive AI‑assisted guidance."
    icon="🧠"
    href="/assessment"
  />
  <FeatureCardHover
    title="Doctor Recommendations"
    description="Find relevant medical specialists based on your needs."
    icon="👩‍⚕️"
    href="/doctors"
  />
  <FeatureCardHover
    title="Risk Assessment"
    description="Clear, understandable risk guidance and next steps."
    icon="⚠️"
    href="/risk"
  />
  <FeatureCardHover
    title="Privacy & Consent"
    description="Explain consent, privacy, and responsible use of health information."
    icon="🔐"
    href="/privacy"
  />
</div>

        </section>

        {/* Step: consent modal dialog */}
        {step === "consent" && (
          <ConsentStep
            onConsented={handleConsented}
            onDeclined={handleDeclined}
          />
        )}

        {/* Step: user declined dialog */}
        {step === "declined" && (
          <div
            role="alert"
            className="mx-auto mt-8 w-full max-w-lg rounded-2xl border border-slate-200 bg-white p-6 text-center shadow-lg"
          >
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-xl">
              🛡️
            </div>
            <p className="mt-3 text-base font-bold text-slate-900">
              You need to agree to the terms to use this tool.
            </p>
            <p className="mt-1.5 text-xs text-slate-500">
              No health data has been collected or stored. You can go back anytime to review the terms.
            </p>
            <button
              type="button"
              onClick={() => setStep("disclaimer")}
              className="mt-5 rounded-full border border-slate-300 bg-white px-5 py-2 text-xs font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50"
            >
              Go back
            </button>
          </div>
        )}
      </main>

      {/* Persistent Footer with Mandatory Disclaimer (DR-01) */}
      <footer className="mt-16 border-t border-slate-200 bg-white px-4 py-8 text-center text-xs text-slate-500 sm:px-6">
        <div className="mx-auto max-w-3xl space-y-2">
          <p className="font-medium text-slate-600">
            This is not a medical diagnosis. Always consult a qualified healthcare professional.
          </p>
          <p className="text-[11px] text-slate-400">
            Emergency contacts: 112 (Unified Emergency) · 108 (Ambulance).
            Data processed ephemerally pursuant to DPDP Act 2023.
          </p>
        </div>
      </footer>
    </div>
  );
}
