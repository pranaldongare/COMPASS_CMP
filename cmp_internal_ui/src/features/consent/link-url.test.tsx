/**
 * A consent link points at the portal that serves it, never at the console.
 *
 * The bug this pins: all three places that showed a minted link built it from
 * `window.location.origin`, which is the console's own origin — 3000 in
 * development. `/c/{token}` is a page on the data principal's portal, on 3001.
 * So the URL copied out of the console and handed to whoever collects was a
 * host that has no such route, and nothing about it looked wrong.
 *
 * It is worth a test rather than a careful reading, because the failure is
 * invisible from inside the console: the string is well-formed, the token in it
 * is correct, and the only way to find out is to open it.
 */

import { describe, expect, it, vi } from "vitest";

import { CopyLinkButton } from "@/features/consent/components/copy-link";
import { consentLinkUrl } from "@/features/consent/link-url";
import { config } from "@/lib/config";
import { render, screen } from "@/test/render";

vi.mock("@/providers", async () => {
  const actual = await vi.importActual<Record<string, unknown>>("@/providers");
  return {
    ...actual,
    useToast: () => ({ success: vi.fn(), error: vi.fn(), info: vi.fn(), warning: vi.fn() }),
  };
});

const PATH = "/c/EXAMPLE-TOKEN";

describe("consentLinkUrl", () => {
  it("puts the data principal's portal in front of the path", () => {
    expect(consentLinkUrl(PATH)).toBe(`${config.subjectPortalUrl}${PATH}`);
  });

  it("is not the console's own origin, which has no such route", () => {
    expect(consentLinkUrl(PATH).startsWith(window.location.origin)).toBe(false);
  });

  it("answers nothing for a link whose token was never kept", () => {
    expect(consentLinkUrl(null)).toBe("");
    expect(consentLinkUrl("")).toBe("");
  });

  it("does not double the slash when the configured origin carries one", () => {
    const trailing = { ...config, subjectPortalUrl: "https://portal.example.org/" };
    vi.spyOn(config, "subjectPortalUrl", "get").mockReturnValue(trailing.subjectPortalUrl);

    expect(consentLinkUrl(PATH)).toBe(`https://portal.example.org${PATH}`);

    vi.restoreAllMocks();
  });
});

describe("the copy button", () => {
  it("copies the portal's URL", async () => {
    // `userEvent.setup()` installs its own clipboard, so the assertion reads
    // what the button actually put there rather than spying on the call.
    const { user } = render(<CopyLinkButton link={{ url_path: PATH, status: "active" }} />);
    await user.click(screen.getByRole("button", { name: /copy link/i }));

    expect(await navigator.clipboard.readText()).toBe(`${config.subjectPortalUrl}${PATH}`);
  });

  it("offers nothing to copy where the URL was never kept", () => {
    render(<CopyLinkButton link={{ url_path: null, status: "active" }} />);

    expect(screen.queryByRole("button", { name: /copy link/i })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /url not kept/i })).toBeInTheDocument();
  });
});
