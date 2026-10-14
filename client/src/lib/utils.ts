/**
 * @file Utility helpers for Tailwind class composition.
 * Owner: Dimple · Task: S1-DIM-2 · Requirements: DR-01
 *
 * Uses `clsx` for conditional class handling and `twMerge` from `tailwind-merge`
 * to intelligently resolve conflicting Tailwind utilities.
 */

import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Merge Tailwind class strings safely.
 * - Accepts any arguments supported by `clsx` (strings, objects, arrays).
 * - Removes falsy values.
 * - Merges conflicting Tailwind utilities (e.g., `p-2` + `p-4` => `p-4`).
 *
 * @param inputs - Class values, objects, or arrays to compose.
 * @returns Merged class name string.
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

