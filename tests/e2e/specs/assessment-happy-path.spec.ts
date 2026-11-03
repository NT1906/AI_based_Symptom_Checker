/**
 * @file E2E happy-path spec: full assessment flow from consent to result and restart.
 *
 * Covers task S1-MOH-4: start -> describe symptoms -> clarify -> confirm -> result -> restart.
 * This spec runs against the locally running full stack with AI_PROVIDER=mock
 * and CV_PROVIDER=mock so no real APIs are called (AI_RULES §2, NFR-07).
 *
 * Owner: Mohit (testing) · Task: S0-MOH-1 (scaffold), S1-MOH-4 (impl)
 * Requirements: FR-03, FR-04, FR-16, FR-22, FR-25, DR-01
 */

import { test, expect } from "../fixtures";

test.describe("Assessment happy path", () => {
  test.beforeEach(async ({ consentPage }) => {
    // Every test starts from the consent screen (DR-08)
    await consentPage.acceptConsent();
  });

  test("completes a full assessment and shows disclaimer", async ({
    page,
    chatPage,
    confirmationPage,
    resultPage,
  }) => {
    // Step 1: User describes symptoms in plain language (FR-03)
    await chatPage.sendMessage(
      "I have had a headache and mild fever for two days"
    );
    await chatPage.waitForBotReply();

    // Step 2: Bot may ask a clarifying question (FR-04). Answer it.
    // Why: The mock provider always returns a canned clarification question.
    await chatPage.sendMessage("The headache is on both sides and is throbbing");
    await chatPage.waitForBotReply();

    // Step 3: Symptom confirmation card appears (FR-16)
    await confirmationPage.confirmSymptoms();

    // Step 4: Result page loads (FR-22, DR-01)
    await resultPage.assertDisclaimerVisible();
    await resultPage.assertConditionsVisible();
    await resultPage.assertRiskBadgeVisible();

    // Step 5: Raw percentages must NOT appear anywhere in the result (AI_RULES §2 rule 3)
    const bodyText = await page.locator("body").innerText();
    expect(bodyText).not.toMatch(/\b\d{1,3}%/);
  });

  test("can restart and start a new assessment (FR-25)", async ({
    chatPage,
    confirmationPage,
    resultPage,
  }) => {
    await chatPage.sendMessage("I have a test rash on my arm");
    await chatPage.waitForBotReply();
    await confirmationPage.confirmSymptoms();
    await resultPage.assertDisclaimerVisible();

    // Restart flow
    await chatPage.clickRestart();

    // After restart, the chat input should be available again
    // Why: Restart resets state to START — the user should be back at the beginning.
    await expect(
      chatPage["page"].getByRole("textbox", {
        name: /describe your symptoms|type a message/i,
      })
    ).toBeVisible();
  });
});
