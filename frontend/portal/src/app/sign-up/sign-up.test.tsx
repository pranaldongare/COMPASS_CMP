/**
 * Sign-up refuses a child with the server's own words, on the date-of-birth
 * field (S2-01). Before this the page knew only "already registered" and showed
 * a person under eighteen "We could not complete that. Please try again." - the
 * refusal held, but it read like a fault.
 */
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";

import SignUpPage from "@/app/sign-up/page";
import { render, screen, waitFor } from "@/test/render";
import { API, server } from "@/test/server";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => "/sign-up",
}));
vi.mock("@/components/security", () => ({
  AuthPageGate: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));
vi.mock("@/providers", () => ({ useAuth: () => ({ refresh: vi.fn(), me: null }) }));

const REFUSAL =
  "We cannot register or record consent for a person under eighteen. If you think your date of birth is wrong, contact the Privacy Office.";

describe("sign-up", () => {
  it("puts the under-eighteen refusal on the date of birth, offering no guardian route", async () => {
    server.use(
      http.post(`${API}/auth/register`, () =>
        HttpResponse.json(
          {
            error: {
              code: "minor_not_permitted",
              message: REFUSAL,
              field: "dob",
              request_id: "t",
            },
          },
          { status: 422 },
        ),
      ),
    );
    const { user } = render(<SignUpPage />);

    await user.type(screen.getByLabelText(/full name/i), "Child Tester");
    await user.type(screen.getByLabelText(/mobile number/i), "+91 98707 00009");
    await user.type(screen.getByLabelText(/date of birth/i), "2015-03-01");
    await user.click(
      screen.getByRole("button", { name: /create|sign up|register|continue/i }),
    );

    expect(await screen.findByText(REFUSAL)).toBeInTheDocument();
    expect(screen.queryByText(/could not complete that/i)).not.toBeInTheDocument();
    expect(document.body.textContent?.toLowerCase()).not.toMatch(/guardian|parent/);
  });
});

/**
 * Every refusal of `POST /auth/register/verify` is one sentence on one field
 * (2026-11-08): an unknown mobile, a wrong code, an expired one, one left out
 * and one cancelled by its fifth wrong try. The fifth used to answer "Too many
 * incorrect attempts. Request a new code."; now nothing the server says tells
 * the person that the code is gone, or how to get another. So the page says
 * it, to everybody alike, and the details already given ask for new codes.
 *
 * Those codes go to the contacts the sign-up was begun with, whatever is typed
 * later, so the step offers no way back to change the details: it says where
 * the codes go instead (2026-11-08).
 */
const ACCEPTED = {
  ok: true,
  message: "We have sent a code to each contact you gave. Enter them to finish.",
};
const NEUTRAL = {
  error: {
    code: "otp_invalid",
    message: "Invalid or expired code",
    field: "mobile_code",
    request_id: "t",
  },
};
const HINT =
  "Each code expires in ten minutes, or after five wrong tries; then send the codes again. They go to the contacts given when this sign-up began.";
const RESENT =
  "A new code is on its way to each contact given when this sign-up began. The earlier ones no longer work.";

async function giveDetails(
  user: ReturnType<typeof render>["user"],
  { email }: { email: string | null },
) {
  await user.type(screen.getByLabelText(/full name/i), "Asha Tester");
  await user.type(screen.getByLabelText(/mobile number/i), "+919870700009");
  if (email) await user.type(screen.getByLabelText(/email address/i), email);
  await user.type(screen.getByLabelText(/date of birth/i), "1990-01-01");
  await user.click(screen.getByRole("button", { name: /create account/i }));
  await screen.findByRole("heading", { name: /confirm your contacts/i });
}

describe("confirming the contacts", () => {
  it("says that five wrong tries cancel a code, and sends the codes again with the same details", async () => {
    const registered: unknown[] = [];
    const verified: unknown[] = [];
    server.use(
      http.post(`${API}/auth/register`, async ({ request }) => {
        registered.push(await request.json());
        return HttpResponse.json(ACCEPTED, { status: 202 });
      }),
      http.post(`${API}/auth/register/verify`, async ({ request }) => {
        verified.push(await request.json());
        return HttpResponse.json(NEUTRAL, { status: 400 });
      }),
    );
    const { user } = render(<SignUpPage />);
    await giveDetails(user, { email: "asha@example.org" });

    expect(screen.getByText(HINT)).toBeInTheDocument();
    const mobileCode = screen.getByLabelText(/code sent to your mobile/i);
    const emailCode = screen.getByLabelText(/code sent to your email/i);
    const confirm = screen.getByRole("button", { name: /confirm and sign in/i });

    // Both codes, always, when both contacts were given: one alone is not enough.
    await user.type(mobileCode, "123456");
    expect(confirm).toBeDisabled();
    await user.type(emailCode, "654321");
    await user.click(confirm);

    expect(await screen.findByText("Invalid or expired code")).toBeInTheDocument();
    expect(verified).toEqual([
      { mobile: "+919870700009", mobile_code: "123456", email_code: "654321" },
    ]);
    // The refusal names no code: it is not put on the mobile's field.
    expect(mobileCode).not.toHaveAttribute("aria-invalid");
    expect(screen.getByText(HINT)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /sign in instead/i })).toHaveAttribute(
      "href",
      `/sign-in?contact=${encodeURIComponent("+919870700009")}`,
    );

    // No way back to change a contact: the codes would not follow it.
    expect(
      screen.queryByRole("button", { name: /change the details/i }),
    ).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Send the codes again" }));

    expect(await screen.findByText(RESENT)).toBeInTheDocument();
    expect(registered).toHaveLength(2);
    expect(registered[1]).toEqual(registered[0]);
    expect(registered[1]).toEqual({
      full_name: "Asha Tester",
      mobile: "+919870700009",
      dob: "1990-01-01",
      email: "asha@example.org",
    });
    expect(screen.queryByText("Invalid or expired code")).not.toBeInTheDocument();
    expect(mobileCode).toHaveValue("");
    expect(emailCode).toHaveValue("");
  });

  it("shows the server's words when the codes cannot be sent again", async () => {
    let calls = 0;
    server.use(
      http.post(`${API}/auth/register`, () => {
        calls += 1;
        return calls === 1
          ? HttpResponse.json(ACCEPTED, { status: 202 })
          : HttpResponse.json(
              {
                error: {
                  code: "rate_limited",
                  message: "Too many registration attempts for this contact.",
                  request_id: "t",
                },
              },
              { status: 429 },
            );
      }),
    );
    const { user } = render(<SignUpPage />);
    await giveDetails(user, { email: null });

    await user.click(screen.getByRole("button", { name: "Send the codes again" }));

    expect(
      await screen.findByText("Too many registration attempts for this contact."),
    ).toBeInTheDocument();
    expect(screen.queryByText(/on (its|their) way/i)).not.toBeInTheDocument();
  });

  it("puts a contact taken since in the page's own words, offering no other contact", async () => {
    let calls = 0;
    server.use(
      http.post(`${API}/auth/register`, () => {
        calls += 1;
        return calls === 1
          ? HttpResponse.json(ACCEPTED, { status: 202 })
          : HttpResponse.json(
              {
                error: {
                  code: "contact_taken",
                  message:
                    "An account already exists with this email. Sign in with it instead, or use a different email.",
                  field: "email",
                  request_id: "t",
                },
              },
              { status: 409 },
            );
      }),
    );
    const { user } = render(<SignUpPage />);
    await giveDetails(user, { email: "asha@example.org" });

    await user.click(screen.getByRole("button", { name: "Send the codes again" }));

    expect(
      await screen.findByText(
        "An account already holds this email. If it is yours, sign in with it instead.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText(/use a different/i)).not.toBeInTheDocument();
    expect(screen.queryByText(RESENT)).not.toBeInTheDocument();
  });

  it("with a mobile alone, takes the code an earlier email was sent, and offers no way back", async () => {
    const verified: unknown[] = [];
    server.use(
      http.post(`${API}/auth/register`, () => HttpResponse.json(ACCEPTED, { status: 202 })),
      http.post(`${API}/auth/register/verify`, async ({ request }) => {
        verified.push(await request.json());
        return HttpResponse.json(NEUTRAL, { status: 400 });
      }),
    );
    const { user } = render(<SignUpPage />);
    await giveDetails(user, { email: null });

    expect(
      screen.getByText("A code has gone to your mobile. Enter it below."),
    ).toBeInTheDocument();
    expect(screen.getByText(HINT)).toBeInTheDocument();
    const emailCode = screen.getByLabelText(
      "Code sent to your email, if you gave one before",
    );
    expect(emailCode).not.toBeRequired();
    expect(
      screen.getByText(
        "Only if you started signing up before and gave an email then: a code has gone there too. Otherwise leave this empty.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText(/change the details/i)).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /change the details/i }),
    ).not.toBeInTheDocument();

    const confirm = screen.getByRole("button", { name: /confirm and sign in/i });
    await user.type(screen.getByLabelText(/code sent to your mobile/i), "123456");
    // The mobile's code alone is enough to send...
    expect(confirm).toBeEnabled();
    await user.click(confirm);
    expect(await screen.findByText("Invalid or expired code")).toBeInTheDocument();
    // ...and a code half typed in the email's box is not sent.
    await user.type(emailCode, "654");
    expect(confirm).toBeDisabled();
    await user.type(emailCode, "321");
    await user.click(confirm);
    await waitFor(() => expect(verified).toHaveLength(2));
    expect(verified).toEqual([
      { mobile: "+919870700009", mobile_code: "123456", email_code: null },
      { mobile: "+919870700009", mobile_code: "123456", email_code: "654321" },
    ]);

    await user.click(screen.getByRole("button", { name: "Send the codes again" }));
    expect(await screen.findByText(RESENT)).toBeInTheDocument();
  });
});

/**
 * The first step's refusals are answered by what the server says, not by who
 * holds the contact (2026-11-08): a member of staff's email, pending or not,
 * is as taken as a data principal's, and goes on its field with sign-in
 * offered, as anybody's does.
 */
describe("giving the details", () => {
  it("puts a taken email's refusal on the email field and offers sign-in with it", async () => {
    server.use(
      http.post(`${API}/auth/register`, () =>
        HttpResponse.json(
          {
            error: {
              code: "contact_taken",
              message:
                "An account already exists with this email. Sign in with it instead, or use a different email.",
              field: "email",
              request_id: "t",
            },
          },
          { status: 409 },
        ),
      ),
    );
    const { user } = render(<SignUpPage />);
    await user.type(screen.getByLabelText(/full name/i), "Asha Tester");
    await user.type(screen.getByLabelText(/mobile number/i), "+919870700009");
    await user.type(screen.getByLabelText(/email address/i), "staff@example.org");
    await user.type(screen.getByLabelText(/date of birth/i), "1990-01-01");
    await user.click(screen.getByRole("button", { name: /create account/i }));

    expect(
      await screen.findByText(
        "An account already exists with this email. Sign in with it instead, or use a different email.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/email address/i)).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByLabelText(/mobile number/i)).not.toHaveAttribute("aria-invalid");
    expect(screen.getByRole("link", { name: /sign in with this email/i })).toHaveAttribute(
      "href",
      `/sign-in?contact=${encodeURIComponent("staff@example.org")}`,
    );
    expect(
      screen.queryByRole("heading", { name: /confirm your contacts/i }),
    ).not.toBeInTheDocument();
  });
});
