import { expect, type Page } from "@playwright/test";

/**
 * The page must fit the viewport it was given. A page wider than the phone
 * makes mobile Chrome zoom out to the content width, and a control the layout
 * puts at one point is then hit-tested at another - which is how a button came
 * to be "under" a card two screens above it.
 */
export async function expectNoSidewaysScroll(page: Page): Promise<void> {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow, "the page must not scroll sideways").toBeLessThanOrEqual(0);
}
