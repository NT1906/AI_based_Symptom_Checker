/**
 * @file Interactive symptom definition tooltip component.
 * Owner: Mann (Frontend + Deployment · Testing) · Task: S2-MAN-3 · Requirements: FR-18
 * Restyle (design tokens, lucide icons, dark mode): Nisarg · S2-NIS-22 (#323)
 */

import { X } from "lucide-react";
import {
  type KeyboardEvent,
  useEffect,
  useId,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { getSymptomDefinition } from "./symptomGlossary";

/** Props for the SymptomTooltip component (FR-18). */
export interface SymptomTooltipProps {
  /** Symptom ID or name used for glossary lookup. */
  symptom: string;
  /** Optional custom trigger text or React node overriding default symptom label. */
  children?: ReactNode;
  /** Optional custom definition string overriding glossary default. */
  customDefinition?: string;
  /** Optional CSS class name for container. */
  className?: string;
}

/**
 * Accessible symptom definition tooltip component.
 *
 * Displays a plain-language definition from the curated symptom glossary
 * (FR-18). It gives no "when to seek care" advice: urgency comes only from the
 * deterministic risk engine, so the two can never disagree (AI_RULES.md §2.4). Provides full keyboard navigation
 * (Enter/Space to toggle, Escape to dismiss, focus trap handling).
 *
 * @param props Symptom identifier, optional overrides, and children.
 * @returns Accessible trigger button and popover tooltip.
 */
export function SymptomTooltip({
  symptom,
  children,
  customDefinition,
  className = "",
}: SymptomTooltipProps) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLSpanElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const tooltipId = useId();

  const entry = getSymptomDefinition(symptom);
  const definition = customDefinition || entry?.plainDefinition;

  // Handle outside clicks to close
  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (event: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  const handleKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (event.key === "Escape") {
      event.preventDefault();
      setIsOpen(false);
      triggerRef.current?.focus();
    }
  };

  // If no glossary entry or definition exists, render plain children or symptom name
  if (!definition) {
    return <span className={className}>{children || symptom}</span>;
  }

  return (
    <span
      ref={containerRef}
      className={`relative inline-flex items-center gap-1 ${className}`}
    >
      <button
        ref={triggerRef}
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        onKeyDown={handleKeyDown}
        aria-expanded={isOpen}
        aria-describedby={isOpen ? tooltipId : undefined}
        aria-label={`Definition for ${entry?.name || symptom}`}
        className="group inline-flex items-center gap-1 text-left text-inherit underline decoration-primary decoration-dotted underline-offset-2 hover:decoration-primary focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1 rounded-xs"
      >
        <span>{children || entry?.name || symptom}</span>
        <span
          aria-hidden="true"
          className="inline-flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-primary/15 text-[10px] font-bold text-primary-strong transition group-hover:bg-primary/25"
        >
          ℹ
        </span>
      </button>

      {/* Accessible Tooltip Popover */}
      {isOpen && (
        <span
          id={tooltipId}
          role="tooltip"
          className="absolute bottom-full left-1/2 z-50 mb-2 w-72 -translate-x-1/2 rounded-xl border border-primary/25 bg-card p-3.5 text-xs text-muted-foreground shadow-lg"
        >
          {/* Header */}
          <span className="mb-1 flex items-center justify-between border-b border-border pb-1.5 font-bold text-foreground">
            <span>{entry?.name || symptom}</span>
            <button
              type="button"
              onClick={() => setIsOpen(false)}
              aria-label="Close definition tooltip"
              className="rounded-sm text-muted-foreground hover:text-muted-foreground"
            >
              <X className="size-5" aria-hidden="true" />
            </button>
          </span>

          {/* Plain Language Definition */}
          <span className="block leading-relaxed">{definition}</span>

          {/* Safe Non-Diagnostic Disclaimer */}
          <span className="mt-2 block border-t border-border pt-1.5 text-[10px] text-muted-foreground">
            Informational triage aid only. Not a medical diagnosis.
          </span>
        </span>
      )}
    </span>
  );
}
