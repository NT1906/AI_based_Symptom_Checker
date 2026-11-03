
/**
 * @file Combines conversation messages and the message composer.
 * Owner: Rutva · Task: S1-RUT-1 · Requirements: idea §1, §2
 */

import { useEffect, useRef } from "react";
import type { AssessmentMessage } from "../../stores/assessmentStore";
import { MessageBubble } from "./MessageBubble";
import { MessageInput } from "./MessageInput";

type ChatContainerProps = {
  messages: AssessmentMessage[];
  onSend: (message: string) => void;
  disabled?: boolean;
};

/**
 * Displays the assessment conversation and keeps the latest message visible.
 *
 * @param props.messages Conversation messages to display.
 * @param props.onSend Callback for newly submitted messages.
 * @param props.disabled Whether the message composer is disabled.
 * @returns The complete chat conversation interface.
 */
export function ChatContainer({
  messages,
  onSend,
  disabled = false,
}: ChatContainerProps) {
  const conversationEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    conversationEndRef.current?.scrollIntoView?.({
      behavior: "smooth",
      block: "end",
    });
  }, [messages]);

  return (
    <section className="flex h-full min-h-0 flex-col overflow-hidden rounded-xl border border-slate-200 bg-slate-50">
      <div
        role="log"
        aria-label="Assessment conversation"
        aria-live="polite"
        aria-relevant="additions"
        className="flex-1 space-y-4 overflow-y-auto p-4"
      >
        {messages.length === 0 ? (
          <p className="py-8 text-center text-sm text-slate-500">
            Tell me what you're experiencing, and I'll help you organize the
            information.
          </p>
        ) : (
          messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))
        )}

        <div ref={conversationEndRef} />
      </div>

      <MessageInput onSend={onSend} disabled={disabled} />
    </section>
  );
}
