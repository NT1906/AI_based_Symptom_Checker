/**
 * @file Optional login page for returning users.
 * Owner: Rutva · Task: S2-RUT-1 · Issue: #180 · Redesign: Nisarg · S2-NIS-21 (#322)
 *
 * Authentication is optional. Users can continue as guests without logging in.
 */

import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AlertCircle, ArrowRight, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AuthLayout } from "../components/auth/AuthLayout";
import { PasswordInput } from "../components/auth/PasswordInput";
import { useAuthStore } from "../stores/authStore";

/** Renders the optional login form. */
export default function LoginPage(): React.JSX.Element {
  const navigate = useNavigate();
  const { login, status, errorMessage } = useAuthStore();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [validationError, setValidationError] = useState("");

  const isLoading = status === "loading";

  /** Validates and submits the login form. */
  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();
    setValidationError("");

    const normalizedEmail = email.trim().toLowerCase();

    if (!normalizedEmail || !password) {
      setValidationError("Please enter your email and password.");
      return;
    }

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalizedEmail)) {
      setValidationError("Please enter a valid email address.");
      return;
    }

    try {
      await login({ email: normalizedEmail, password });
      navigate("/");
    } catch {
      // The auth store exposes a user-friendly error message.
    }
  }

  const shownError = validationError || (status === "error" ? errorMessage : "");

  return (
    <AuthLayout title="Welcome back" description="Sign in to your account.">
      <form onSubmit={(event) => void handleSubmit(event)} noValidate className="space-y-5">
        <div className="space-y-2">
          <Label htmlFor="login-email">Email address</Label>
          <Input
            id="login-email"
            name="email"
            type="email"
            autoComplete="email"
            placeholder="you@example.com"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            disabled={isLoading}
            required
            className="h-11"
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="login-password">Password</Label>
          <PasswordInput
            id="login-password"
            name="password"
            autoComplete="current-password"
            placeholder="Enter your password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            disabled={isLoading}
            required
          />
        </div>

        {shownError && (
          <div
            role="alert"
            aria-live="polite"
            className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2.5 text-sm text-destructive"
          >
            <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
            {shownError}
          </div>
        )}

        <Button type="submit" disabled={isLoading} aria-busy={isLoading} className="h-11 w-full text-sm">
          {isLoading && <Loader2 className="size-4 animate-spin" aria-hidden="true" />}
          {isLoading ? "Signing in..." : "Sign In"}
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-muted-foreground">
        Don&apos;t have an account?{" "}
        <Link to="/register" className="font-medium text-primary underline-offset-4 hover:underline">
          Create account
        </Link>
      </p>

      <div className="my-6 flex items-center gap-3 text-xs text-muted-foreground">
        <span className="h-px flex-1 bg-border" />
        OR
        <span className="h-px flex-1 bg-border" />
      </div>

      <Button asChild variant="outline" className="h-11 w-full">
        <Link to="/">
          Continue as Guest
          <ArrowRight className="size-4" aria-hidden="true" />
        </Link>
      </Button>
    </AuthLayout>
  );
}
