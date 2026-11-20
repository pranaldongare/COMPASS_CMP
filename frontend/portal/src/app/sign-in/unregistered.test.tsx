/**
 * A contact no account carries is told so, and taken to registration
 * (2026-11-16, the product owner's decision). The server answers the code
 * request `404 account_not_found`; sign-in and a consent link send the person
 * to sign-up with the contact filled in, and sign-up says why they are there.
 *
 * The contact is handed over in this tab's sessionStorage, never in the URL,
 * where it would stay in the history, the logs and a Referer (review SEC-6).
 */
import { HttpResponse, http } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import SignInPage from "@/app/sign-in/page";
import SignUpPage from "@/app/sign-up/page";
import { handOverContact } from "@/features/auth/contact-handover";
import { IdentifyStep } from "@/features/public-consent/components/identify-step";
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

const MOBILE = "+919876500001";
const EMAIL = "asha@example.org";
const TOKEN = "tok-example";

beforeEach(async () => {
  // The last test's sign-up was unmounted; what it took is forgotten a moment later.
  await new Promise((resolve) => setTimeout(resolve, 0));
  vi.restoreAllMocks();
  vi.clearAllMocks();
  nav.query = "";
  window.sessionStorage.clear();
});

/** Where the last navigation went, checked to carry no contact. */
function pushed(): string {
  const to = nav.push.mock.calls.at(-1)?.[0] as string;
  expect(to).toBeDefined();
  expect(to).not.toContain("contact");
  expect(to).not.toContain("9876500001");
  expect(decodeURIComponent(to)).not.toContain(EMAIL);
  return to;
}

/** Sign-up, opened at the address a navigation went to. */
function openSignUp(to: string) {
  nav.query = to.split("?")[1] ?? "";
  return render(<SignUpPage />);
}

