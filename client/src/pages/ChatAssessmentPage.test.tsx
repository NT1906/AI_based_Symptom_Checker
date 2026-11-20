/**
 * @file Tests for the chat assessment flow on /chat.
 * Owner: Nisarg (integration) · Task: S2-NIS-13 · Issue: #280
 *
 * Covers the happy path (chat, confirm, result from the server), the urgent
 * result, and failures: start error, send error with retry, an expired
 * assessment, and the server asking for confirmation (409).
 * Scroll-to-top on result: Nisarg · S2-NIS-25 (#338)
 */

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "../services/assessmentApi";
import { AssessmentApiError } from "../services/assessmentApi";
import { useAssessmentStore } from "../stores/assessmentStore";
import type { AssessmentResult, SendMessageResponse, SymptomRead } from "../types";
import { ChatAssessmentPage, ERROR_TEXT } from "./ChatAssessmentPage";

vi.mock("../services/assessmentApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../services/assessmentApi")>();
  return {
    ...actual,
    createAssessment: vi.fn(),
    sendAssessmentMessage: vi.fn(),
    getAssessmentSymptoms: vi.fn(),
    updateAssessmentSymptoms: vi.fn(),
    analyzeAssessment: vi.fn(),
    getAssessmentResult: vi.fn(),
  };
});

const AID = "11111111-1111-4111-8111-111111111111";
const CONSENT = "22222222-2222-4222-8222-222222222222";
const SYMPTOM_ID = "33333333-3333-4333-8333-333333333333";

const reply = (content: string, nextState: SendMessageResponse["nextState"]): SendMessageResponse => ({
  message: { assessmentId: AID, content: "user text", role: "user" },
  assistantMessage: { id: `a-${content.length}`, assessmentId: AID, content, role: "assistant" },
  nextState,
});

const SYMPTOMS: SymptomRead[] = [
  { id: SYMPTOM_ID, name: "sore_throat", severity: "MODERATE", source: "AI_EXTRACTED" },
];

const RESULT: AssessmentResult = {
  assessmentId: AID,
  riskLevel: "SELF_CARE",
  conditions: [
    { name: "Sore throat (pharyngitis)", confidence: "LIKELY", rank: 1, why: "Because you reported sore throat." },
  ],
  guidance: ["Rest and drink plenty of fluids."],
  limitations: ["No physical examination was done."],
  disclaimer: "This is not a medical diagnosis. Always consult a qualified healthcare professional.",
};

function renderPage() {
  return render(
    <MemoryRouter>
      <ChatAssessmentPage consentId={CONSENT} />
    </MemoryRouter>,
  );
}

async function sendMessage(text: string) {
  const input = await screen.findByRole("textbox");
  await waitFor(() => expect(input).toBeEnabled());
  await userEvent.type(input, text);
  await userEvent.click(screen.getByRole("button", { name: "Send" }));
}

beforeEach(() => {
  useAssessmentStore.getState().clearAssessment();
  vi.mocked(api.createAssessment).mockResolvedValue({ id: AID, state: "START", consentId: CONSENT });
  vi.mocked(api.getAssessmentSymptoms).mockResolvedValue(SYMPTOMS);
  vi.mocked(api.updateAssessmentSymptoms).mockResolvedValue(SYMPTOMS);
  vi.mocked(api.analyzeAssessment).mockResolvedValue({ assessmentId: AID, state: "COMPLETED", resultAvailable: true });
  vi.mocked(api.getAssessmentResult).mockResolvedValue(RESULT);
});

afterEach(() => {
  vi.clearAllMocks();
});

