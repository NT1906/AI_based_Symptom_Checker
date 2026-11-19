/**
 * @file Header account control: log-in links for guests, account menu for users.
 * Owner: Nisarg · Task: S2-NIS-15, S2-NIS-19 · Issues: #312, #320 · Requirements: FR-02, NFR-06
 *
 * Responsibilities:
 * - Guests (the default, idea §10) see "Log in" and "Sign up" links.
 * - Logged-in users see their email and a menu with My history, My profile, Privacy & data and Log out.
 * - Logging out clears the session, the in-progress assessment and cached queries, then returns home.
 * - Renders nothing outside a router, so layout-only tests keep working.
 */
import { useState } from "react";
import { History, LogOut, ShieldCheck, UserRound } from "lucide-react";
import { Link, useInRouterContext, useNavigate } from "react-router-dom";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { queryClient } from "../../lib/queryClient";
import { useAssessmentStore } from "../../stores/assessmentStore";
import { useAuthStore } from "../../stores/authStore";
import { useConsentStore } from "../../stores/consentStore";

/** Links shown in the logged-in account menu. */
const MENU_LINKS = [
  { to: "/history", label: "My history", Icon: History },
  { to: "/profile", label: "My profile", Icon: UserRound },
  { to: "/privacy", label: "Privacy & data", Icon: ShieldCheck },
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

  // Why: while the session check runs, showing "Log in" would flash for
  // users who are in fact logged in.
  if (status === "idle" || (status === "loading" && !user)) return null;

  if (!user) {
    return (
      <nav aria-label="Account" className="flex items-center gap-1">
        <Button asChild variant="ghost" className="h-10">
          <Link to="/login">Log in</Link>
        </Button>
        <Button asChild variant="outline" className="hidden h-10 sm:inline-flex">
          <Link to="/register">Sign up</Link>
        </Button>
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
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          aria-label={`Account menu for ${user.email}`}
          className="h-10 gap-2 rounded-full pl-1 pr-1 sm:pr-3"
        >
          <Avatar className="size-8">
            <AvatarFallback className="bg-primary text-sm font-semibold text-primary-foreground">
              {avatarInitial(user.email)}
            </AvatarFallback>
          </Avatar>
          <span className="hidden max-w-[10rem] truncate text-sm font-medium sm:inline">
            {user.email}
          </span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-64">
        <DropdownMenuLabel className="font-normal">
          <span className="block text-xs text-muted-foreground">Signed in as</span>
          <span className="block truncate text-sm font-medium text-foreground">{user.email}</span>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        {MENU_LINKS.map(({ to, label, Icon }) => (
          <DropdownMenuItem key={to} asChild>
            <Link to={to}>
              <Icon className="size-4" aria-hidden="true" />
              {label}
            </Link>
          </DropdownMenuItem>
        ))}
        <DropdownMenuSeparator />
        <DropdownMenuItem
          variant="destructive"
          disabled={status === "loading"}
          onSelect={(event) => {
            // Keep the menu open so a failure can be shown in it.
            event.preventDefault();
            void handleLogout();
          }}
        >
          <LogOut className="size-4" aria-hidden="true" />
          {status === "loading" ? "Logging out..." : "Log out"}
        </DropdownMenuItem>
        {logoutError && (
          <p role="alert" className="px-2 pb-2 pt-1 text-xs text-destructive">
            Could not log out. Please try again.
          </p>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export default AccountMenu;