function refuseAsUnknown() {
  server.use(
    http.post(`${API}/auth/otp/request`, () =>
      HttpResponse.json(
        {
          error: {
            code: "account_not_found",
            message:
              "No account exists for this mobile number or email address. Register first.",
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
  it("goes to sign-up without the contact in the URL, and never says a code is on its way", async () => {
    refuseAsUnknown();
    const { user } = render(<SignInPage />);
    await user.type(await screen.findByLabelText(/mobile number/i), MOBILE);
    await user.click(screen.getByRole("button", { name: "Send code" }));

    await vi.waitFor(() =>
      expect(nav.push).toHaveBeenCalledWith("/sign-up?unregistered=1"),
    );
    pushed();
    expect(screen.queryByText(/check your messages/i)).not.toBeInTheDocument();
  });

  it("keeps where the person was going", async () => {
    refuseAsUnknown();
    nav.query = "next=/my-requests";
    const { user } = render(<SignInPage />);
    await user.type(await screen.findByLabelText(/mobile number/i), MOBILE);
    await user.click(screen.getByRole("button", { name: "Send code" }));

    await vi.waitFor(() =>
      expect(nav.push).toHaveBeenCalledWith("/sign-up?unregistered=1&next=%2Fmy-requests"),
    );
    pushed();
  });

  it("arrives at sign-up with the mobile filled in and the notice", async () => {
    refuseAsUnknown();
    const signIn = render(<SignInPage />);
    await signIn.user.type(await screen.findByLabelText(/mobile number/i), MOBILE);
    await signIn.user.click(screen.getByRole("button", { name: "Send code" }));
    await vi.waitFor(() => expect(nav.push).toHaveBeenCalled());
    const to = pushed();
    signIn.unmount();

    openSignUp(to);
    expect(
      await screen.findByText("No account exists for that contact"),
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/mobile number/i)).toHaveValue(MOBILE);
    // Read once: nothing is left behind in the tab.
    expect(window.sessionStorage.length).toBe(0);
  });
});

describe("a consent link's contact nobody registered", () => {
  function refuseLinkAsUnknown() {
    server.use(
      http.post(`${API}/c/${TOKEN}/otp`, () =>
        HttpResponse.json(
          {
            error: {
              code: "account_not_found",
              message:
                "No account exists for this mobile number or email address. Register first.",
              field: "contact",
              request_id: "t",
            },
          },
          { status: 404 },
        ),
      ),
    );
  }

  it("goes to sign-up with the way back but not the contact, which is filled in there", async () => {
    refuseLinkAsUnknown();
    const onDone = vi.fn();
    const step = render(<IdentifyStep token={TOKEN} onDone={onDone} onError={vi.fn()} />);
    await step.user.click(screen.getByRole("radio", { name: "Email" }));
    await step.user.type(screen.getByLabelText(/email address/i), EMAIL);
    await step.user.click(screen.getByRole("button", { name: "Send the code" }));

    await vi.waitFor(() =>
      expect(nav.push).toHaveBeenCalledWith(
        `/sign-up?unregistered=1&next=${encodeURIComponent(`/c/${TOKEN}`)}`,
      ),
    );
    const to = pushed();
    expect(onDone).not.toHaveBeenCalled();
    step.unmount();

    openSignUp(to);
    expect(
      await screen.findByText(/you will need a mobile number too/),
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toHaveValue(EMAIL);
    expect(screen.getByLabelText(/mobile number/i)).toHaveValue("");
    expect(window.sessionStorage.length).toBe(0);
  });
});

describe("sign-up, reached that way", () => {
  it("says there is no account for the mobile, which is filled in", async () => {
    handOverContact(MOBILE, "sign-up");
    openSignUp("/sign-up?unregistered=1");

    expect(
      await screen.findByText("No account exists for that contact"),
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/mobile number/i)).toHaveValue(MOBILE);
  });

  it("ignores a contact put in the URL", async () => {
    openSignUp(`/sign-up?contact=${encodeURIComponent(MOBILE)}&unregistered=1`);
    await screen.findByLabelText(/mobile number/i);
    expect(screen.getByLabelText(/mobile number/i)).toHaveValue("");
    expect(
      screen.queryByText("No account exists for that contact"),
    ).not.toBeInTheDocument();
  });

  it("leaves the field empty when storage is blocked", async () => {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("blocked", "SecurityError");
    });
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("blocked", "SecurityError");
    });
    expect(() => handOverContact(MOBILE, "sign-up")).not.toThrow();
    openSignUp("/sign-up?unregistered=1");

    await screen.findByLabelText(/mobile number/i);
    expect(screen.getByLabelText(/mobile number/i)).toHaveValue("");
  });

  it("says nothing of the kind to somebody who came to register", async () => {
    render(<SignUpPage />);
    await screen.findByLabelText(/mobile number/i);
    expect(
      screen.queryByText("No account exists for that contact"),
    ).not.toBeInTheDocument();
  });
});

describe("sign-in, reached from sign-up", () => {
  it("fills in the mobile handed over, with nothing of it in the URL", async () => {
    handOverContact(MOBILE, "sign-in");
    nav.query = "prefill=1";
    render(<SignInPage />);

    expect(await screen.findByLabelText(/mobile number/i)).toHaveValue(MOBILE);
    expect(window.sessionStorage.length).toBe(0);
  });

  it("fills in an email as the email", async () => {
    handOverContact(EMAIL, "sign-in");
    nav.query = "prefill=1";
    render(<SignInPage />);

    expect(await screen.findByLabelText(/email address/i)).toHaveValue(EMAIL);
    expect(screen.getByRole("radio", { name: /email/i })).toBeChecked();
  });

  it("ignores a contact put in the URL", async () => {
    nav.query = `contact=${encodeURIComponent(MOBILE)}&prefill=1`;
    render(<SignInPage />);

    expect(await screen.findByLabelText(/mobile number/i)).toHaveValue("");
  });

  it("does not take what was handed to sign-up", async () => {
    handOverContact(MOBILE, "sign-up");
    nav.query = "prefill=1";
    render(<SignInPage />);

    expect(await screen.findByLabelText(/mobile number/i)).toHaveValue("");
    expect(window.sessionStorage.length).toBe(1);
  });
});

describe("the way to report an incident", () => {
  it("is on the sign-in card, for somebody with no account", async () => {
    render(<SignInPage />);
    const link = await screen.findByRole("link", {
      name: /Report a personal data incident/,
    });
    expect(link).toHaveAttribute("href", "/report-incident");
  });
});
