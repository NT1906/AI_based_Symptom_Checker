/**
 * @file Account settings on the profile page: change password, export or delete the account.
 * Owner: Nisarg · Task: S2-NIS-18 · Issue: #315 · Requirements: FR-01, DR-06, NFR-06
 *
 * Responsibilities:
 * - Let a logged-in user change their password (current password required).
 * - Offer the DPDP data export and permanent account deletion (privacy panel), then return home.
 * - Render nothing for guests.
 */
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { AuthApiError, changePassword } from "../../services/authApi";
import { useAuthStore } from "../../stores/authStore";
import { DataExportDelete } from "../privacy/DataExportDelete";

/** Shortest password the server accepts. */
export const MIN_PASSWORD_LENGTH = 8;

/** Result of the last change-password attempt shown to the user. */
type Status = { type: "success" | "error"; text: string } | null;

/**
 * Check the change-password form before it is sent.
 *
 * @param current - Current password.
 * @param next - New password.
 * @param confirm - New password typed again.
 * @returns A message to show, or null when the form is valid.
 */
export function validatePasswordChange(
  current: string,
  next: string,
  confirm: string,
): string | null {
  if (!current || !next || !confirm) return "Please fill in all three fields.";
  if (next.length < MIN_PASSWORD_LENGTH) {
    return `Your new password needs at least ${MIN_PASSWORD_LENGTH} characters.`;
  }
  if (next !== confirm) return "The new passwords do not match.";
  if (next === current) return "Choose a new password that differs from the current one.";
  return null;
}

/**
 * Message for a failed change-password request.
 *
 * @param error - The error thrown by the API call.
 * @returns A short, safe message.
 */
function failureMessage(error: unknown): string {
  if (error instanceof AuthApiError) {
    if (error.status === 401) return "Your session has ended. Please log in again.";
    if (error.status === 422) return error.message;
  }
  return "Could not change your password. Please try again.";
}

const inputClass =
  "mt-1 block min-h-[44px] w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-teal-600 focus:outline-none focus:ring-2 focus:ring-teal-600/30";

/**
 * Account settings for the logged-in user.
 *
 * @returns The settings, or null for guests.
 */
export function AccountSettings(): React.JSX.Element | null {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState<Status>(null);

  if (!user) return null;

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const problem = validatePasswordChange(current, next, confirm);
    if (problem) {
      setStatus({ type: "error", text: problem });
      return;
    }
    setSaving(true);
    setStatus(null);
    try {
      await changePassword({ currentPassword: current, newPassword: next });
      setCurrent("");
      setNext("");
      setConfirm("");
      setStatus({ type: "success", text: "Your password has been changed." });
    } catch (error) {
      setStatus({ type: "error", text: failureMessage(error) });
    } finally {
      setSaving(false);
    }
  };

  return (
    <section aria-labelledby="account-settings-heading" className="space-y-6">
      <div>
        <h2 id="account-settings-heading" className="text-xl font-bold text-slate-900">
          Account settings
        </h2>
        <p className="text-sm text-slate-600">
          Signed in as <strong>{user.email}</strong>
        </p>
      </div>

      <form
        onSubmit={(event) => void handleSubmit(event)}
        aria-labelledby="change-password-heading"
        className="space-y-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
        noValidate
      >
        <h3 id="change-password-heading" className="text-base font-bold text-slate-900">
          Change password
        </h3>
        <label className="block text-sm font-semibold text-slate-800">
          Current password
          <input
            type="password"
            autoComplete="current-password"
            value={current}
            onChange={(event) => setCurrent(event.target.value)}
            className={inputClass}
          />
        </label>
        <label className="block text-sm font-semibold text-slate-800">
          New password
          <input
            type="password"
            autoComplete="new-password"
            value={next}
            onChange={(event) => setNext(event.target.value)}
            className={inputClass}
            aria-describedby="new-password-hint"
          />
        </label>
        <p id="new-password-hint" className="-mt-2 text-xs text-slate-500">
          At least {MIN_PASSWORD_LENGTH} characters.
        </p>
        <label className="block text-sm font-semibold text-slate-800">
          Confirm new password
          <input
            type="password"
            autoComplete="new-password"
            value={confirm}
            onChange={(event) => setConfirm(event.target.value)}
            className={inputClass}
          />
        </label>
        {status && (
          <p
            role={status.type === "error" ? "alert" : "status"}
            className={
              status.type === "error" ? "text-sm text-rose-700" : "text-sm text-emerald-800"
            }
          >
            {status.text}
          </p>
        )}
        <button
          type="submit"
          disabled={saving}
          className="inline-flex min-h-[44px] items-center rounded-lg bg-teal-700 px-5 py-2 text-sm font-semibold text-white transition hover:bg-teal-800 disabled:opacity-60"
        >
          {saving ? "Saving..." : "Change password"}
        </button>
      </form>

      <DataExportDelete onDataDeleted={() => navigate("/", { replace: true })} />
    </section>
  );
}

export default AccountSettings;
