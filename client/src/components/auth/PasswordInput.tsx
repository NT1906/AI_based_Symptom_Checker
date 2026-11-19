/**
 * @file Password field with an accessible show / hide control.
 * Owner: Nisarg · Task: S2-NIS-21 · Issue: #322 · Requirements: FR-01, NFR-06
 */
import { useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import { Input } from "@/components/ui/input";

/** Props for PasswordInput: native input props plus the label used by the toggle. */
type PasswordInputProps = Omit<React.ComponentProps<"input">, "type"> & {
  /** Word used in the toggle's label, e.g. "password" → "Show password". */
  toggleLabel?: string;
};

/**
 * Password input whose text can be revealed.
 *
 * @param props - Input props.
 * @returns The field with its toggle.
 */
export function PasswordInput({
  toggleLabel = "password",
  className,
  ...props
}: PasswordInputProps): React.JSX.Element {
  const [visible, setVisible] = useState(false);
  return (
    <div className="relative">
      <Input {...props} type={visible ? "text" : "password"} className={`h-11 pr-11 ${className ?? ""}`} />
      <button
        type="button"
        onClick={() => setVisible((value) => !value)}
        aria-label={visible ? `Hide ${toggleLabel}` : `Show ${toggleLabel}`}
        aria-pressed={visible}
        className="absolute inset-y-0 right-0 flex w-11 items-center justify-center rounded-r-lg text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        {visible ? <EyeOff className="size-4" aria-hidden="true" /> : <Eye className="size-4" aria-hidden="true" />}
      </button>
    </div>
  );
}
