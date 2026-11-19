/**
 * @file Header control to switch between light, dark and system theme.
 * Owner: Nisarg · Task: S2-NIS-19 · Issue: #320 · Requirements: NFR-06
 */
import { Check, Monitor, Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useTheme } from "./ThemeProvider";
import type { ThemePreference } from "./theme";

const OPTIONS: { value: ThemePreference; label: string; Icon: typeof Sun }[] = [
  { value: "light", label: "Light", Icon: Sun },
  { value: "dark", label: "Dark", Icon: Moon },
  { value: "system", label: "System", Icon: Monitor },
];

/**
 * Icon button with a menu of theme options.
 *
 * @returns The theme toggle.
 */
export function ThemeToggle(): React.JSX.Element {
  const { preference, resolved, setPreference } = useTheme();
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" aria-label="Change theme" className="size-10">
          {resolved === "dark" ? <Moon className="size-[18px]" /> : <Sun className="size-[18px]" />}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-36">
        {OPTIONS.map(({ value, label, Icon }) => (
          <DropdownMenuItem key={value} onSelect={() => setPreference(value)}>
            <Icon className="size-4" aria-hidden="true" />
            {label}
            {preference === value && <Check className="ml-auto size-4" aria-label="selected" />}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
