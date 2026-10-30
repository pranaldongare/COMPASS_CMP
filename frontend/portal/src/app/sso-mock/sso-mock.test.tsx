/**
 * The development stand-in for an organisation's sign-in (`SSO_MOCK`).
 *
 * - Any address gets a code; the code back sends the browser where the API
 *   says - the sign-in's callback.
 * - A sign-in the API does not know says to start again from the link.
 * - Cancel goes back the way a provider would.
 */
import { HttpResponse, http } from "msw";
import { afterEach, describe, expect, it, vi } from "vitest";

import SsoMockPage from "@/app/sso-mock/page";
import { render, screen } from "@/test/render";
import { API, server } from "@/test/server";

const STATE = "state-0123456789abcdef";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams({ state: STATE }),
}));

afterEach(() => {
  vi.unstubAllGlobals();
});

function stubAssign() {
  const assign = vi.fn();
  vi.stubGlobal("location", { ...window.location, assign });
  return assign;
}

describe("The stand-in sign-in", () => {
  it("sends a code to any address and, with it back, goes to the callback", async () => {
    const assign = stubAssign();
    const asked: unknown[] = [];
    server.use(
      http.post(`${API}/dev/sso/code`, async ({ request }) => {
        asked.push(await request.json());
        return HttpResponse.json({ ok: true, message: "Sent." });
      }),
      http.post(`${API}/dev/sso/confirm`, async ({ request }) => {
        asked.push(await request.json());
        return HttpResponse.json({ redirect_url: "/api/auth/sso/callback?state=s&code=c" });
      }),
    );
    const { user } = render(<SsoMockPage />);

    await user.type(screen.getByLabelText(/work email/i), "anyone@wherever.example");
    await user.click(screen.getByRole("button", { name: "Send a code" }));
    await user.type(await screen.findByLabelText(/the code we sent/i), "123456");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    await vi.waitFor(() =>
      expect(assign).toHaveBeenCalledWith("/api/auth/sso/callback?state=s&code=c"),
    );
    expect(asked).toEqual([
      { state: STATE, email: "anyone@wherever.example" },
      { state: STATE, email: "anyone@wherever.example", code: "123456" },
    ]);
  });

  it("says to start again when the sign-in is unknown", async () => {
    server.use(
      http.post(`${API}/dev/sso/code`, () =>
        HttpResponse.json(
          { error: { code: "not_found", message: "Not found" } },
          { status: 404 },
        ),
      ),
    );
    const { user } = render(<SsoMockPage />);
    await user.type(screen.getByLabelText(/work email/i), "anyone@wherever.example");
    await user.click(screen.getByRole("button", { name: "Send a code" }));
    expect(await screen.findByText(/start again/i)).toBeInTheDocument();
  });

  it("cancels back to the callback", async () => {
    const assign = stubAssign();
    server.use(
      http.post(`${API}/dev/sso/cancel`, () =>
        HttpResponse.json({
          redirect_url: "/api/auth/sso/callback?state=s&error=access_denied",
        }),
      ),
    );
    const { user } = render(<SsoMockPage />);
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    await vi.waitFor(() =>
      expect(assign).toHaveBeenCalledWith(
        "/api/auth/sso/callback?state=s&error=access_denied",
      ),
    );
  });
});
