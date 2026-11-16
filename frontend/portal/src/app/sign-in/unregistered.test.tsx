/**
 * A contact no account carries is told so, and taken to registration
 * (2026-11-16, the product owner's decision). The server answers the code
 * request `404 account_not_found`; sign-in sends the person to sign-up with
 * the contact filled in, and sign-up says why they are there.
 */
import { HttpResponse, http } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import SignInPage from "@/app/sign-in/page";
import SignUpPage from "@/app/sign-up/page";
import { render, screen } from "@/test/render";
import { API, server } from "@/test/server";

const nav = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn(), query: "" }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: nav.push, replace: nav.replace }),
  useSearchParams: () => new URLSearchParams(nav.query),
  usePathname: () => "/sign-in",
}));
vi.mock("@/components/security", () => ({
  AuthPageGate: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));
vi.mock("@/providers", () => ({ useAuth: () => ({ refresh: vi.fn(), me: null }) }));

beforeEach(() => {
  vi.clearAllMocks();
  nav.query = "";
});

function refuseAsUnknown() {
  server.use(
    http.post(`${API}/auth/otp/request`, () =>
      HttpResponse.json(
        {
          error: {
            code: "account_not_found",
            message: "No account exists for this mobile number or email address. Register first.",
            field: "contact",
            request_id: "t",
          },
        },
        { status: 404 },
      ),
    ),
  );
}

describe("signing in with a contact nobody registered", () => {
  it("goes to sign-up with the contact, and never says a code is on its way", async () => {
    refuseAsUnknown();
    const { user } = render(<SignInPage />);
    await user.type(await screen.findByLabelText(/mobile number/i), "+919876500001");
    await user.click(screen.getByRole("button", { name: "Send code" }));

    await vi.waitFor(() =>
      expect(nav.push).toHaveBeenCalledWith("/sign-up?contact=%2B919876500001&unregistered=1"),
    );
    expect(screen.queryByText(/check your messages/i)).not.toBeInTheDocument();
  });

  it("keeps where the person was going", async () => {
    refuseAsUnknown();
    nav.query = "next=/my-requests";
    const { user } = render(<SignInPage />);
    await user.type(await screen.findByLabelText(/mobile number/i), "+919876500001");
    await user.click(screen.getByRole("button", { name: "Send code" }));

    await vi.waitFor(() =>
      expect(nav.push).toHaveBeenCalledWith(
        "/sign-up?contact=%2B919876500001&unregistered=1&next=%2Fmy-requests",
      ),
    );
  });
});

describe("sign-up, reached that way", () => {
  it("says there is no account for the mobile, which is filled in", async () => {
    nav.query = "contact=%2B919876500001&unregistered=1";
    render(<SignUpPage />);

    expect(await screen.findByText("No account exists for that contact")).toBeInTheDocument();
    expect(screen.getByLabelText(/mobile number/i)).toHaveValue("+919876500001");
  });

  it("fills an email in as the email, and says a mobile is needed too", async () => {
    nav.query = "contact=asha%40example.org&unregistered=1";
    render(<SignUpPage />);

    expect(await screen.findByText(/you will need a mobile number too/)).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toHaveValue("asha@example.org");
    expect(screen.getByLabelText(/mobile number/i)).toHaveValue("");
  });

  it("says nothing of the kind to somebody who came to register", async () => {
    render(<SignUpPage />);
    await screen.findByLabelText(/mobile number/i);
    expect(screen.queryByText("No account exists for that contact")).not.toBeInTheDocument();
  });
});

describe("the way to report an incident", () => {
  it("is on the sign-in card, for somebody with no account", async () => {
    render(<SignInPage />);
    const link = await screen.findByRole("link", { name: /Report a personal data incident/ });
    expect(link).toHaveAttribute("href", "/report-incident");
  });
});
