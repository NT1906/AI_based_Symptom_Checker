/**
 * @file The assessment flow on /chat: conversation, symptom confirmation, result.
 * Owner: Nisarg (integration) · Task: S2-NIS-13 · Issue: #280 · Requirements: FR-01, FR-03, FR-06, FR-16, DR-01, DR-02
 * Restyle (design tokens, lucide icons, dark mode): Nisarg · S2-NIS-22 (#323)
 * Result opens scrolled to the top: Nisarg · S2-NIS-25 (#338)
 *
 * Connects the existing components to the assessment API:
 * 1. create the assessment with the user's consent ID;
 * 2. chat until the server asks for confirmation (or the user asks to review);
 * 3. the user confirms or edits the symptoms in `SymptomConfirmationCard`;
 * 4. analyze, then show `ResultPage` with the server's result only.
 *
 * Messages stay in memory (`assessmentStore`), never in browser storage
 * (AI_RULES.md §2.11). The risk level comes only from the server.
 */

import React, { useCallback, useEffect, useRef, useState } from "react";
import { SymptomConfirmationCard } from "../components/assessment/SymptomConfirmationCard";
import type { ConfirmedSymptom } from "../components/assessment/types";
import { ChatContainer } from "../components/chat/ChatContainer";
import { AppLayout } from "../components/layout/AppLayout";
import {
  AssessmentApiError,
  analyzeAssessment,
  createAssessment,
  getAssessmentResult,
  getAssessmentSymptoms,
  sendAssessmentMessage,
  updateAssessmentSymptoms,
} from "../services/assessmentApi";
import {
  type MappedResult,
  toConfirmedSymptom,
  toResultData,
  toSymptomUpdates,
} from "../services/assessmentMapping";
import { useAssessmentStore } from "../stores/assessmentStore";
import { ResultPage } from "./ResultPage";

/** Where the user is in the flow. */
type Phase = "starting" | "chatting" | "confirming" | "analyzing" | "result" | "expired";

/** User-facing error texts. Server error messages are never shown verbatim. */
export const ERROR_TEXT = {
  start: "We couldn't start your assessment. Please try again.",
  send: "Your message didn't go through. Please try again.",
  noSymptoms:
    "I couldn't pick out any symptoms yet. Please describe what you're feeling in a few words.",
  analyze: "We couldn't finish the analysis. Please try again.",
  expired:
    "This assessment is no longer available, for example after a server restart. Please start a new one.",
} as const;

/** Props for the ChatAssessmentPage component. */
export interface ChatAssessmentPageProps {
  /** Consent record ID from the consent step; required to create an assessment. */
  consentId: string;
}

/**
 * Runs one assessment from first message to result.
 *
 * @param props - The verified consent ID.
 * @returns The chat, the confirmation card or the result page.
 */
