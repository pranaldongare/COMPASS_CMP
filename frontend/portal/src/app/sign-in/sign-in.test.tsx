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

/**
 * A sign-in code verifies only with the contact it was sent to (2026-11-08):
 * the server keys it on the account and that contact, so a code sent to the
 * mobile is refused with the email typed. The page sends back exactly what it
 * asked a code for, the contact chosen again included.
 */
describe("verifying a sign-in code", () => {
  it("sends the contact the code was asked for, and the new one once it is changed", async () => {
    const asked: string[] = [];
    const verified: unknown[] = [];
    server.use(
      http.post(`${API}/auth/otp/request`, async ({ request }) => {
        asked.push(((await request.json()) as { contact: string }).contact);
        return HttpResponse.json({ ok: true, message: "" });
      }),
      http.post(`${API}/auth/otp/verify`, async ({ request }) => {
        verified.push(await request.json());
        return HttpResponse.json(
          { error: { code: "otp_invalid", message: "Invalid or expired code", request_id: "t" } },
          { status: 400 },
        );
      }),
    );
    const { user } = render(<SignInPage />);

    await ask(user);
    await user.type(await screen.findByLabelText(/six-digit code/i), "123456");
    await user.click(screen.getByRole("button", { name: "Verify" }));
    await vi.waitFor(() => expect(verified).toHaveLength(1));

    await user.click(screen.getByRole("button", { name: "Use a different contact" }));
    await user.click(screen.getByRole("radio", { name: "Email" }));
    const field = await screen.findByLabelText(/email address/i);
    await user.clear(field);
    await user.type(field, "Asha@Example.org");
    await user.click(screen.getByRole("button", { name: "Send code" }));
    await user.type(await screen.findByLabelText(/six-digit code/i), "654321");
    await user.click(screen.getByRole("button", { name: "Verify" }));
    await vi.waitFor(() => expect(verified).toHaveLength(2));

    expect(asked).toEqual(["+919876500001", "Asha@Example.org"]);
    expect(verified).toEqual([
      { contact: "+919876500001", code: "123456" },
      { contact: "Asha@Example.org", code: "654321" },
    ]);
  });

  /**
   * The server refuses a wrong code, a spent one and one never sent in one
   * sentence, a fifth wrong try included (2026-11-08): it no longer answers a
   * registered contact "Too many incorrect attempts. Request a new code.". So
   * the page says, to everybody alike, that five wrong tries cancel a code.
   */
  it("says to everybody that five wrong tries cancel the code, beside the server's one refusal", async () => {
    server.use(
      http.post(`${API}/auth/otp/request`, () => HttpResponse.json({ ok: true, message: "" })),
      http.post(`${API}/auth/otp/verify`, () =>
        HttpResponse.json(
          { error: { code: "otp_invalid", message: "Invalid or expired code", request_id: "t" } },
          { status: 400 },
        ),
      ),
    );
    const { user } = render(<SignInPage />);

    await ask(user);
    expect(
      await screen.findByText(/It expires in ten minutes, or after five wrong tries; then ask for another\./),
    ).toBeInTheDocument();
    await user.type(await screen.findByLabelText(/six-digit code/i), "123456");
    await user.click(screen.getByRole("button", { name: "Verify" }));

    expect(await screen.findByText("Invalid or expired code")).toBeInTheDocument();
    expect(screen.getByText(/after five wrong tries; then ask for another/)).toBeInTheDocument();
  });
});
