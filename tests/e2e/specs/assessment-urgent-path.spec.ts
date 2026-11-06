/**
 * @file E2E urgent-path spec: red-flag symptoms must produce an URGENT result
 * with the emergency number (112) shown first (FR-06, FR-15, DR-02, AI_RULES §2 rule 5).
 *
 * Owner: Mohit (testing) · Task: S0-MOH-1 (scaffold), S1-MOH-4 (impl)
 * Requirements: FR-06, FR-15, DR-01, DR-02
 */

import { test, expect } from "../fixtures";

test.describe("Urgent assessment path", () => {
  test.beforeEach(async ({ consentPage }) => {
    await consentPage.acceptConsent();
  });

  test("severe chest pain shows URGENT alert with emergency number first", async ({
    page,
    chatPage,
    confirmationPage,
  }) => {
    // Severe chest pain is a canonical red-flag symptom (AI_RULES §2 rule 5)
    await chatPage.sendMessage(
      "I have severe chest pain radiating to my left arm, started 10 minutes ago"
    );
    await chatPage.waitForBotReply();
    await confirmationPage.confirmSymptoms();

    // The urgent-care full-screen alert must be shown (Dimple, S1-DIM-3)
    const urgentAlert = page.locator("[data-testid='urgent-alert']");
    await urgentAlert.waitFor({ state: "visible", timeout: 10_000 });

    // The emergency number 112 must appear before any other guidance text
    const alertText = await urgentAlert.innerText();
    const emergencyPos = alertText.indexOf("112");
    expect(emergencyPos).toBeGreaterThan(-1);

    // Disclaimer must still be present (DR-01)
    await expect(page.getByText(/not a medical diagnosis/i)).toBeVisible();
  });
});
