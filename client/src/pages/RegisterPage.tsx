
/**
 * @file Optional account registration page.
 * Owner: Rutva · Task: S2-RUT-1 · Issue: #180
 *
 * Registration does not automatically create an authenticated session.
 * Users can continue using the symptom checker as guests.
 */

import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuthStore } from "../stores/authStore";
import {
  ACCESSIBILITY_TOKENS,
  COLOR_TOKENS,
  SHADOW_TOKENS,
  TYPOGRAPHY_TOKENS,
} from "../theme/tokens";

/** Renders the optional account registration form. */
export default function RegisterPage(): React.JSX.Element {
  const navigate = useNavigate();
  const { register, status, errorMessage } = useAuthStore();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
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

  /** Renders an accessible password visibility control. */
  function passwordToggle(
    visible: boolean,
    onToggle: () => void,
    label: string,
  ): React.JSX.Element {
    return (
      <button
        type="button"
        onClick={onToggle}
        aria-label={visible ? `Hide ${label}` : `Show ${label}`}
        aria-pressed={visible}
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
        {visible ? "Hide" : "Show"}
      </button>
    );
  }

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
            aria-hidden="true"
            style={{ fontSize: "2rem", marginBottom: "2rem" }}
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
            Take a step towards informed health decisions.
          </h1>

          <p style={{ lineHeight: 1.8, opacity: 0.9 }}>
            Create an account to access your personal account experience.
            Sharing an account is optional, never a requirement for using
            the symptom checker.
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
            <strong>Your choice matters.</strong>
            <p style={{ marginBottom: 0 }}>
              You can always use the symptom checker without registering.
            </p>
          </div>
        </div>
      </section>

      {/* Registration form */}
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
            Create your account
          </h2>

          <p
            style={{
              color: COLOR_TOKENS.neutral.textSecondary,
              marginBottom: "2rem",
            }}
          >
            Enter your details to get started.
          </p>

          {success ? (
            <div role="status" aria-live="polite">
              <div
                style={{
                  padding: "1rem",
                  borderRadius: "0.65rem",
                  background: "#ecfdf5",
                  border: "1px solid #a7f3d0",
                  color: "#065f46",
                  lineHeight: 1.7,
                }}
              >
                <strong>Account created successfully!</strong>
                <p style={{ marginBottom: 0 }}>
                  Your account is ready. Please sign in to continue.
                </p>
              </div>

              <button
                type="button"
                onClick={() => navigate("/login")}
                style={{
                  width: "100%",
                  marginTop: "1.25rem",
                  padding: "0.9rem",
                  minHeight: ACCESSIBILITY_TOKENS.minTouchTarget,
                  border: "none",
                  borderRadius: "0.65rem",
                  background: COLOR_TOKENS.brand.primary,
                  color: "#ffffff",
                  fontSize: "1rem",
                  fontWeight: 700,
                  cursor: "pointer",
                }}
              >
                Go to Login
              </button>
            </div>
          ) : (
            <form onSubmit={(event) => void handleSubmit(event)} noValidate>
              <div style={{ marginBottom: "1.25rem" }}>
                <label htmlFor="register-email" style={labelStyle}>
                  Email address
                </label>
                <input
                  id="register-email"
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
                <label htmlFor="register-password" style={labelStyle}>
                  Password
                </label>

                <div style={{ position: "relative" }}>
                  <input
                    id="register-password"
                    name="password"
                    type={showPassword ? "text" : "password"}
                    autoComplete="new-password"
                    placeholder="Create a password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    style={{ ...inputStyle, paddingRight: "5rem" }}
                    disabled={isLoading}
                    minLength={8}
                    maxLength={128}
                    required
                  />
                  {passwordToggle(
                    showPassword,
                    () => setShowPassword((visible) => !visible),
                    "password",
                  )}
                </div>

                {password.length > 0 && (
                  <div
                    style={{ marginTop: "0.6rem" }}
                    aria-live="polite"
                  >
                    <div
                      style={{
                        display: "flex",
                        gap: "4px",
                        marginBottom: "0.35rem",
                      }}
                    >
                      {[1, 2, 3, 4, 5].map((level) => (
                        <span
                          key={level}
                          style={{
                            flex: 1,
                            height: "5px",
                            borderRadius: "5px",
                            background:
                              level <= passwordStrength
                                ? passwordStrength <= 2
                                  ? "#e11d48"
                                  : passwordStrength <= 4
                                    ? "#d97706"
                                    : "#059669"
                                : COLOR_TOKENS.neutral.border,
                          }}
                        />
                      ))}
                    </div>
                    <span
                      style={{
                        fontSize: "0.8rem",
                        color: COLOR_TOKENS.neutral.textSecondary,
                      }}
                    >
                      Password strength: {strengthLabel}
                    </span>
                  </div>
                )}

                <p
                  style={{
                    margin: "0.5rem 0 0",
                    fontSize: "0.8rem",
                    color: COLOR_TOKENS.neutral.textMuted,
                  }}
                >
                  Use between 8 and 128 characters.
                </p>
              </div>

              <div style={{ marginBottom: "1.25rem" }}>
                <label htmlFor="register-confirm-password" style={labelStyle}>
                  Confirm password
                </label>

                <div style={{ position: "relative" }}>
                  <input
                    id="register-confirm-password"
                    name="confirmPassword"
                    type={showConfirmPassword ? "text" : "password"}
                    autoComplete="new-password"
                    placeholder="Enter your password again"
                    value={confirmPassword}
                    onChange={(event) =>
                      setConfirmPassword(event.target.value)
                    }
                    style={{ ...inputStyle, paddingRight: "5rem" }}
                    disabled={isLoading}
                    required
                  />
                  {passwordToggle(
                    showConfirmPassword,
                    () =>
                      setShowConfirmPassword((visible) => !visible),
                    "confirm password",
                  )}
                </div>
              </div>

              {(validationError ||
                (status === "error" && errorMessage)) && (
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
                {isLoading ? "Creating account..." : "Create Account"}
              </button>
            </form>
          )}

          <p
            style={{
              textAlign: "center",
              marginTop: "1.5rem",
              color: COLOR_TOKENS.neutral.textSecondary,
            }}
          >
            Already have an account?{" "}
            <Link
              to="/login"
              style={{
                color: COLOR_TOKENS.brand.primary,
                fontWeight: 700,
              }}
            >
              Sign in
            </Link>
          </p>

          <Link
            to="/"
            style={{
              display: "block",
              textAlign: "center",
              marginTop: "1rem",
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
