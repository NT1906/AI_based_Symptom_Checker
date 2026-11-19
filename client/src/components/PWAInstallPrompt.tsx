
/**
 * @file Progressive Web App installation prompt.
 * Owner: Rutva · Task: S2-RUT-3 · Issue: #182
 */
import { useEffect, useState } from "react";

interface BeforeInstallPromptEvent extends Event {
  readonly platforms: string[];
  prompt: () => Promise<void>;
  userChoice: Promise<{
    outcome: "accepted" | "dismissed";
    platform: string;
  }>;
}

export function PWAInstallPrompt() {
  const [installEvent, setInstallEvent] =
    useState<BeforeInstallPromptEvent | null>(null);

  useEffect(() => {
    const handleBeforeInstall = (event: Event) => {
      event.preventDefault();
      setInstallEvent(event as BeforeInstallPromptEvent);
    };

    const handleInstalled = () => {
      setInstallEvent(null);
    };

    window.addEventListener("beforeinstallprompt", handleBeforeInstall);
    window.addEventListener("appinstalled", handleInstalled);

    return () => {
      window.removeEventListener("beforeinstallprompt", handleBeforeInstall);
      window.removeEventListener("appinstalled", handleInstalled);
    };
  }, []);

  const handleInstall = async () => {
    if (!installEvent) return;

    await installEvent.prompt();
    await installEvent.userChoice;
    setInstallEvent(null);
  };

  if (!installEvent) return null;

  return (
    <div
      role="status"
      className="fixed bottom-4 left-4 right-4 z-40 mx-auto flex max-w-lg items-center justify-between gap-4 rounded-xl border border-slate-200 bg-white p-4 shadow-lg"
    >
      <p className="text-sm text-slate-800">
        Install this app for a better experience.
      </p>
      <div className="flex shrink-0 gap-2">
        <button
          type="button"
          onClick={() => setInstallEvent(null)}
          className="rounded-lg px-3 py-2 text-sm text-slate-600 hover:bg-slate-100"
        >
          Later
        </button>
        <button
          type="button"
          onClick={handleInstall}
          className="rounded-lg bg-teal-700 px-3 py-2 text-sm font-semibold text-white hover:bg-teal-800"
        >
          Install
        </button>
      </div>
    </div>
  );
}