describe("ChatAssessmentPage", () => {
  it("runs chat, confirmation and the server's result end to end", async () => {
    vi.mocked(api.sendAssessmentMessage).mockResolvedValue(
      reply("Please review and confirm your symptoms.", "CONFIRMING"),
    );
    renderPage();

    await sendMessage("I have a sore throat");

    expect(api.createAssessment).toHaveBeenCalledWith({ consentId: CONSENT });
    expect(api.sendAssessmentMessage).toHaveBeenCalledWith(AID, { content: "I have a sore throat" });
    expect(await screen.findByText("Please review and confirm your symptoms.")).toBeInTheDocument();
    expect(await screen.findByText(/1\. Sore throat/)).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /Confirm & Analyze Symptoms/i }));

    expect((await screen.findAllByText("Sore throat (pharyngitis)")).length).toBeGreaterThan(0);
    expect(api.updateAssessmentSymptoms).toHaveBeenCalledWith(AID, {
      symptoms: [expect.objectContaining({ id: SYMPTOM_ID, name: "sore_throat" })],
    });
    expect(screen.getByText("What to do next")).toBeInTheDocument();
    expect(screen.getByText("No physical examination was done.")).toBeInTheDocument();
    // Never the result page's built-in sample data.
    expect(screen.queryByText(/Migraine with Photophobia/)).not.toBeInTheDocument();
  });

  it("opens the result scrolled to the top, not at the chat's scroll position", async () => {
    vi.mocked(api.sendAssessmentMessage).mockResolvedValue(reply("Please confirm.", "CONFIRMING"));
    const scrollTo = vi.spyOn(window, "scrollTo");
    renderPage();
    await sendMessage("I have a sore throat");
    await screen.findByText(/1\. Sore throat/);
    scrollTo.mockClear();

    await userEvent.click(screen.getByRole("button", { name: /Confirm & Analyze Symptoms/i }));

    await screen.findAllByText("Sore throat (pharyngitis)");
    expect(scrollTo).toHaveBeenCalledWith(0, 0);
    scrollTo.mockRestore();
  });

  it("does not jump the page while the user is still chatting", async () => {
    vi.mocked(api.sendAssessmentMessage).mockResolvedValue(reply("How long?", "CLARIFYING"));
    renderPage();
    const input = await screen.findByRole("textbox");
    await waitFor(() => expect(input).toBeEnabled());
    const scrollTo = vi.spyOn(window, "scrollTo");

    await sendMessage("sore throat");
    await screen.findByText("How long?");

    expect(scrollTo).not.toHaveBeenCalled();
    scrollTo.mockRestore();
  });

  it("lets the user review symptoms before the server asks", async () => {
    vi.mocked(api.sendAssessmentMessage).mockResolvedValue(
      reply("How long have you had it?", "CLARIFYING"),
    );
    renderPage();
    await sendMessage("sore throat");

    await userEvent.click(await screen.findByRole("button", { name: /review my symptoms/i }));

    expect(await screen.findByText(/1\. Sore throat/)).toBeInTheDocument();
  });

  it("shows the emergency call first on an urgent result", async () => {
    vi.mocked(api.sendAssessmentMessage).mockResolvedValue(reply("Please confirm.", "CONFIRMING"));
    vi.mocked(api.getAssessmentResult).mockResolvedValue({
      ...RESULT,
      riskLevel: "URGENT",
      guidance: ["Call 112 now, or go to the nearest emergency department."],
      referral: { required: true, emergencyNumber: "112" },
    });
    renderPage();
    await sendMessage("severe chest pain");

    await userEvent.click(await screen.findByRole("button", { name: /Confirm & Analyze Symptoms/i }));

    expect(await screen.findByRole("link", { name: /Call emergency number 112 now/i })).toBeInTheDocument();
  });

  it("retries a failed message without repeating it in the conversation", async () => {
    vi.mocked(api.sendAssessmentMessage)
      .mockRejectedValueOnce(new AssessmentApiError(503))
      .mockResolvedValueOnce(reply("How long have you had it?", "CLARIFYING"));
    renderPage();
    await sendMessage("I have a headache");

    expect(await screen.findByText(ERROR_TEXT.send)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));

    expect(await screen.findByText("How long have you had it?")).toBeInTheDocument();
    expect(screen.getAllByText("I have a headache")).toHaveLength(1);
    expect(api.sendAssessmentMessage).toHaveBeenCalledTimes(2);
  });

  it("shows a retry when the assessment cannot be started", async () => {
    vi.mocked(api.createAssessment)
      .mockRejectedValueOnce(new AssessmentApiError(500))
      .mockResolvedValueOnce({ id: AID, state: "START", consentId: CONSENT });
    renderPage();

    expect(await screen.findByText(ERROR_TEXT.start)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));

    await waitFor(() => expect(api.createAssessment).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(screen.getByRole("textbox")).toBeEnabled());
  });

  it("offers a new assessment when the old one has expired", async () => {
    vi.mocked(api.sendAssessmentMessage).mockRejectedValue(new AssessmentApiError(404));
    renderPage();
    await sendMessage("hello");

    expect(await screen.findByText(ERROR_TEXT.expired)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Start a new assessment" }));

    await waitFor(() => expect(api.createAssessment).toHaveBeenCalledTimes(2));
  });

  it("opens the confirmation when the server refuses more chat (409)", async () => {
    vi.mocked(api.sendAssessmentMessage).mockRejectedValue(new AssessmentApiError(409));
    renderPage();
    await sendMessage("one more thing");

    expect(await screen.findByText(/1\. Sore throat/)).toBeInTheDocument();
  });

  it("asks for more detail when no symptoms were recognised", async () => {
    vi.mocked(api.sendAssessmentMessage).mockResolvedValue(reply("Please confirm.", "CONFIRMING"));
    vi.mocked(api.getAssessmentSymptoms).mockResolvedValue([]);
    renderPage();
    await sendMessage("hmm");

    expect(await screen.findByText(ERROR_TEXT.noSymptoms)).toBeInTheDocument();
  });
});
