/**
 * Sign-up refuses a child with the server's own words, on the date-of-birth
 * field (S2-01). Before this the page knew only "already registered" and showed
 * a person under eighteen "We could not complete that. Please try again." - the
 * refusal held, but it read like a fault.
 */
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";

import SignUpPage from "@/app/sign-up/page";
import { render, screen } from "@/test/render";
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
  "Each code expires in ten minutes, or after five wrong tries; then send the codes again.";

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

    await user.click(screen.getByRole("button", { name: "Send the codes again" }));

    expect(
      await screen.findByText(
        "New codes are on their way. The earlier ones no longer work.",
      ),
    ).toBeInTheDocument();
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

  it("with a mobile alone, says where an earlier email's code went, and goes back with the details kept", async () => {
    server.use(
      http.post(`${API}/auth/register`, () => HttpResponse.json(ACCEPTED, { status: 202 })),
    );
    const { user } = render(<SignUpPage />);
    await giveDetails(user, { email: null });

    expect(screen.queryByLabelText(/code sent to your email/i)).not.toBeInTheDocument();
    expect(
      screen.getByText(
        /If you gave an email when you first started signing up, a code has gone there too/,
      ),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Send the codes again" }));
    expect(
      await screen.findByText("A new code is on its way. The earlier one no longer works."),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Change the details" }));

    expect(
      await screen.findByRole("heading", { name: /create your account/i }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/full name/i)).toHaveValue("Asha Tester");
    expect(screen.getByLabelText(/mobile number/i)).toHaveValue("+919870700009");
  });
});
