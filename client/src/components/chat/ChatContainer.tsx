/**
 * @file Combines conversation messages, response states, and the composer.
 * Owner: Rutva · Task: S1-RUT-3 · Issue: #57
 */

import { useEffect, useRef, useState } from "react";
import type { AssessmentMessage } from "../../stores/assessmentStore";
import { MessageBubble } from "./MessageBubble";
import { MessageInput } from "./MessageInput";

type ChatContainerProps = {
  messages: AssessmentMessage[];
  onSend: (message: string) => void;
  disabled?: boolean;
  isTyping?: boolean;
  isLoading?: boolean;
  error?: string | null;
  onRetry?: () => void;
};

/**
 * Displays the conversation and its response, error, and network states.
 *
 * @param props Chat messages, submission callback, and response states.
 * @returns The complete chat conversation interface.
 */
export function ChatContainer({
  messages,
  onSend,
  disabled = false,
  isTyping = false,
  isLoading = false,
  error = null,
  onRetry,
}: ChatContainerProps) {
  const conversationEndRef = useRef<HTMLDivElement>(null);
  const [isOnline, setIsOnline] = useState(
    () => typeof navigator === "undefined" || navigator.onLine,
  );

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  useEffect(() => {
    conversationEndRef.current?.scrollIntoView?.({
      behavior: "smooth",
      block: "end",
    });
  }, [messages, isTyping, isLoading, error]);

  const composerDisabled = disabled || isLoading || !isOnline;

  return (
    <section className="flex h-full min-h-0 flex-col overflow-hidden rounded-xl border border-slate-200 bg-slate-50">
      {!isOnline && (
        <div
          role="alert"
          className="border-b border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-800"
        >
          You're offline. If this is an emergency, call 112.
        </div>
      )}

      <div
        role="log"
        aria-label="Assessment conversation"
        aria-live="polite"
        aria-relevant="additions"
        className="flex-1 space-y-4 overflow-y-auto p-4"
      >
        {messages.length === 0 ? (
          <p className="py-8 text-center text-sm text-slate-500">
            Tell me what you're experiencing, and I'll help you organize the information.
          </p>
        ) : (
          messages.map((message) => <MessageBubble key={message.id} message={message} />)
        )}

        {isTyping && (
          <div
            role="status"
            aria-label="Assistant is typing"
            className="flex items-center gap-2 px-3 py-2 text-sm text-slate-500"
          >
            <span className="flex gap-1" aria-hidden="true">
              <span className="h-2 w-2 animate-bounce rounded-full bg-slate-400" />
              <span className="h-2 w-2 animate-bounce rounded-full bg-slate-400 [animation-delay:150ms]" />
              <span className="h-2 w-2 animate-bounce rounded-full bg-slate-400 [animation-delay:300ms]" />
            </span>
            Assistant is typing...
          </div>
        )}

        {isLoading && (
          <p role="status" className="px-3 text-sm text-slate-500">
            Sending your message...
          </p>
        )}

        {error && (
          <div
            role="alert"
            className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800"
          >
            <p>{error}</p>
            {onRetry && (
              <button
                type="button"
                onClick={onRetry}
                className="rounded-lg bg-red-700 px-3 py-2 font-semibold text-white hover:bg-red-800 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
              >
                Retry
              </button>
            )}
          </div>
        )}

        <div ref={conversationEndRef} />
      </div>

      <MessageInput onSend={onSend} disabled={composerDisabled} />
    </section>
  );
}
