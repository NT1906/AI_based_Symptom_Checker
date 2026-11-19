
/**
 * @file Optional login page for returning users.
 * Owner: Rutva · Task: S2-RUT-1 · Issue: #180
 *
 * Authentication is optional. Users can continue as guests without logging in.
 */

import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuthStore } from "../stores/authStore";
import {
  ACCESSIBILITY_TOKENS,
  COLOR_TOKENS,
  SHADOW_TOKENS,
  SPACING_TOKENS,
  TYPOGRAPHY_TOKENS,
} from "../theme/tokens";

/** Renders the optional login form. */
export default function LoginPage(): React.JSX.Element {
  const navigate = useNavigate();
  const { login, status, errorMessage } = useAuthStore();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
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

  const inputStyle: React.CSSProperties = {
    width: "100%",
    boxSizing: "border-box",
    padding: "0.85rem 1rem",
    border: `1px solid ${COLOR_TOKENS.neutral.borderStrong}`,
    borderRadius: "0.65rem",
    fontSize: "1rem",
    color: COLOR_TOKENS.neutral.textPrimary,
    background: COLOR_TOKENS.neutral.surface,
    outlineColor: COLOR_TOKENS.brand.primary,
    minHeight: ACCESSIBILITY_TOKENS.minTouchTarget,
  };

  const labelStyle: React.CSSProperties = {
    display: "block",
    marginBottom: "0.5rem",
    fontWeight: 600,
    color: COLOR_TOKENS.neutral.textPrimary,
  };

  return (
    <main
      style={{
        minHeight: "100vh",
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 420px), 1fr))",
        background: COLOR_TOKENS.neutral.background,
        fontFamily: TYPOGRAPHY_TOKENS.fontFamily,
      }}
    >
      {/* Brand panel */}
      <section
        style={{
          background:
            "linear-gradient(145deg, #115e59 0%, #0f766e 55%, #14b8a6 100%)",
          color: "#ffffff",
          padding: "clamp(2rem, 6vw, 5rem)",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          minHeight: "260px",
        }}
      >
        <div style={{ maxWidth: "480px", margin: "0 auto" }}>
          <div
            style={{
              fontSize: "2rem",
              marginBottom: "2rem",
            }}
            aria-hidden="true"
          >
            ✚
          </div>

          <p
            style={{
              fontSize: "0.85rem",
              fontWeight: 700,
              letterSpacing: "0.16em",
              textTransform: "uppercase",
              opacity: 0.85,
            }}
          >
            AI-Based Symptom Checker
          </p>

          <h1
            style={{
              fontSize: "clamp(2rem, 4vw, 3.2rem)",
              lineHeight: 1.15,
              margin: "1rem 0",
            }}
          >
            Your health journey starts with understanding.
          </h1>

          <p style={{ lineHeight: 1.8, opacity: 0.9 }}>
            Sign in to access your account and continue your health
            information journey.
          </p>

          <div
            style={{
              marginTop: "2.5rem",
              padding: "1rem",
              border: "1px solid rgba(255,255,255,0.3)",
              borderRadius: "1rem",
              background: "rgba(255,255,255,0.1)",
              lineHeight: 1.7,
            }}
          >
            <strong>Prefer not to sign in?</strong>
            <p style={{ marginBottom: 0 }}>
              No problem. You can use the symptom checker as a guest.
            </p>
          </div>
        </div>
      </section>

      {/* Login form */}
      <section
        style={{
          padding: "clamp(1.5rem, 5vw, 4rem)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div
          style={{
            width: "100%",
            maxWidth: "440px",
            background: COLOR_TOKENS.neutral.surface,
            padding: "clamp(1.5rem, 4vw, 2.5rem)",
            borderRadius: "1.25rem",
            boxShadow: SHADOW_TOKENS.lg,
            border: `1px solid ${COLOR_TOKENS.neutral.border}`,
          }}
        >
          <Link
            to="/"
            style={{
              color: COLOR_TOKENS.brand.primary,
              textDecoration: "none",
              fontSize: "0.9rem",
            }}
          >
            ← Back to Home
          </Link>

          <h2
            style={{
              fontSize: "2rem",
              margin: "2rem 0 0.5rem",
              color: COLOR_TOKENS.neutral.textPrimary,
            }}
          >
            Welcome back
          </h2>

          <p
            style={{
              color: COLOR_TOKENS.neutral.textSecondary,
              marginBottom: "2rem",
            }}
          >
            Sign in to your account.
          </p>

          <form onSubmit={(event) => void handleSubmit(event)} noValidate>
            <div style={{ marginBottom: "1.25rem" }}>
              <label htmlFor="login-email" style={labelStyle}>
                Email address
              </label>
              <input
                id="login-email"
                name="email"
                type="email"
                autoComplete="email"
                placeholder="you@example.com"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                style={inputStyle}
                disabled={isLoading}
                required
              />
            </div>

            <div style={{ marginBottom: "1.25rem" }}>
              <label htmlFor="login-password" style={labelStyle}>
                Password
              </label>

              <div style={{ position: "relative" }}>
                <input
                  id="login-password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  placeholder="Enter your password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  style={{ ...inputStyle, paddingRight: "5rem" }}
                  disabled={isLoading}
                  required
                />

                <button
                  type="button"
                  onClick={() => setShowPassword((visible) => !visible)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  aria-pressed={showPassword}
                  style={{
                    position: "absolute",
                    right: "0.75rem",
                    top: "50%",
                    transform: "translateY(-50%)",
                    border: "none",
                    background: "transparent",
                    color: COLOR_TOKENS.brand.primary,
                    cursor: "pointer",
                    fontWeight: 600,
                    minHeight: ACCESSIBILITY_TOKENS.minTouchTarget,
                  }}
                >
                  {showPassword ? "Hide" : "Show"}
                </button>
              </div>
            </div>

            {(validationError || (status === "error" && errorMessage)) && (
              <div
                role="alert"
                aria-live="polite"
                style={{
                  padding: "0.85rem",
                  borderRadius: "0.6rem",
                  background: "#fff1f2",
                  border: "1px solid #fecdd3",
                  color: "#9f1239",
                  marginBottom: "1rem",
                  fontSize: "0.9rem",
                }}
              >
                {validationError || errorMessage}
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading}
              aria-busy={isLoading}
              style={{
                width: "100%",
                padding: "0.9rem",
                minHeight: ACCESSIBILITY_TOKENS.minTouchTarget,
                border: "none",
                borderRadius: "0.65rem",
                background: isLoading
                  ? COLOR_TOKENS.neutral.borderStrong
                  : COLOR_TOKENS.brand.primary,
                color: "#ffffff",
                fontSize: "1rem",
                fontWeight: 700,
                cursor: isLoading ? "not-allowed" : "pointer",
                boxShadow: SHADOW_TOKENS.md,
              }}
            >
              {isLoading ? "Signing in..." : "Sign In"}
            </button>
          </form>

          <p
            style={{
              textAlign: "center",
              marginTop: "1.5rem",
              color: COLOR_TOKENS.neutral.textSecondary,
            }}
          >
            Don't have an account?{" "}
            <Link
              to="/register"
              style={{
                color: COLOR_TOKENS.brand.primary,
                fontWeight: 700,
              }}
            >
              Create account
            </Link>
          </p>

          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: SPACING_TOKENS[4],
              margin: "1.5rem 0",
              color: COLOR_TOKENS.neutral.textMuted,
              fontSize: "0.85rem",
            }}
          >
            <span style={{ flex: 1, height: "1px", background: COLOR_TOKENS.neutral.border }} />
            OR
            <span style={{ flex: 1, height: "1px", background: COLOR_TOKENS.neutral.border }} />
          </div>

          <Link
            to="/"
            style={{
              display: "block",
              textAlign: "center",
              padding: "0.85rem",
              border: `1px solid ${COLOR_TOKENS.neutral.borderStrong}`,
              borderRadius: "0.65rem",
              color: COLOR_TOKENS.neutral.textPrimary,
              textDecoration: "none",
              fontWeight: 600,
              minHeight: ACCESSIBILITY_TOKENS.minTouchTarget,
              boxSizing: "border-box",
            }}
          >
            Continue as Guest →
          </Link>

          <p
            style={{
              marginTop: "1.75rem",
              textAlign: "center",
              fontSize: "0.78rem",
              lineHeight: 1.6,
              color: COLOR_TOKENS.neutral.textMuted,
            }}
          >
            This tool provides informational guidance, not a medical diagnosis.
            Always consult a qualified healthcare professional.
          </p>
        </div>
      </section>
    </main>
  );
}
