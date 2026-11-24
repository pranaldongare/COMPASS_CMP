/**
 * Leaving the code step (2026-11-24).
 *
 * While the password-only session lives, the sign-in page sends its holder
 * back to the code step. "Start over" was a plain link to the sign-in page, so
 * somebody whose code went wrong looped between the two and never reached
 * "Forgotten your password?". Both ways out now end the half-finished sign-in
 * first, and the code step offers the reset itself.
 */
import { describe, expect, it, vi } from "vitest";

import VerifyPage from "@/app/sign-in/verify/page";
import { render, screen, waitFor } from "@/test/render";
import { API, HttpResponse, http, server } from "@/test/server";

const replace = vi.fn();
const navigateFresh = vi.fn();
vi.mock("@/lib/security", async (original) => ({
  ...(await original<typeof import("@/lib/security")>()),
  navigateFresh: (href: string) => navigateFresh(href),
}));
vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(""),
  usePathname: () => "/sign-in/verify",
  useRouter: () => ({ push: vi.fn(), replace, back: vi.fn(), refresh: vi.fn() }),
}));

vi.mock("@/providers", () => ({
  useAuth: () => ({ refresh: () => Promise.resolve() }),
  useSessionState: () => ({ status: "partial" }),
}));

function partialSession() {
  const ended: string[] = [];
  server.use(
    http.post(`${API}/auth/logout`, () => {
      ended.push("logout");
      return HttpResponse.json({ ok: true, message: "Signed out." });
    }),
  );
  return ended;
}

describe("leaving the code step", () => {
  it("ends the half-finished sign-in before going to the password reset", async () => {
    const ended = partialSession();
    navigateFresh.mockClear();
    const { user } = render(<VerifyPage />);

    await user.click(await screen.findByRole("button", { name: "Forgotten your password?" }));

    await waitFor(() => expect(navigateFresh).toHaveBeenCalledWith("/sign-in/reset"));
    expect(ended).toEqual(["logout"]);
  });

  it("ends it before starting over, so the sign-in page does not send them back", async () => {
    const ended = partialSession();
    navigateFresh.mockClear();
    const { user } = render(<VerifyPage />);

    await user.click(await screen.findByRole("button", { name: "Start over" }));

    await waitFor(() => expect(navigateFresh).toHaveBeenCalledWith("/sign-in"));
    expect(ended).toEqual(["logout"]);
  });

  it("still leaves when the session has already gone", async () => {
    partialSession();
    server.use(
      http.post(`${API}/auth/logout`, () =>
        HttpResponse.json({ error: { code: "unauthenticated", message: "x" } }, { status: 401 }),
      ),
    );
    navigateFresh.mockClear();
    const { user } = render(<VerifyPage />);

    await user.click(await screen.findByRole("button", { name: "Forgotten your password?" }));

    await waitFor(() => expect(navigateFresh).toHaveBeenCalledWith("/sign-in/reset"));
  });
});
