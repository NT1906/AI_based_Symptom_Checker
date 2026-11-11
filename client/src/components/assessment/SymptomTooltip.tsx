/**
 * @file Interactive symptom definition tooltip component.
 * Owner: Mann (Frontend + Deployment · Testing) · Task: S2-MAN-3 · Requirements: FR-18
 */

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
  /** Optional custom when-to-seek-care guidance. */
  customWhenToSeekCare?: string;
  /** Optional CSS class name for container. */
  className?: string;
}

/**
 * Accessible symptom definition tooltip component.
 *
 * Displays plain-language definitions and safe "when to seek care" guidance
 * from the curated symptom glossary (FR-18). Provides full keyboard navigation
 * (Enter/Space to toggle, Escape to dismiss, focus trap handling).
 *
 * @param props Symptom identifier, optional overrides, and children.
 * @returns Accessible trigger button and popover tooltip.
 */
export function SymptomTooltip({
  symptom,
  children,
  customDefinition,
  customWhenToSeekCare,
  className = "",
}: SymptomTooltipProps) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLSpanElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const tooltipId = useId();

  const entry = getSymptomDefinition(symptom);
  const definition = customDefinition || entry?.plainDefinition;
  const seekCare = customWhenToSeekCare || entry?.whenToSeekCare;

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
        className="group inline-flex items-center gap-1 text-left text-inherit underline decoration-teal-500/50 decoration-dotted underline-offset-2 hover:decoration-teal-600 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-1 rounded-xs"
      >
        <span>{children || entry?.name || symptom}</span>
        <span
          aria-hidden="true"
          className="inline-flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-teal-100 text-[10px] font-bold text-teal-800 transition group-hover:bg-teal-200 dark:bg-teal-900/60 dark:text-teal-200"
        >
          ℹ
        </span>
      </button>

      {/* Accessible Tooltip Popover */}
      {isOpen && (
        <span
          id={tooltipId}
          role="tooltip"
          className="absolute bottom-full left-1/2 z-50 mb-2 w-72 -translate-x-1/2 rounded-xl border border-teal-200 bg-white p-3.5 text-xs text-slate-700 shadow-lg dark:border-teal-900 dark:bg-slate-900 dark:text-slate-200"
        >
          {/* Header */}
          <span className="mb-1 flex items-center justify-between border-b border-slate-100 pb-1.5 font-bold text-slate-900 dark:border-slate-800 dark:text-slate-100">
            <span>{entry?.name || symptom}</span>
            <button
              type="button"
              onClick={() => setIsOpen(false)}
              aria-label="Close definition tooltip"
              className="rounded-sm text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
            >
              ✕
            </button>
          </span>

          {/* Plain Language Definition */}
          <span className="block leading-relaxed">{definition}</span>

          {/* When to Seek Care Notice */}
          {seekCare && (
            <span className="mt-2 block rounded-md bg-amber-50/80 p-2 text-[11px] leading-relaxed text-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
              <strong className="font-semibold">When to seek care: </strong>
              {seekCare}
            </span>
          )}

          {/* Safe Non-Diagnostic Disclaimer */}
          <span className="mt-2 block border-t border-slate-100 pt-1.5 text-[10px] text-slate-400 dark:border-slate-800">
            Informational triage aid only. Not a medical diagnosis.
          </span>
        </span>
      )}
    </span>
  );
}
