/**
 * Sign-in says when a code could not be sent (review 2026-10-01, UX-3).
 *
 * The page swallowed every failure of the code request and showed "if this
 * contact is registered, a code is on its way" regardless - so a person
 * during an outage, or past the hourly limit, waited for a code that was never
 * going to come. That silence was meant to keep the form neutral; it is the
 * server that keeps it neutral. Its reply is the same for a registered contact
 * and a stranger, a rate limit is counted before anybody is looked up, and an
 * outage is a 503 for everybody (`ensure_broker`). So a failure can be shown.
 */
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";

import SignInPage from "@/app/sign-in/page";
import { render, screen } from "@/test/render";
import { API, server } from "@/test/server";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => "/sign-in",
}));
vi.mock("@/components/security", () => ({
  AuthPageGate: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));
vi.mock("@/providers", () => ({ useAuth: () => ({ refresh: vi.fn(), me: null }) }));

async function ask(user: ReturnType<typeof render>["user"]) {
  await user.type(await screen.findByLabelText(/mobile number/i), "+919876500001");
  await user.click(screen.getByRole("button", { name: /send|code|continue/i }));
}

describe("asking for a sign-in code", () => {
  it("shows the same neutral sentence when the request was taken", async () => {
    server.use(
      http.post(`${API}/auth/otp/request`, () => HttpResponse.json({ ok: true, message: "" })),
    );
    const { user } = render(<SignInPage />);
    await ask(user);
    expect(await screen.findByText(/check your messages/i)).toBeInTheDocument();
  });

  it.each([
    [503, "service_unavailable", "We could not send that message just now."],
    [429, "rate_limited", "Too many code requests for this contact."],
  ])("says so when the request failed (%s)", async (status, code, message) => {
    server.use(
      http.post(`${API}/auth/otp/request`, () =>
        HttpResponse.json({ error: { code, message, request_id: "t" } }, { status }),
      ),
    );
    const { user } = render(<SignInPage />);
    await ask(user);
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.queryByText(/check your messages/i)).not.toBeInTheDocument();
  });
});
