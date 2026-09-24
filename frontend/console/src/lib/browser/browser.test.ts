/**
 * The page opened at `http://<ip>` is not a secure context, and the browser
 * leaves out `crypto.randomUUID` and `navigator.clipboard` there. These pin
 * that nothing the app relies on throws when they are missing.
 */
import { afterEach, describe, expect, it, vi } from "vitest";

import { copyText, uid } from "@/lib/browser";

afterEach(() => vi.unstubAllGlobals());

describe("uid", () => {
  it("works without crypto.randomUUID, as over plain http by IP", () => {
    vi.stubGlobal("crypto", {
      getRandomValues: (a: Uint8Array) => a.map(() => Math.floor(Math.random() * 256)),
    });
    const a = uid();
    const b = uid();
    expect(a).toMatch(/^[0-9a-f]{32}$/);
    expect(a).not.toBe(b);
  });

  it("works with no crypto at all", () => {
    vi.stubGlobal("crypto", undefined);
    expect(uid()).toMatch(/^[0-9a-z]+$/);
  });
});

describe("copyText", () => {
  it("falls back to the selection copy when navigator.clipboard is missing", async () => {
    vi.stubGlobal("navigator", {});
    const exec = vi.fn().mockReturnValue(true);
    Object.defineProperty(document, "execCommand", { value: exec, configurable: true });

    expect(await copyText("https://portal/c/abc")).toBe(true);
    expect(exec).toHaveBeenCalledWith("copy");
    expect(document.querySelector("textarea")).toBeNull(); // cleaned up
  });

  it("never throws, and says when the copy did not happen", async () => {
    vi.stubGlobal("navigator", {
      clipboard: { writeText: vi.fn().mockRejectedValue(new Error("denied")) },
    });
    Object.defineProperty(document, "execCommand", {
      value: () => {
        throw new Error("unsupported");
      },
      configurable: true,
    });
    await expect(copyText("x")).resolves.toBe(false);
  });
});
