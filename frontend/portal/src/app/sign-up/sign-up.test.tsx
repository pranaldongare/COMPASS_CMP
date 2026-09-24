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
          { error: { code: "minor_not_permitted", message: REFUSAL, field: "dob", request_id: "t" } },
          { status: 422 },
        ),
      ),
    );
    const { user } = render(<SignUpPage />);

    await user.type(screen.getByLabelText(/full name/i), "Child Tester");
    await user.type(screen.getByLabelText(/mobile number/i), "+91 98707 00009");
    await user.type(screen.getByLabelText(/date of birth/i), "2015-03-01");
    await user.click(screen.getByRole("button", { name: /create|sign up|register|continue/i }));

    expect(await screen.findByText(REFUSAL)).toBeInTheDocument();
    expect(screen.queryByText(/could not complete that/i)).not.toBeInTheDocument();
    expect(document.body.textContent?.toLowerCase()).not.toMatch(/guardian|parent/);
  });
});
