
/**
 * @file Service worker registration and update notification.
 * Owner: Rutva · Task: S2-RUT-3 · Issue: #182
 */

import { useRegisterSW } from "virtual:pwa-register/react";

/** Registers the service worker and prompts users when an update is available. */
export function PWAUpdatePrompt() {
  const {
    needRefresh: [needRefresh, setNeedRefresh],
    updateServiceWorker,
  } = useRegisterSW({
    onRegisterError(error) {
      console.error("Service worker registration failed:", error);
    },
  });

  if (!needRefresh) return null;

  return (
    <div
      role="status"
      className="fixed bottom-4 left-4 right-4 z-50 mx-auto flex max-w-lg items-center justify-between gap-4 rounded-xl border border-teal-200 bg-white p-4 shadow-lg"
    >
      <p className="text-sm text-slate-800">
        A new version is available.
      </p>
      <div className="flex shrink-0 gap-2">
        <button
          type="button"
          onClick={() => setNeedRefresh(false)}
          className="rounded-lg px-3 py-2 text-sm text-slate-600 hover:bg-slate-100"
        >
          Later
        </button>
        <button
          type="button"
          onClick={() => updateServiceWorker(true)}
          className="rounded-lg bg-teal-700 px-3 py-2 text-sm font-semibold text-white hover:bg-teal-800"
        >
          Update
        </button>
      </div>
    </div>
  );
}
