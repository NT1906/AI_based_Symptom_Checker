/**
 * @file Vitest test setup.
 * Owner: Rutva · Task: S0-RUT-1 · Requirements: NFR-08, NFR-09
 * IntersectionObserver stand-in: Nisarg · Task: S2-NIS-20 (#321)
 */
import "@testing-library/jest-dom/vitest";
import { afterAll, afterEach, beforeAll } from "vitest";
import { server } from "./server";

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// jsdom has no IntersectionObserver; motion's whileInView needs one. This
// stand-in reports every element as visible so scroll reveals render at once.
if (typeof window !== "undefined" && !("IntersectionObserver" in window)) {
  class VisibleIntersectionObserver {
    readonly root = null;
    readonly rootMargin = "0px";
    readonly thresholds = [0];
    private readonly callback: IntersectionObserverCallback;
    constructor(callback: IntersectionObserverCallback) {
      this.callback = callback;
    }
    observe(target: Element): void {
      this.callback(
        [{ isIntersecting: true, target, intersectionRatio: 1 } as IntersectionObserverEntry],
        this as unknown as IntersectionObserver,
      );
    }
    unobserve(): void {}
    disconnect(): void {}
    takeRecords(): IntersectionObserverEntry[] {
      return [];
    }
  }
  Object.defineProperty(window, "IntersectionObserver", {
    writable: true,
    value: VisibleIntersectionObserver,
  });
}
