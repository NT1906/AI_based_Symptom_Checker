/**
 * @file Shared Playwright fixtures and page-object helpers for the
 * AI-Based Symptom Checker E2E suite.
 *
 * Responsibilities:
 *   - Export a custom `test` with page-object fixtures pre-wired.
 *   - Provide typed helpers for common user actions (consent, chat, result).
 *
 * Owner: Mohit (testing) · Task: S0-MOH-1 · Requirements: NFR-07, NFR-08
 */

import { test as base, expect, type Page } from "@playwright/test";

// ---------------------------------------------------------------------------
// Page-Object Helpers
// ---------------------------------------------------------------------------

/**
 * Encapsulates interactions with the consent step shown before any assessment.
 * This step is mandatory (DR-08) and must complete before messages can be sent.
 */
export class ConsentPage {
  constructor(private readonly page: Page) {}

  /** Navigate to the app root and accept the consent prompt. */
  async acceptConsent(): Promise<void> {
    await this.page.goto("/");
    // Why: The consent button text is defined by Dimple (S1-DIM-1).
    // Use a role selector so the test is resilient to minor label changes.
    const consentButton = this.page.getByRole("button", {
      name: /i understand|accept|agree/i,
    });
    await consentButton.waitFor({ state: "visible", timeout: 10_000 });
    await consentButton.click();
  }
}

/**
 * Encapsulates interactions with the guided chat interface (Rutva, S1-RUT-1).
 */
export class ChatPage {
  constructor(private readonly page: Page) {}

  /** Type a message in the input field and submit it. */
  async sendMessage(text: string): Promise<void> {
    const input = this.page.getByRole("textbox", {
      name: /describe your symptoms|type a message/i,
    });
    await input.fill(text);
    await this.page.keyboard.press("Enter");
  }

  /** Wait for the most recent bot reply to appear in the chat. */
  async waitForBotReply(): Promise<void> {
    // Why: aria-live on the message list means new messages are announced.
    await this.page
      .locator("[aria-live]")
      .last()
      .waitFor({ state: "visible", timeout: 15_000 });
  }

  /** Click the "Start new assessment" / restart button (Mann, S1-MAN-4). */
  async clickRestart(): Promise<void> {
    await this.page
      .getByRole("button", { name: /start new|restart/i })
      .click();
    // Confirm the dialog if one appears
    const confirmButton = this.page.getByRole("button", {
      name: /confirm|yes/i,
    });
    if (await confirmButton.isVisible()) {
      await confirmButton.click();
    }
  }
}

/**
 * Encapsulates interactions with the symptom confirmation card (Mann, S1-MAN-1).
 */
export class ConfirmationPage {
  constructor(private readonly page: Page) {}

  /** Click the primary confirm / looks-correct button. */
  async confirmSymptoms(): Promise<void> {
    await this.page
      .getByRole("button", { name: /confirm|looks correct|that.s right/i })
      .click();
  }
}

/**
 * Encapsulates assertions on the result page (Mann, S1-MAN-3).
 */
export class ResultPage {
  constructor(private readonly page: Page) {}

  /**
   * Assert the mandatory medical disclaimer is visible somewhere on the page.
   * This is a non-negotiable safety requirement (DR-01, AI_RULES §2).
   */
  async assertDisclaimerVisible(): Promise<void> {
    await expect(
      this.page.getByText(/not a medical diagnosis/i)
    ).toBeVisible();
  }

  /** Assert at least one condition card with a confidence badge is shown. */
  async assertConditionsVisible(): Promise<void> {
    await expect(
      this.page.locator("[data-testid='condition-card']").first()
    ).toBeVisible();
  }

  /** Assert the risk badge (SELF_CARE / CONSULT_DOCTOR / URGENT) is shown. */
  async assertRiskBadgeVisible(): Promise<void> {
    await expect(
      this.page.locator("[data-testid='risk-badge']")
    ).toBeVisible();
  }
}

// ---------------------------------------------------------------------------
// Custom test fixture
// ---------------------------------------------------------------------------

/** Fixtures available to every spec file that imports from this module. */
type E2EFixtures = {
  consentPage: ConsentPage;
  chatPage: ChatPage;
  confirmationPage: ConfirmationPage;
  resultPage: ResultPage;
};

export const test = base.extend<E2EFixtures>({
  consentPage: async ({ page }, use) => {
    await use(new ConsentPage(page));
  },
  chatPage: async ({ page }, use) => {
    await use(new ChatPage(page));
  },
  confirmationPage: async ({ page }, use) => {
    await use(new ConfirmationPage(page));
  },
  resultPage: async ({ page }, use) => {
    await use(new ResultPage(page));
  },
});

export { expect };
