/**
 * @file Split layout for the login and register pages.
 * Owner: Nisarg · Task: S2-NIS-21 · Issue: #322 · Requirements: FR-01, NFR-06
 *
 * Brand panel (hidden on small screens) next to a centred form card. Guests are
 * reminded that an account is optional (idea §10).
 */
import { motion } from "motion/react";
import { Activity, ArrowLeft, History, ShieldCheck, UserRound } from "lucide-react";
import { GridBackground } from "@/components/aceternity/grid-background";
import { ThemeToggle } from "@/components/theme/ThemeToggle";
import { RouterLink } from "../layout/RouterLink";

/** Props for AuthLayout. */
type AuthLayoutProps = {
  /** Form heading, e.g. "Welcome back". */
  title: string;
  /** One line under the heading. */
  description: string;
  /** The form and its links. */
  children: React.ReactNode;
};

const BENEFITS = [
  { Icon: History, text: "Keep a private history of your results" },
  { Icon: UserRound, text: "Add optional health context to your profile" },
  { Icon: ShieldCheck, text: "Export or delete your data at any time" },
] as const;

/**
 * Two-column authentication layout.
 *
 * @param props - Layout content.
 * @returns The page.
 */
export function AuthLayout({ title, description, children }: AuthLayoutProps): React.JSX.Element {
  return (
    <main className="grid min-h-screen bg-background text-foreground lg:grid-cols-2">
      {/* Brand panel */}
      <section
        aria-label="About accounts"
        className="relative hidden overflow-hidden border-r border-border bg-gradient-to-br from-primary/15 via-background to-background p-10 lg:flex lg:flex-col"
      >
        <GridBackground />
        <RouterLink to="/" className="relative flex items-center gap-2.5 font-semibold tracking-tight">
          <span className="flex size-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Activity className="size-5" aria-hidden="true" />
          </span>
          Symptom Checker
        </RouterLink>
        <div className="relative mt-auto max-w-md">
          <p className="text-3xl font-semibold leading-tight tracking-tight">
            Your health journey starts with understanding.
          </p>
          <ul className="mt-8 space-y-3 text-sm text-muted-foreground">
            {BENEFITS.map(({ Icon, text }) => (
              <li key={text} className="flex items-center gap-3">
                <span className="flex size-8 items-center justify-center rounded-md bg-card text-primary shadow-xs">
                  <Icon className="size-4" aria-hidden="true" />
                </span>
                {text}
              </li>
            ))}
          </ul>
          <p className="mt-10 rounded-lg border border-border bg-card/70 p-4 text-sm backdrop-blur">
            <strong className="font-medium">Prefer not to sign in?</strong>{" "}
            <span className="text-muted-foreground">
              Every feature of the symptom check works as a guest.
            </span>
          </p>
        </div>
      </section>

      {/* Form panel */}
      <section className="flex flex-col px-4 py-6 sm:px-8">
        <div className="flex items-center justify-between">
          <RouterLink
            to="/"
            className="inline-flex items-center gap-1.5 rounded-md text-sm text-muted-foreground transition-colors hover:text-foreground"
          >
            <ArrowLeft className="size-4" aria-hidden="true" />
            Back to Home
          </RouterLink>
          <ThemeToggle />
        </div>
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="m-auto w-full max-w-sm py-10"
        >
          <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
          <p className="mt-1.5 text-sm text-muted-foreground">{description}</p>
          <div className="mt-8">{children}</div>
          <p className="mt-10 text-center text-xs text-muted-foreground">
            This tool provides informational guidance, not a medical diagnosis. Always consult a
            qualified healthcare professional.
          </p>
        </motion.div>
      </section>
    </main>
  );
}