export function ChatAssessmentPage({
  consentId,
}: ChatAssessmentPageProps): React.ReactElement {
  const messages = useAssessmentStore((s) => s.messages);
  const assessmentId = useAssessmentStore((s) => s.assessmentId);
  const addMessage = useAssessmentStore((s) => s.addMessage);
  const setAssessment = useAssessmentStore((s) => s.setAssessment);
  const setAssessmentState = useAssessmentStore((s) => s.setAssessmentState);
  const clearAssessment = useAssessmentStore((s) => s.clearAssessment);

  const [phase, setPhase] = useState<Phase>(assessmentId ? "chatting" : "starting");
  const [error, setError] = useState<string | null>(null);
  const [isWaiting, setIsWaiting] = useState(false);
  const [symptoms, setSymptoms] = useState<ConfirmedSymptom[]>([]);
  const [result, setResult] = useState<MappedResult | null>(null);
  const serverSymptomIds = useRef<Set<string>>(new Set());
  const retry = useRef<(() => void) | null>(null);
  const creating = useRef(false);

  /** Shows a failure; a missing assessment (404) means it expired. */
  const fail = useCallback((err: unknown, text: string, again: (() => void) | null) => {
    if (err instanceof AssessmentApiError && err.status === 404) {
      setPhase("expired");
      setError(ERROR_TEXT.expired);
      retry.current = null;
      return;
    }
    setError(text);
    retry.current = again;
  }, []);

  const start = useCallback(async () => {
    if (creating.current) return;
    creating.current = true;
    setPhase("starting");
    setError(null);
    try {
      const created = await createAssessment({ consentId });
      setAssessment(created);
      setPhase("chatting");
    } catch (err) {
      fail(err, ERROR_TEXT.start, () => void start());
    } finally {
      creating.current = false;
    }
  }, [consentId, fail, setAssessment]);

  useEffect(() => {
    if (!assessmentId && phase === "starting") void start();
  }, [assessmentId, phase, start]);

  // The result replaces the chat on the same route, so the browser keeps the
  // chat's scroll position. Open the result (and a fresh start) at the top.
  useEffect(() => {
    if (phase === "result" || phase === "starting") window.scrollTo(0, 0);
  }, [phase]);

  const openConfirmation = useCallback(
    async (id: string) => {
      const list = await getAssessmentSymptoms(id);
      if (list.length === 0) {
        setError(ERROR_TEXT.noSymptoms);
        retry.current = null;
        return;
      }
      serverSymptomIds.current = new Set(
        list.map((s) => s.id).filter((v): v is string => Boolean(v)),
      );
      setSymptoms(list.map(toConfirmedSymptom));
      setPhase("confirming");
    },
    [],
  );

  const deliver = useCallback(
    async (text: string) => {
      if (!assessmentId) return;
      setIsWaiting(true);
      setError(null);
      try {
        const reply = await sendAssessmentMessage(assessmentId, { content: text });
        addMessage({
          id: reply.assistantMessage.id ?? `assistant-${Date.now()}`,
          role: "assistant",
          content: reply.assistantMessage.content,
        });
        setAssessmentState(reply.nextState);
        if (reply.nextState === "CONFIRMING") await openConfirmation(assessmentId);
      } catch (err) {
        if (err instanceof AssessmentApiError && err.status === 409) {
          // Why: the server wants the symptoms confirmed before more chat.
          await openConfirmation(assessmentId).catch((e: unknown) =>
            fail(e, ERROR_TEXT.send, null),
          );
        } else {
          fail(err, ERROR_TEXT.send, () => void deliver(text));
        }
      } finally {
        setIsWaiting(false);
      }
    },
    [addMessage, assessmentId, fail, openConfirmation, setAssessmentState],
  );

  const handleSend = (text: string) => {
    addMessage({ id: `user-${Date.now()}`, role: "user", content: text });
    void deliver(text);
  };

  const handleReview = () => {
    if (!assessmentId) return;
    setError(null);
    openConfirmation(assessmentId).catch((err: unknown) =>
      fail(err, ERROR_TEXT.send, handleReview),
    );
  };

  const handleConfirm = async (confirmed: ConfirmedSymptom[]) => {
    if (!assessmentId) return;
    setPhase("analyzing");
    setError(null);
    try {
      await updateAssessmentSymptoms(assessmentId, {
        symptoms: toSymptomUpdates(confirmed, serverSymptomIds.current),
      });
      await analyzeAssessment(assessmentId);
      const mapped = toResultData(await getAssessmentResult(assessmentId));
      setAssessmentState("COMPLETED");
      setResult(mapped);
      setPhase("result");
    } catch (err) {
      setSymptoms(confirmed);
      setPhase("confirming");
      fail(err, ERROR_TEXT.analyze, () => void handleConfirm(confirmed));
    }
  };

  const startOver = () => {
    clearAssessment();
    setResult(null);
    setSymptoms([]);
    serverSymptomIds.current = new Set();
    retry.current = null;
    setError(null);
    setPhase("starting");
  };

  if (phase === "result" && result) {
    return (
      <ResultPage
        result={result.data}
        emergencyNumber={result.emergencyNumber}
        onStartNewAssessment={startOver}
      />
    );
  }

  const hasUserMessage = messages.some((m) => m.role === "user");

  return (
    <AppLayout
      title="Symptom assessment"
      subtitle="Describe your symptoms in your own words"
      onStartOver={startOver}
      showStartOver={phase !== "starting"}
    >
      <div className="flex flex-col gap-6 pb-12">
        {phase === "expired" ? (
          <div role="alert" className="rounded-xl border border-warning/25 bg-warning/10 p-5 text-warning-strong">
            <p>{error}</p>
            <button
              type="button"
              onClick={startOver}
              className="mt-3 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
            >
              Start a new assessment
            </button>
          </div>
        ) : (
          <div className="h-[28rem]">
            <ChatContainer
              messages={messages}
              onSend={handleSend}
              disabled={phase !== "chatting" || isWaiting}
              isTyping={isWaiting}
              error={phase === "chatting" || phase === "starting" ? error : null}
              onRetry={retry.current ? () => retry.current?.() : undefined}
            />
          </div>
        )}

        {phase === "chatting" && hasUserMessage && !isWaiting && (
          <button
            type="button"
            onClick={handleReview}
            className="self-start rounded-lg border border-primary/60 px-4 py-2 text-sm font-semibold text-primary-strong hover:bg-primary/10 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
          >
            I'm done, review my symptoms
          </button>
        )}

        {(phase === "confirming" || phase === "analyzing") && (
          <>
            {error && (
              <div role="alert" className="rounded-xl border border-danger/25 bg-danger/10 p-4 text-sm text-danger-strong">
                <p>{error}</p>
                {retry.current && (
                  <button
                    type="button"
                    onClick={() => retry.current?.()}
                    className="mt-2 font-semibold underline"
                  >
                    Retry
                  </button>
                )}
              </div>
            )}
            <SymptomConfirmationCard
              key={symptoms.map((s) => s.id).join("|")}
              initialSymptoms={symptoms}
              onConfirm={(confirmed) => void handleConfirm(confirmed)}
              isSubmitting={phase === "analyzing"}
            />
          </>
        )}
      </div>
    </AppLayout>
  );
}

export default ChatAssessmentPage;
