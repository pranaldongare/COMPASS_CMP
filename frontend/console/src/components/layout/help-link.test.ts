/**
 * Help goes back to the page it was opened from, and only to one of ours.
 */
import { afterEach, describe, expect, it } from "vitest";

import { helpHref, helpReturn } from "@/components/layout/help-link";
import { safeRedirectPath } from "@/lib/security";

const safe = (v: string | null) => safeRedirectPath(v, "");

afterEach(() => window.history.replaceState(null, "", "/"));

describe("helpHref", () => {
  it("carries the page and its query string", () => {
    window.history.replaceState(null, "", "/projects?status=approved");
    expect(helpHref()).toBe(`/help?from=${encodeURIComponent("/projects?status=approved")}`);
  });

  it("does not point Help back at Help", () => {
    window.history.replaceState(null, "", "/help?from=%2Fprojects");
    expect(helpHref()).toBe("/help");
  });
});

describe("helpReturn", () => {
  it("returns one of this site's own pages", () => {
    expect(helpReturn("/projects/abc#sites", safe)).toBe("/projects/abc#sites");
  });

  it.each(["https://evil.example/", "//evil.example", "javascript:alert(1)", "/help", null])(
    "refuses %s",
    (from) => {
      expect(helpReturn(from, safe)).toBeNull();
    },
  );
});
