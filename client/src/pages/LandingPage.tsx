/**
 * @file Landing page — entry point of the app with medical disclaimer and start flow.
 * Owner: Dimple · Task: S1-DIM-2, S2-NIS-15 (#312), S2-NIS-20 (#321 redesign) · Requirements: DR-01, FR-02
 *
 * Responsibilities:
 * - Show the verbatim medical disclaimer before the first user action (DR-01).
 * - Gate the start flow behind the ConsentStep (S1-DIM-1, DR-08).
 * - Route to the assessment chat once both steps are complete; an already-consented session skips to it.
 * - Show the account control, and a welcome panel for logged-in users.
 * - Calm clinical design: shadcn/ui components, restrained Aceternity effects, dark mode.
 */

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { motion } from "motion/react";
import {
  ArrowRight,
  Brain,
  ClipboardCheck,
  FileDown,
  Lightbulb,
  Lock,
  MapPin,
  MessageSquareText,
  Phone,
  ShieldCheck,
  Siren,
  Sparkles,
  Stethoscope,
  TriangleAlert,
} from "lucide-react";
import { BentoGrid, BentoGridItem } from "@/components/aceternity/bento-grid";
import { GridBackground } from "@/components/aceternity/grid-background";
import { Spotlight } from "@/components/aceternity/spotlight";
import { TextGenerateEffect } from "@/components/aceternity/text-generate-effect";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { WelcomeBackPanel } from "../components/account/WelcomeBackPanel";
import { ConsentStep } from "../components/consent/ConsentStep";
import { SiteFooter } from "../components/layout/SiteFooter";
import { SiteHeader } from "../components/layout/SiteHeader";
import { getCurrentPolicyVersion } from "../services/consentApi";
import { useConsentStore } from "../stores/consentStore";

/** Step the landing page can be in. */
type LandingStep = "disclaimer" | "consent" | "declined";

/** Common symptoms shown as quick starting points. */
const STARTER_SYMPTOMS = [
  "Headache",
  "Fever & chills",
  "Cough",
  "Sore throat",
  "Abdominal pain",
  "Fatigue",
  "Nausea",
  "Skin rash",
];

/** The three steps of an assessment. */
const STEPS = [
  {
    Icon: MessageSquareText,
    title: "Describe how you feel",
    text: "Type your symptoms in your own words. A few short follow-up questions fill in what is missing.",
  },
  {
    Icon: ClipboardCheck,
    title: "Confirm your symptoms",
    text: "Check the list we understood, add anything we missed, and remove what does not fit.",
  },
  {
    Icon: Stethoscope,
    title: "Get clear guidance",
    text: "See whether self-care, a doctor's visit or urgent care fits best, and why.",
  },
] as const;

/** Small decorative header for a bento card. */
function CardVisual({ children }: { children: React.ReactNode }): React.JSX.Element {
  return (
    <div
      aria-hidden="true"
      className="flex min-h-32 flex-1 items-center justify-center rounded-lg border border-border/60 bg-gradient-to-br from-accent/70 via-background to-background p-4"
    >
      {children}
    </div>
  );
}

/** Fade-up reveal used for sections as they scroll into view. */
const reveal = {
  initial: { opacity: 0, y: 16 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: "-60px" },
  transition: { duration: 0.45, ease: [0.22, 1, 0.36, 1] },
} as const;

/**
 * Landing page shown to every new session.
 *
 * Flow: disclaimer accepted → consent modal → assessment chat.
 * A session with consent for the active policy resumes the chat on Start.
 *
 * @returns The landing page element.
 */
