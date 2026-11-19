/**
 * @file Optional account registration page.
 * Owner: Rutva · Task: S2-RUT-1 · Issue: #180 · Redesign: Nisarg · S2-NIS-21 (#322)
 *
 * Registration is optional. Users can always use the symptom checker as guests.
 */

import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AlertCircle, CheckCircle2, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { AuthLayout } from "../components/auth/AuthLayout";
import { PasswordInput } from "../components/auth/PasswordInput";
import { useAuthStore } from "../stores/authStore";

/** Colour of each filled strength bar, by strength label. */
const STRENGTH_COLOUR: Record<string, string> = {
  Weak: "bg-danger",
  Moderate: "bg-warning",
  Strong: "bg-success",
};

/** Renders the optional account registration form. */
export default function RegisterPage(): React.JSX.Element {
  const navigate = useNavigate();
  const { register, status, errorMessage } = useAuthStore();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [validationError, setValidationError] = useState("");
  const [success, setSuccess] = useState(false);

  const isLoading = status === "loading";

  const passwordStrength =
    password.length === 0
      ? 0
      : [
          password.length >= 8,
          /[A-Z]/.test(password),
          /[a-z]/.test(password),
          /\d/.test(password),
          /[^A-Za-z0-9]/.test(password),
        ].filter(Boolean).length;

  const strengthLabel =
    password.length === 0
      ? ""
      : passwordStrength <= 2
        ? "Weak"
        : passwordStrength <= 4
          ? "Moderate"
          : "Strong";

  /** Validates and submits a new account registration. */
  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();
    setValidationError("");
    setSuccess(false);

    const normalizedEmail = email.trim().toLowerCase();

    if (!normalizedEmail || !password || !confirmPassword) {
      setValidationError("Please complete all fields.");
      return;
    }

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalizedEmail)) {
      setValidationError("Please enter a valid email address.");
      return;
    }

    if (password.length < 8 || password.length > 128) {
      setValidationError("Password must be between 8 and 128 characters.");
      return;
    }

    if (password !== confirmPassword) {
      setValidationError("Your passwords do not match.");
      return;
    }

    try {
      await register({ email: normalizedEmail, password });
      setSuccess(true);
    } catch {
      // The auth store exposes a user-friendly error message.
    }
  }

  const shownError = validationError || (status === "error" ? errorMessage : "");

  return (
    <AuthLayout title="Create your account" description="Enter your details to get started.">
      {success ? (
        <div role="status" aria-live="polite" className="space-y-5">
          <div className="flex items-start gap-3 rounded-lg border border-success/30 bg-success/10 p-4 text-sm">
            <CheckCircle2 className="mt-0.5 size-5 shrink-0 text-success" aria-hidden="true" />
            <div>
              <strong className="font-medium">Account created successfully!</strong>
              <p className="mt-0.5 text-muted-foreground">
                Your account is ready. Please sign in to continue.
              </p>
            </div>
          </div>
          <Button type="button" onClick={() => navigate("/login")} className="h-11 w-full">
            Go to Login
          </Button>
        </div>
      ) : (
        <form onSubmit={(event) => void handleSubmit(event)} noValidate className="space-y-5">
          <div className="space-y-2">
            <Label htmlFor="register-email">Email address</Label>
            <Input
              id="register-email"
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
            <Label htmlFor="register-password">Password</Label>
            <PasswordInput
              id="register-password"
              name="password"
              autoComplete="new-password"
              placeholder="Create a password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              disabled={isLoading}
              minLength={8}
              maxLength={128}
              required
              aria-describedby="register-password-hint"
            />
            {password.length > 0 && (
              <div aria-live="polite" className="flex items-center gap-3 pt-1">
                <div className="flex flex-1 gap-1" aria-hidden="true">
                  {[1, 2, 3, 4, 5].map((level) => (
                    <span
                      key={level}
                      className={cn(
                        "h-1.5 flex-1 rounded-full bg-muted transition-colors",
                        level <= passwordStrength && STRENGTH_COLOUR[strengthLabel],
                      )}
                    />
                  ))}
                </div>
                <span className="text-xs text-muted-foreground">
                  Password strength: {strengthLabel}
                </span>
              </div>
            )}
            <p id="register-password-hint" className="text-xs text-muted-foreground">
              Use between 8 and 128 characters.
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="register-confirm-password">Confirm password</Label>
            <PasswordInput
              id="register-confirm-password"
              name="confirmPassword"
              autoComplete="new-password"
              placeholder="Enter your password again"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              disabled={isLoading}
              required
              toggleLabel="confirm password"
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

          <Button type="submit" disabled={isLoading} aria-busy={isLoading} className="h-11 w-full">
            {isLoading && <Loader2 className="size-4 animate-spin" aria-hidden="true" />}
            {isLoading ? "Creating account..." : "Create Account"}
          </Button>
        </form>
      )}

      <p className="mt-6 text-center text-sm text-muted-foreground">
        Already have an account?{" "}
        <Link to="/login" className="font-medium text-primary underline-offset-4 hover:underline">
          Sign in
        </Link>
      </p>
    </AuthLayout>
  );
}
