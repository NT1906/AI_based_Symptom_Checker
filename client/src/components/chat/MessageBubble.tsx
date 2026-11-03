
/**
 * @file Displays an individual message in the assessment conversation.
 * Owner: Rutva · Task: S1-RUT-1 · Requirements: idea §1, §2
 */

import type { AssessmentMessage } from "../../stores/assessmentStore";

type MessageBubbleProps = {
  message: AssessmentMessage;
};

/**
 * Displays a user or assistant message with appropriate alignment and styling.
 *
 * @param props.message The message to display.
 * @returns An accessible message bubble.
 */
export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex w-full ${isUser ? "justify-end" : "justify-start"}`}>
      <article
        aria-label={isUser ? "Your message" : "Assistant message"}
        className={`max-w-[85%] rounded-2xl px-4 py-3 shadow-sm ${
          isUser
            ? "rounded-br-md bg-teal-700 text-white"
            : "rounded-bl-md border border-slate-200 bg-white text-slate-900"
        }`}
      >
        <p className="mb-1 text-xs font-semibold uppercase tracking-wide opacity-75">
          {isUser ? "You" : "AI Assistant"}
        </p>

        <p className="whitespace-pre-wrap break-words text-sm leading-relaxed">
          {message.content}
        </p>
      </article>
    </div>
  );
}
