
/**
 * @file Restores an unfinished assessment from the backend.
 * Owner: Rutva · Task: S2-RUT-3 · Issue: #182
 *
 * Only the assessment ID is read from sessionStorage.
 * Conversation content is fetched from the backend.
 */

import {
  getAssessment,
  getAssessmentMessages,
} from "./assessmentApi";
import {
  useAssessmentStore,
  type AssessmentMessage,
} from "../stores/assessmentStore";

/**
 * Restore an unfinished assessment and its server-side conversation.
 *
 * @returns Whether an unfinished assessment was successfully restored.
 */
export async function restoreUnfinishedAssessment(): Promise<boolean> {
  const assessmentId = useAssessmentStore.getState().assessmentId;

  if (!assessmentId) {
    return false;
  }

  try {
    const assessment = await getAssessment(assessmentId);

    if (
      assessment.id !== assessmentId ||
      assessment.state === "COMPLETED" ||
      assessment.state === "ERROR"
    ) {
      useAssessmentStore.getState().clearAssessment();
      return false;
    }

    const serverMessages = await getAssessmentMessages(assessmentId);

    const messages: AssessmentMessage[] = serverMessages
      .filter(
        (message): message is typeof message & {
          role: "user" | "assistant";
        } =>
          message.role === "user" || message.role === "assistant",
      )
      .map((message, index) => ({
        id: message.id ?? `${assessmentId}-${index}`,
        role: message.role,
        content: message.content,
      }));

    const store = useAssessmentStore.getState();

    store.setAssessment(assessment);
    store.clearMessages();
    messages.forEach((message) => {
      useAssessmentStore.getState().addMessage(message);
    });

    return true;
  } catch {
    // Keep the ID so the user can retry when the service is available.
    return false;
  }
}