export default function LandingPage() {
  const navigate = useNavigate();
  const consentId = useConsentStore((s) => s.consentId);
  const policyVersion = useConsentStore((s) => s.policyVersion);
  const activePolicy = useQuery({
    queryKey: ["current-consent-policy"],
    queryFn: getCurrentPolicyVersion,
    enabled: Boolean(consentId),
  });
  const [step, setStep] = useState<LandingStep>("disclaimer");

  const hasActiveConsent =
    Boolean(consentId) &&
    activePolicy.isSuccess &&
    !activePolicy.isFetching &&
    policyVersion === activePolicy.data;

  // Why: the home page stays reachable mid-session (account menu, history);
  // a session that already consented goes straight back to the chat.
  const handleStart = () =>
    hasActiveConsent ? navigate("/chat") : setStep("consent");
  const handleConsented = () => navigate("/chat", { replace: true });
  const handleDeclined = () => setStep("declined");

  return (
    <div className="relative flex min-h-screen flex-col bg-background text-foreground antialiased">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-primary focus:px-4 focus:py-2 focus:text-primary-foreground"
      >
        Skip to main content
      </a>
      <SiteHeader />

      <main id="main-content" tabIndex={-1} className="flex-1 focus:outline-none">
        {/* Hero */}
        <section className="relative isolate overflow-hidden border-b border-border/60">
          <GridBackground />
          <Spotlight />
          <div className="relative mx-auto max-w-6xl px-4 pt-16 pb-16 text-center sm:px-6 sm:pt-24 sm:pb-20">
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4 }}
            >
              <Badge
                variant="outline"
                className="gap-1.5 rounded-full border-primary/25 bg-background/70 px-3 py-1 text-xs font-medium text-muted-foreground backdrop-blur"
              >
                <Sparkles className="size-3.5 text-primary" aria-hidden="true" />
                Free · about 3 minutes · Not a diagnosis
              </Badge>
            </motion.div>

            <h1 className="mx-auto mt-6 max-w-3xl text-4xl font-semibold tracking-tight text-balance sm:text-6xl sm:leading-[1.05]">
              <TextGenerateEffect words="Understand your symptoms." filter={false} duration={0.4} />
              <span className="block text-primary">
                <TextGenerateEffect words="Know what to do next." filter={false} duration={0.4} />
              </span>
            </h1>

            <motion.p
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.5 }}
              className="mx-auto mt-6 max-w-2xl text-base text-pretty text-muted-foreground sm:text-lg"
            >
              Describe how you feel in plain words. Our triage engine checks for warning signs
              first, then suggests whether self-care, a doctor&apos;s visit or urgent care fits
              best.
            </motion.p>

            {step !== "declined" && (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.65 }}
                className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row"
              >
                <Button
                  type="button"
                  size="lg"
                  onClick={handleStart}
                  className="group h-12 rounded-full px-7 text-base shadow-lg shadow-primary/20"
                >
                  Start Symptom Check
                  <ArrowRight
                    className="size-4 transition-transform group-hover:translate-x-0.5"
                    aria-hidden="true"
                  />
                </Button>
                <Button asChild variant="ghost" size="lg" className="h-12 rounded-full px-6 text-base">
                  <a href="#how-it-works">How it works</a>
                </Button>
              </motion.div>
            )}

            <p className="mt-4 text-xs text-muted-foreground">
              By starting the check, you agree to review our terms and privacy notice before
              assessment.
            </p>

            <ul className="mx-auto mt-10 flex max-w-3xl flex-wrap items-center justify-center gap-x-8 gap-y-3 text-sm text-muted-foreground">
              <li className="flex items-center gap-2">
                <Siren className="size-4 text-primary" aria-hidden="true" />
                Warning signs checked first
              </li>
              <li className="flex items-center gap-2">
                <Lightbulb className="size-4 text-primary" aria-hidden="true" />
                Explainable, rule-based triage
              </li>
              <li className="flex items-center gap-2">
                <ShieldCheck className="size-4 text-primary" aria-hidden="true" />
                Private by design (DPDP Act 2023)
              </li>
            </ul>
          </div>
        </section>

        <div className="mx-auto max-w-6xl space-y-20 px-4 py-14 sm:px-6 sm:py-20">
          <div className="space-y-6">
            <WelcomeBackPanel />

            {/* Step: user declined */}
            {step === "declined" && (
              <div
                role="alert"
                className="mx-auto w-full max-w-lg rounded-xl border border-border bg-card p-6 text-center shadow-sm"
              >
                <ShieldCheck className="mx-auto size-8 text-muted-foreground" aria-hidden="true" />
                <p className="mt-3 font-semibold">You need to agree to the terms to use this tool.</p>
                <p className="mt-1.5 text-sm text-muted-foreground">
                  No health data has been collected or stored. You can go back anytime to review
                  the terms.
                </p>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setStep("disclaimer")}
                  className="mt-5 h-10 rounded-full px-5"
                >
                  Go back
                </Button>
              </div>
            )}

            {/* Mandatory medical disclaimer (DR-01) */}
            <motion.div
              {...reveal}
              role="note"
              aria-label="Medical disclaimer"
              className="mx-auto flex max-w-3xl gap-4 rounded-xl border border-warning/40 bg-warning/10 p-5 sm:p-6"
            >
              <TriangleAlert className="mt-0.5 size-5 shrink-0 text-warning" aria-hidden="true" />
              <div className="space-y-2 text-left text-sm">
                <p className="font-semibold">Important medical safety notice</p>
                <p className="leading-relaxed text-muted-foreground">
                  This tool provides <strong className="text-foreground">general health information only</strong>.
                  It is <strong className="text-foreground">not a medical diagnosis</strong>, prescription, or
                  substitute for professional medical advice. Always consult a qualified healthcare
                  professional for any medical concern.
                </p>
                <p className="font-medium">
                  In an emergency, call <strong>112</strong> (Unified Emergency) or go to the nearest
                  emergency department immediately.
                </p>
              </div>
            </motion.div>
          </div>

          {/* How it works */}
          <section id="how-it-works" aria-labelledby="how-heading" className="scroll-mt-24">
            <motion.div {...reveal} className="mx-auto max-w-2xl text-center">
              <p className="text-sm font-medium text-primary">How it works</p>
              <h2 id="how-heading" className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">
                Three calm steps to a clear next step
              </h2>
            </motion.div>
            <ol className="mt-10 grid gap-4 md:grid-cols-3">
              {STEPS.map(({ Icon, title, text }, index) => (
                <motion.li
                  key={title}
                  {...reveal}
                  transition={{ ...reveal.transition, delay: index * 0.08 }}
                  className="relative rounded-xl border border-border bg-card p-6 shadow-xs"
                >
                  <div className="flex items-center gap-3">
                    <span className="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                      <Icon className="size-5" aria-hidden="true" />
                    </span>
                    <span className="text-xs font-medium text-muted-foreground">Step {index + 1}</span>
                  </div>
                  <h3 className="mt-4 font-semibold tracking-tight">{title}</h3>
                  <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{text}</p>
                </motion.li>
              ))}
            </ol>
          </section>

          {/* Features */}
          <section aria-labelledby="features-heading">
            <motion.div {...reveal} className="mx-auto max-w-2xl text-center">
              <p className="text-sm font-medium text-primary">Built for safety</p>
              <h2 id="features-heading" className="mt-2 text-3xl font-semibold tracking-tight sm:text-4xl">
                Careful by default, clear by design
              </h2>
              <p className="mt-3 text-muted-foreground">
                Language understanding helps you describe symptoms. Every medical decision comes from
                transparent rules you can review.
              </p>
            </motion.div>
            <motion.div {...reveal} className="mt-10">
              <BentoGrid>
                <BentoGridItem
                  className="md:col-span-2"
                  title="Understands plain language"
                  description="Say it the way you would to a friend. Symptoms, duration and severity are picked out for you to confirm."
                  icon={<Brain className="size-5 text-primary" aria-hidden="true" />}
                  header={
                    <CardVisual>
                      <div className="w-full max-w-sm space-y-2 text-left text-xs">
                        <p className="ml-auto w-fit rounded-2xl rounded-br-sm bg-primary px-3 py-2 text-primary-foreground">
                          Sore throat and fever since two days
                        </p>
                        <div className="flex flex-wrap gap-1.5">
                          {["Sore throat", "Fever", "2 days"].map((chip) => (
                            <span key={chip} className="rounded-full border border-border bg-card px-2.5 py-1">
                              {chip}
                            </span>
                          ))}
                        </div>
                      </div>
                    </CardVisual>
                  }
                />
                <BentoGridItem
                  title="Warning signs first"
                  description="Red flags such as chest pain with breathlessness always lead to urgent advice and 112."
                  icon={<Siren className="size-5 text-danger" aria-hidden="true" />}
                  header={
                    <CardVisual>
                      <span className="inline-flex items-center gap-2 rounded-full bg-danger/10 px-3 py-1.5 text-xs font-semibold text-danger">
                        <Phone className="size-3.5" /> Urgent · call 112
                      </span>
                    </CardVisual>
                  }
                />
                <BentoGridItem
                  title="Explainable results"
                  description="Each possible condition shows why it was suggested. No hidden scores."
                  icon={<Lightbulb className="size-5 text-primary" aria-hidden="true" />}
                />
                <BentoGridItem
                  title="The right specialist, nearby"
                  description="See which kind of doctor fits, then search for one on a map."
                  icon={<MapPin className="size-5 text-primary" aria-hidden="true" />}
                />
                <BentoGridItem
                  title="Your data, your control"
                  description="Use it as a guest, or keep a private history. Export or delete everything anytime."
                  icon={<Lock className="size-5 text-primary" aria-hidden="true" />}
                />
                <BentoGridItem
                  className="md:col-span-3"
                  title="Save, print and revisit"
                  description="Logged-in users can reopen past results and save any result as a PDF to show their doctor."
                  icon={<FileDown className="size-5 text-primary" aria-hidden="true" />}
                />
              </BentoGrid>
            </motion.div>
          </section>

          {/* Quick starting points */}
          <motion.section
            {...reveal}
            aria-labelledby="common-heading"
            className="rounded-2xl border border-border bg-card p-6 shadow-xs sm:p-8"
          >
            <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-end">
              <div>
                <h2 id="common-heading" className="text-lg font-semibold tracking-tight">
                  Common symptoms people check
                </h2>
                <p className="text-sm text-muted-foreground">Pick one to start; you can add more in the chat.</p>
              </div>
            </div>
            <div className="mt-5 flex flex-wrap gap-2">
              {STARTER_SYMPTOMS.map((symptom) => (
                <Button
                  key={symptom}
                  type="button"
                  variant="outline"
                  onClick={handleStart}
                  className="h-9 rounded-full px-4 transition hover:border-primary/40 hover:bg-accent hover:text-accent-foreground"
                >
                  {symptom}
                </Button>
              ))}
            </div>
          </motion.section>

          {/* Closing call to action */}
          <motion.section
            {...reveal}
            className="relative overflow-hidden rounded-2xl border border-primary/20 bg-gradient-to-br from-primary/10 via-card to-card p-8 text-center sm:p-12"
          >
            <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
              Not feeling well? Get guidance in about three minutes.
            </h2>
            <p className="mx-auto mt-3 max-w-xl text-muted-foreground">
              Severe chest pain, trouble breathing, fainting or heavy bleeding? Do not wait —
              call <a href="tel:112" className="font-semibold text-danger underline-offset-4 hover:underline">112</a> now.
            </p>
            {step !== "declined" && (
              <Button
                type="button"
                size="lg"
                onClick={handleStart}
                className="mt-7 h-12 rounded-full px-7 text-base"
              >
                Start now
                <ArrowRight className="size-4" aria-hidden="true" />
              </Button>
            )}
          </motion.section>
        </div>
      </main>

      <SiteFooter />

      {/* Step: consent modal dialog */}
      {step === "consent" && (
        <ConsentStep onConsented={handleConsented} onDeclined={handleDeclined} />
      )}
    </div>
  );
}
