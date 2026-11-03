
/**
 * @file Provides the text input for the assessment conversation.
 * Owner: Rutva · Task: S1-RUT-1 · Requirements: idea §1, §2
 */

import { useState, type FormEvent, type KeyboardEvent } from "react";

type MessageInputProps = {
  onSend: (message: string) => void;
  disabled?: boolean;
};

/**
 * Provides a multiline message composer with keyboard and button submission.
 *
 * @param props.onSend Callback invoked with the submitted message.
 * @param props.disabled Whether message submission is temporarily disabled.
 * @returns An accessible message input form.
 */
export function MessageInput({
  onSend,
  disabled = false,
}: MessageInputProps) {
  const [value, setValue] = useState("");

  const submitMessage = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const message = value.trim();

    if (!message || disabled) {
      return;
    }

    onSend(message);
    setValue("");
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  };

  return (
    <form
      onSubmit={submitMessage}
      className="flex items-end gap-3 border-t border-slate-200 bg-white p-4"
    >
      <label htmlFor="assessment-message" className="sr-only">
        Type your message
      </label>

      <textarea
        id="assessment-message"
        name="message"
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Describe how you're feeling..."
        rows={1}
        maxLength={2000}
        disabled={disabled}
        className="max-h-32 min-h-11 flex-1 resize-y rounded-xl border border-slate-300 px-4 py-3 text-sm outline-none transition focus:border-teal-600 focus:ring-2 focus:ring-teal-100 disabled:cursor-not-allowed disabled:bg-slate-100"
      />

      <button
        type="submit"
        disabled={disabled || !value.trim()}
        className="rounded-xl bg-teal-700 px-5 py-3 text-sm font-semibold text-white transition hover:bg-teal-800 disabled:cursor-not-allowed disabled:opacity-50"
      >
        Send
      </button>
    </form>
  );
}
