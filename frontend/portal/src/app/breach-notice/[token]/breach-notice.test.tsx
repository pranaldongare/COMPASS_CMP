/**
 * A breach notice by its link (2026-11-20): the link shows the reference and
 * the masked mobile; a code sent by text to that mobile opens the notice in
 * five headed sections; a bad link is one neutral screen; and nothing is
 * kept in the browser afterwards.
 */
import { HttpResponse, http } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import BreachNoticeLinkPage from "@/app/breach-notice/[token]/page";
import { render, screen } from "@/test/render";
import { API, server } from "@/test/server";

const TOKEN = "Ab3-_".repeat(12) + "Zz09"; // 64 characters, the link's alphabet
const nav = vi.hoisted(() => ({ token: "" }));

vi.mock("next/navigation", () => ({
  useParams: () => ({ token: nav.token }),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => `/breach-notice/${nav.token}`,
}));

const LINK = { reference: "BR-2026-000007", code_goes_to: "••••••••14" };

const NOTICE = {
  reference: "BR-2026-000007",
  version: 1,
  approved_at: "2026-11-19T09:00:00Z",
  what_happened: "A laptop holding a customer list was stolen on 12 November.",
  consequences: "Your name and mobile number may be seen by somebody else.",
  measures: "We have reported the theft and locked the laptop remotely.",
  protective_steps: "Be wary of calls or texts that claim to be from us.",
  contact: "Write to privacy@example.org or call the Privacy Office.",
};

function refusal(status: number, code: string, message: string) {
  return HttpResponse.json(
    { error: { code, message, field: status === 400 ? "code" : null, request_id: "t" } },
    { status },
  );
}

/** The link, a code, and the notice for 123456 only. */
function serve(notice: typeof NOTICE = NOTICE) {
  const asked = { codes: 0, opened: [] as string[] };
  server.use(
    http.get(`${API}/breach-notices/${TOKEN}`, () => HttpResponse.json(LINK)),
    http.post(`${API}/breach-notices/${TOKEN}/code`, () => {
      asked.codes += 1;
      return HttpResponse.json({
        ok: true,
        message: "A code is on its way to the mobile the notice was sent to.",
      });
    }),
    http.post(`${API}/breach-notices/${TOKEN}/open`, async ({ request }) => {
      const { code } = (await request.json()) as { code: string };
      asked.opened.push(code);
      return code === "123456"
        ? HttpResponse.json(notice)
        : refusal(400, "otp_invalid", "Invalid or expired code");
    }),
  );
  return asked;
}

beforeEach(() => {
  nav.token = TOKEN;
  window.sessionStorage.clear();
  window.localStorage.clear();
});
afterEach(() => server.resetHandlers());

