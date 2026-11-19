/**
 * @file Header account control: log-in links for guests, account menu for users.
 * Owner: Nisarg · Task: S2-NIS-15 · Issue: #312 · Requirements: FR-02, NFR-06
 *
 * Responsibilities:
 * - Guests (the default, idea §10) see "Log in" and "Sign up" links.
 * - Logged-in users see their email and a menu with My history, My profile, Privacy & data and Log out.
 * - Logging out clears the session, the in-progress assessment and cached queries, then returns home.
 * - Renders nothing outside a router, so layout-only tests keep working.
 */
import { useEffect, useId, useRef, useState } from "react";
import { Link, useInRouterContext, useNavigate } from "react-router-dom";
import { queryClient } from "../../lib/queryClient";
import { useAssessmentStore } from "../../stores/assessmentStore";
import { useAuthStore } from "../../stores/authStore";
import { useConsentStore } from "../../stores/consentStore";

/** Links shown in the logged-in account menu. */
const MENU_LINKS = [
  { to: "/history", label: "My history", icon: "🗂️" },
  { to: "/profile", label: "My profile", icon: "👤" },
  { to: "/privacy", label: "Privacy & data", icon: "🔐" },
] as const;

/**
 * First letter of an email address, used as the avatar.
 *
 * @param email - User email address.
 * @returns One upper-case character.
 */
export function avatarInitial(email: string): string {
  return (email.trim()[0] ?? "?").toUpperCase();
}

/**
 * Header account control that adapts to the session state.
 *
 * @returns The account control, or null outside a router.
 */
export function AccountMenu(): React.JSX.Element | null {
  if (!useInRouterContext()) return null;
  return <AccountMenuInRouter />;
}

/** Account control body; needs a router for links and navigation. */
function AccountMenuInRouter(): React.JSX.Element | null {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const status = useAuthStore((s) => s.status);
  const logout = useAuthStore((s) => s.logout);
  const [open, setOpen] = useState(false);
  const [logoutError, setLogoutError] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const menuId = useId();

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: PointerEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) setOpen(false);
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  // Why: while the session check runs, showing "Log in" would flash for
  // users who are in fact logged in.
  if (status === "idle" || (status === "loading" && !user)) return null;

  if (!user) {
    return (
      <nav aria-label="Account" className="flex items-center gap-1.5">
        <Link
          to="/login"
          className="inline-flex min-h-[44px] items-center rounded-lg px-3 py-2 text-xs font-semibold text-teal-800 transition hover:bg-teal-50 focus:outline-none focus:ring-2 focus:ring-teal-600 sm:text-sm"
        >
          Log in
        </Link>
        <Link
          to="/register"
          className="hidden min-h-[44px] items-center rounded-lg border border-teal-600 px-3 py-2 text-xs font-semibold text-teal-800 transition hover:bg-teal-50 focus:outline-none focus:ring-2 focus:ring-teal-600 sm:inline-flex sm:text-sm"
        >
          Sign up
        </Link>
      </nav>
    );
  }

  const handleLogout = async () => {
    setLogoutError(false);
    try {
      await logout();
    } catch {
      setLogoutError(true);
      return;
    }
    setOpen(false);
    useAssessmentStore.getState().clearAssessment();
    useConsentStore.getState().clearConsent();
    queryClient.clear();
    navigate("/", { replace: true });
  };

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={menuId}
        aria-label={`Account menu for ${user.email}`}
        onClick={() => setOpen((value) => !value)}
        className="inline-flex min-h-[44px] items-center gap-2 rounded-full border border-slate-200 bg-white py-1 pl-1 pr-3 text-xs font-semibold text-slate-700 shadow-xs transition hover:border-teal-500 focus:outline-none focus:ring-2 focus:ring-teal-600"
      >
        <span
          aria-hidden="true"
          className="flex h-8 w-8 items-center justify-center rounded-full bg-teal-700 text-sm font-bold text-white"
        >
          {avatarInitial(user.email)}
        </span>
        <span className="hidden max-w-[10rem] truncate sm:inline">{user.email}</span>
        <span aria-hidden="true" className="text-slate-400">
          ▾
        </span>
      </button>

      {open && (
        <div
          id={menuId}
          role="menu"
          aria-label="Account"
          className="absolute right-0 z-50 mt-2 w-64 overflow-hidden rounded-xl border border-slate-200 bg-white text-sm shadow-lg"
        >
          <div className="border-b border-slate-100 px-4 py-3">
            <p className="text-xs text-slate-500">Signed in as</p>
            <p className="truncate font-semibold text-slate-900">{user.email}</p>
          </div>
          {MENU_LINKS.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              role="menuitem"
              onClick={() => setOpen(false)}
              className="flex items-center gap-2.5 px-4 py-2.5 text-slate-700 transition hover:bg-teal-50 hover:text-teal-900 focus:bg-teal-50 focus:outline-none"
            >
              <span aria-hidden="true">{item.icon}</span>
              {item.label}
            </Link>
          ))}
          <button
            type="button"
            role="menuitem"
            onClick={() => void handleLogout()}
            disabled={status === "loading"}
            className="flex w-full items-center gap-2.5 border-t border-slate-100 px-4 py-2.5 text-left font-semibold text-rose-700 transition hover:bg-rose-50 focus:bg-rose-50 focus:outline-none disabled:opacity-60"
          >
            <span aria-hidden="true">↩</span>
            {status === "loading" ? "Logging out..." : "Log out"}
          </button>
          {logoutError && (
            <p role="alert" className="px-4 pb-3 text-xs text-rose-700">
              Could not log out. Please try again.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export default AccountMenu;
