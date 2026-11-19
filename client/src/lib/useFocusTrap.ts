/**
 * @file Accessible modal focus-trapping and keyboard interaction hook.
 * Owner: Dimple · Task: S2-DIM-5 · Requirements: NFR-06
 *
 * Implements W3C WAI-ARIA Authoring Practices Guide (APG) for Modal Dialogs:
 * - Traps Tab and Shift+Tab cycling within the dialog boundaries (WCAG 2.1 SC 2.1.2).
 * - Listens for Escape key to trigger cancellation/dismissal callbacks.
 * - Directs initial focus into the dialog on mount (WCAG 2.1 SC 2.4.3).
 * - Restores focus to the trigger element when the dialog unmounts.
 */

import { useEffect, useRef } from "react";

/** Query selector string targeting all standard focusable HTML elements. */
const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

/** Configuration options for the modal focus trap hook. */
export interface UseFocusTrapOptions {
  /** Whether the focus trap is currently active. Defaults to true. */
  isActive?: boolean;
  /** Optional callback invoked when the user presses the Escape key. */
  onEscape?: () => void;
  /** Optional reference to a specific element that should receive initial focus. */
  initialFocusRef?: React.RefObject<HTMLElement | null>;
  /** Whether to automatically move focus into the modal upon activation. Defaults to true. */
  autoFocus?: boolean;
}

/**
 * Traps keyboard focus within a modal container and handles Escape key dismissal.
 *
 * @param containerRef - Reference to the modal container element.
 * @param options - Configuration options for the focus trap.
 */
export function useFocusTrap(
  containerRef: React.RefObject<HTMLElement | null>,
  options: UseFocusTrapOptions = {},
): void {
  const {
    isActive = true,
    onEscape,
    initialFocusRef,
    autoFocus = true,
  } = options;

  // Persist callbacks to avoid unnecessary re-subscriptions
  const onEscapeRef = useRef(onEscape);
  useEffect(() => {
    onEscapeRef.current = onEscape;
  }, [onEscape]);

  useEffect(() => {
    if (!isActive) {
      return;
    }

    const container = containerRef.current;
    if (!container) {
      return;
    }

    // Record the element that had focus before the modal opened
    const previouslyFocusedElement = document.activeElement as HTMLElement | null;

    // Helper to query all currently focusable elements in the container
    const getFocusableElements = (): HTMLElement[] => {
      if (!containerRef.current) {
        return [];
      }
      const rawElements = Array.from(
        containerRef.current.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR),
      );
      return rawElements.filter(
        (el) =>
          !el.hasAttribute("disabled") &&
          el.getAttribute("aria-hidden") !== "true" &&
          el.style.display !== "none" &&
          el.style.visibility !== "hidden",
      );
    };

    // Set initial focus
    if (autoFocus) {
      const focusTarget =
        initialFocusRef?.current ||
        getFocusableElements()[0] ||
        container;

      if (focusTarget && typeof focusTarget.focus === "function") {
        focusTarget.focus();
      }
    }

    // Keyboard event handler for Tab cycling and Escape key
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        if (onEscapeRef.current) {
          event.preventDefault();
          onEscapeRef.current();
        }
        return;
      }

      if (event.key === "Tab") {
        const focusableElements = getFocusableElements();

        if (focusableElements.length === 0) {
          event.preventDefault();
          return;
        }

        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];

        if (event.shiftKey) {
          // Shift + Tab: wrap from first to last
          if (
            document.activeElement === firstElement ||
            document.activeElement === container
          ) {
            event.preventDefault();
            lastElement.focus();
          }
        } else {
          // Tab: wrap from last to first
          if (document.activeElement === lastElement) {
            event.preventDefault();
            firstElement.focus();
          }
        }
      }
    };

    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("keydown", handleKeyDown);

      // Restore focus to previous element when modal closes
      if (
        previouslyFocusedElement &&
        typeof previouslyFocusedElement.focus === "function" &&
        document.contains(previouslyFocusedElement)
      ) {
        previouslyFocusedElement.focus();
      }
    };
  }, [isActive, autoFocus, containerRef, initialFocusRef]);
}
