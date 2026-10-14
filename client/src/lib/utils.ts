// src/lib/utils.ts
// Utility helpers for Tailwind class composition.
// We use `clsx` for conditional class handling and `twMerge` from `tailwind-merge`
// to intelligently resolve conflicting Tailwind utilities.

import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Merge Tailwind class strings safely.
 * - Accepts any arguments supported by `clsx` (strings, objects, arrays).
 * - Removes falsy values.
 * - Merges conflicting Tailwind utilities (e.g., `p-2` + `p-4` => `p-4`).
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
