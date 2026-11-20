/**
 * Who may be sent to sign-in. A path missing from this list bounces a person
 * with no account off the page written for them.
 */
import { describe, expect, it } from "vitest";

import { isPublicPath } from "@/lib/security/public-routes";

describe("isPublicPath", () => {
  it("lets the public incident report through", () => {
    expect(isPublicPath("/report-incident")).toBe(true);
  });

  it("lets a breach notice's link through, for somebody with no account", () => {
    expect(isPublicPath(`/breach-notice/${"a".repeat(64)}`)).toBe(true);
    // Her own notices, on her account, stay behind sign-in.
    expect(isPublicPath("/breach-notices")).toBe(false);
  });

  it("keeps an account's pages behind sign-in", () => {
    expect(isPublicPath("/home")).toBe(false);
    expect(isPublicPath("/my-consents")).toBe(false);
  });
});