describe("a breach notice by its link", () => {
  it("shows the reference and where the code goes, and nothing of the notice", async () => {
    serve();
    render(<BreachNoticeLinkPage />);

    expect(await screen.findByText(/BR-2026-000007/)).toBeInTheDocument();
    expect(screen.getByText("••••••••14")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send code" })).toBeInTheDocument();
    expect(screen.queryByText(NOTICE.what_happened)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/six-digit code/i)).not.toBeInTheDocument();
  });

  it("says the same neutral thing for a link the API does not know", async () => {
    server.use(
      http.get(`${API}/breach-notices/${TOKEN}`, () =>
        refusal(
          404,
          "not_found",
          "This link does not open a notice. Contact the Privacy Office.",
        ),
      ),
    );
    render(<BreachNoticeLinkPage />);

    expect(await screen.findByText("This link is not valid")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Send code" })).not.toBeInTheDocument();
  });

  it("does not ask about a link of the wrong shape", async () => {
    nav.token = "too-short";
    render(<BreachNoticeLinkPage />);
    // No handler for it: `onUnhandledRequest: "error"` fails the test if asked.
    expect(await screen.findByText("This link is not valid")).toBeInTheDocument();
  });

  it("sends a code, and sends another when asked", async () => {
    const asked = serve();
    const { user } = render(<BreachNoticeLinkPage />);

    await user.click(await screen.findByRole("button", { name: "Send code" }));
    expect(await screen.findByRole("status")).toHaveTextContent(/a code is on its way/i);
    expect(screen.getByLabelText(/six-digit code/i)).toBeInTheDocument();
    expect(asked.codes).toBe(1);

    await user.click(screen.getByRole("button", { name: "Resend code" }));
    await vi.waitFor(() => expect(asked.codes).toBe(2));
  });

  it("says when too many codes were asked for", async () => {
    serve();
    server.use(
      http.post(`${API}/breach-notices/${TOKEN}/code`, () =>
        refusal(429, "rate_limited", "Too many codes for this notice. Try again later."),
      ),
    );
    const { user } = render(<BreachNoticeLinkPage />);
    await user.click(await screen.findByRole("button", { name: "Send code" }));

    expect(await screen.findByText(/too many codes/i)).toBeInTheDocument();
  });

  it("refuses a wrong code and shows nothing of the notice", async () => {
    const asked = serve();
    const { user } = render(<BreachNoticeLinkPage />);
    await user.click(await screen.findByRole("button", { name: "Send code" }));
    await user.type(await screen.findByLabelText(/six-digit code/i), "999999");
    await user.click(screen.getByRole("button", { name: "Open the notice" }));

    expect(await screen.findByText("Invalid or expired code")).toBeInTheDocument();
    expect(asked.opened).toEqual(["999999"]);
    expect(screen.queryByText(NOTICE.what_happened)).not.toBeInTheDocument();
  });

  it("opens the notice in five headed sections with the right code, keeping nothing", async () => {
    serve();
    const { user } = render(<BreachNoticeLinkPage />);
    await user.click(await screen.findByRole("button", { name: "Send code" }));
    await user.type(await screen.findByLabelText(/six-digit code/i), "123456");
    await user.click(screen.getByRole("button", { name: "Open the notice" }));

    const headings = await screen.findAllByRole("heading", { level: 3 });
    expect(headings.map((h) => h.textContent)).toEqual([
      "What happened",
      "What it may mean for you",
      "What we have done, and are doing",
      "What you can do",
      "Questions",
    ]);
    expect(screen.getByText(NOTICE.what_happened)).toBeInTheDocument();
    expect(screen.getByText(NOTICE.consequences)).toBeInTheDocument();
    expect(screen.getByText(NOTICE.measures)).toBeInTheDocument();
    expect(screen.getByText(NOTICE.protective_steps)).toBeInTheDocument();
    expect(screen.getByText(NOTICE.contact)).toBeInTheDocument();
    expect(screen.getByText(/Breach BR-2026-000007/)).toBeInTheDocument();

    // Neither the notice nor the code is kept in the browser.
    expect(window.sessionStorage.length).toBe(0);
    expect(window.localStorage.length).toBe(0);

    // Closing it leaves the page with the reference and a new code to ask for.
    await user.click(screen.getByRole("button", { name: /close the notice/i }));
    expect(screen.queryByText(NOTICE.what_happened)).not.toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Send code" })).toBeInTheDocument();
  });

  it("goes to the neutral screen if the link stops working between steps", async () => {
    serve();
    server.use(
      http.post(`${API}/breach-notices/${TOKEN}/code`, () =>
        refusal(
          404,
          "not_found",
          "This link does not open a notice. Contact the Privacy Office.",
        ),
      ),
    );
    const { user } = render(<BreachNoticeLinkPage />);
    await user.click(await screen.findByRole("button", { name: "Send code" }));

    expect(await screen.findByText("This link is not valid")).toBeInTheDocument();
  });
});

describe("a notice that arrives sealed", () => {
  // A FREE_TEXT envelope, as `lib/api/client.test.ts` uses.
  const SEALED = "SE::REsBCgS0cnTQzT85P3501uluS_bXRiQF1c8uF94TUKuGxiEq0MEpbf3SQcg5";

  async function openIt() {
    const { user } = render(<BreachNoticeLinkPage />);
    await user.click(await screen.findByRole("button", { name: "Send code" }));
    await user.type(await screen.findByLabelText(/six-digit code/i), "123456");
    await user.click(screen.getByRole("button", { name: "Open the notice" }));
  }

  it("is shown opened when the portal can open it", async () => {
    serve({ ...NOTICE, what_happened: SEALED });
    server.use(
      http.post("/dkms/decrypt", async ({ request }) => {
        const body = (await request.json()) as { data: Record<string, string>[] };
        return HttpResponse.json({
          data: body.data.map((r) =>
            Object.fromEntries(Object.keys(r).map((t) => [t, NOTICE.what_happened])),
          ),
        });
      }),
    );
    await openIt();

    expect(await screen.findByText(NOTICE.what_happened)).toBeInTheDocument();
    expect(screen.queryByText(SEALED)).not.toBeInTheDocument();
  });

  it("is not shown as base64 when it cannot be opened", async () => {
    serve({ ...NOTICE, what_happened: SEALED });
    server.use(
      http.post("/dkms/decrypt", () =>
        HttpResponse.json({ error: "not signed in" }, { status: 401 }),
      ),
    );
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    await openIt();

    expect(await screen.findByText(/could not be shown just now/i)).toBeInTheDocument();
    expect(screen.queryByText(SEALED)).not.toBeInTheDocument();
    expect(screen.queryByText(NOTICE.consequences)).not.toBeInTheDocument();
  });
});
