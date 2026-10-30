/**
 * The development code popup sits in the top-right corner, where every page
 * keeps its main action. A spent sign-in code left there hid the Legal PoC's
 * "New notice template" (2026-10-30), so a page change puts away every code
 * the person has had - clicked or typed since it appeared - and only a code
 * not yet had goes with it, because its own request moved the page (sign-in
 * to verify).
 */
import { HttpResponse, http } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { DevCodePopup } from "@/features/dev/dev-code-popup";
import { render, screen } from "@/test/render";
import { API, server } from "@/test/server";

const nav = vi.hoisted(() => ({ path: "/sign-in" }));

vi.mock("next/navigation", () => ({ usePathname: () => nav.path }));
vi.mock("@/lib/dev/dev-client", () => ({
  DEV_CODES_ON: true,
  DEV_CLIENT_HEADER: "X-CMP-Dev-Client",
  devClientId: () => "tab-1",
}));

const CODE = "468985";

describe("DevCodePopup", () => {
  beforeEach(() => {
    nav.path = "/sign-in";
    // Sent after the popup starts listening, or it would not be new to it.
    const at = Date.now() / 1000 + 1;
    server.use(
      http.get(`${API}/dev/codes`, () =>
        HttpResponse.json({
          items: [{ to: "meera.nair@cmp.local", channel: "email", code: CODE, at }],
        }),
      ),
    );
  });

  it("puts a code away when the page changes after the person has had it", async () => {
    nav.path = "/sign-in/verify";
    const { user, rerender } = render(<DevCodePopup />);
    expect(await screen.findByText(CODE)).toBeInTheDocument();

    await user.keyboard(CODE);
    nav.path = "/notices/templates";
    rerender(<DevCodePopup />);
    expect(screen.queryByText(CODE)).not.toBeInTheDocument();
  });

  it("keeps a code through the page change its own request caused", async () => {
    const { rerender } = render(<DevCodePopup />);
    expect(await screen.findByText(CODE)).toBeInTheDocument();

    nav.path = "/sign-in/verify";
    rerender(<DevCodePopup />);
    expect(screen.getByText(CODE)).toBeInTheDocument();
  });

  it("stays on the page that asked, whatever the person does there", async () => {
    const { user } = render(<DevCodePopup />);
    expect(await screen.findByText(CODE)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /copy code/i }));
    expect(screen.getByText(CODE)).toBeInTheDocument();
  });
});
