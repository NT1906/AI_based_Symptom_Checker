
/**
 * @file Displays an individual message in the assessment conversation.
 * Owner: Rutva · Task: S1-RUT-1 · Requirements: idea §1, §2
 * Restyle (design tokens, lucide icons, dark mode): Nisarg · S2-NIS-22 (#323)
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
        className={`max-w-[85%] rounded-xl px-4 py-3 shadow-sm ${
          isUser
            ? "rounded-br-md bg-primary text-primary-foreground"
            : "rounded-bl-md border border-border bg-card text-foreground"
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
