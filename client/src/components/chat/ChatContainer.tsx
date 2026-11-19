/**
 * @file Combines conversation messages, response states, and the composer.
 * Owner: Rutva · Task: S1-RUT-3 · Issue: #57
 * Restyle (design tokens, lucide icons, dark mode): Nisarg · S2-NIS-22 (#323)
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
    <section className="flex h-full min-h-0 flex-col overflow-hidden rounded-xl border border-border bg-muted/60">
      {!isOnline && (
        <div
          role="alert"
          className="border-b border-danger/25 bg-danger/10 px-4 py-3 text-sm font-medium text-danger-strong"
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
          <p className="py-8 text-center text-sm text-muted-foreground">
            Tell me what you're experiencing, and I'll help you organize the information.
          </p>
        ) : (
          messages.map((message) => <MessageBubble key={message.id} message={message} />)
        )}

        {isTyping && (
          <div
            role="status"
            aria-label="Assistant is typing"
            className="flex items-center gap-2 px-3 py-2 text-sm text-muted-foreground"
          >
            <span className="flex gap-1" aria-hidden="true">
              <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground/30" />
              <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground/30 [animation-delay:150ms]" />
              <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground/30 [animation-delay:300ms]" />
            </span>
            Assistant is typing...
          </div>
        )}

        {isLoading && (
          <p role="status" className="px-3 text-sm text-muted-foreground">
            Sending your message...
          </p>
        )}

        {error && (
          <div
            role="alert"
            className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-danger/25 bg-danger/10 p-3 text-sm text-danger-strong"
          >
            <p>{error}</p>
            {onRetry && (
              <button
                type="button"
                onClick={onRetry}
                className="rounded-lg bg-danger px-3 py-2 font-semibold text-danger-foreground hover:bg-danger/90 focus:outline-none focus:ring-2 focus:ring-danger/40 focus:ring-offset-2"
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
