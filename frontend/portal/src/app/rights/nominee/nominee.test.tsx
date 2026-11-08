/**
 * The nominee's request page, once a code is cancelled (2026-11-08).
 *
 * `POST /rights/nominee/requests` refuses a wrong code, an expired one and one
 * cancelled by its fifth wrong try in the same sentence, to everybody. The
 * fifth used to answer "Too many incorrect attempts. Request a new code.", and
 * the page then had no way to one: the first step is locked once it has run,
 * and a reload loses the request text and the evidence. So the page says, to
 * everybody alike, how long a code lasts, and asks for a new one with the
 * details already typed, keeping the rest.
 */
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";

import NomineePage from "@/app/rights/nominee/page";
import { render, screen } from "@/test/render";
import { API, errorResponse, server } from "@/test/server";

const NOMINATION = "6f1c2a7e-3b4d-4e5f-8a9b-0c1d2e3f4a5b";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(`nomination=${NOMINATION}`),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/rights/nominee",
}));

const STARTED =
  "If that nomination is in place and the contact matches the one recorded, a verification code has been sent to it.";
const HINT =
  "A code expires in ten minutes, or after five wrong tries; then send a new one.";

/**
 * The fields of a multipart body.
 *
 * Read by hand: undici's own parser refuses the body jsdom's FormData writes.
 * A file's part is there, but not its name or bytes, which undici cannot read
 * from jsdom's File as a browser would; so only that it was sent is checked.
 */
function multipart(body: string): Record<string, string> {
  const out: Record<string, string> = {};
  for (const part of body.split(/\r\n-+formdata[^\r]*\r\n?/)) {
    const name = /name="([^"]+)"/.exec(part)?.[1];
    if (name) out[name] = part.slice(part.indexOf("\r\n\r\n") + 4).replace(/\r\n$/, "");
  }
  return out;
}

describe("the nominee's request", () => {
  it("says that five wrong tries cancel a code, and sends a new one keeping the request", async () => {
    const started: unknown[] = [];
    const sent: Array<Record<string, string>> = [];
    server.use(
      http.post(`${API}/rights/nominee/start`, async ({ request }) => {
        started.push(await request.json());
        return HttpResponse.json({ ok: true, message: STARTED });
      }),
      http.post(`${API}/rights/nominee/requests`, async ({ request }) => {
        sent.push(multipart(await request.text()));
        return errorResponse("otp_invalid", "Invalid or expired code", 400, {
          field: "code",
        });
      }),
    );
    const { user } = render(<NomineePage />);

    await user.type(screen.getByLabelText(/your email or mobile/i), "nominee@example.org");
    await user.click(screen.getByRole("button", { name: "Send me a code" }));

    expect(await screen.findByText(STARTED)).toBeInTheDocument();
    expect(screen.getByText(HINT)).toBeInTheDocument();

    const code = screen.getByLabelText(/the code we sent/i);
    // Digits only: a stray space or letter is not sent for the schema to refuse.
    await user.type(code, "12 34a56");
    expect(code).toHaveValue("123456");
    await user.type(
      screen.getByLabelText(/^the request/i),
      "Everything you hold about them, please.",
    );
    await user.upload(
      screen.getByLabelText(/evidence/i),
      new File(["%PDF-1.4"], "certificate.pdf", { type: "application/pdf" }),
    );
    await user.click(screen.getByRole("button", { name: "Record the request" }));

    expect(await screen.findByText("Invalid or expired code")).toBeInTheDocument();
    expect(sent[0]).toMatchObject({
      code: "123456",
      request_text: "Everything you hold about them, please.",
    });
    expect(sent[0]).toHaveProperty("evidence");
    expect(screen.getByText(HINT)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Send me a new code" }));

    expect(
      await screen.findByText(
        "If the details match, a new code is on its way, and the earlier one no longer works.",
      ),
    ).toBeInTheDocument();
    expect(started).toEqual([
      { nomination_uuid: NOMINATION, contact: "nominee@example.org" },
      { nomination_uuid: NOMINATION, contact: "nominee@example.org" },
    ]);
    expect(screen.queryByText("Invalid or expired code")).not.toBeInTheDocument();
    expect(code).toHaveValue("");
    expect(screen.getByLabelText(/^the request/i)).toHaveValue(
      "Everything you hold about them, please.",
    );
    expect(screen.getByText(/certificate\.pdf/)).toBeInTheDocument();

    await user.type(code, "654321");
    await user.click(screen.getByRole("button", { name: "Record the request" }));
    expect(await screen.findByText("Invalid or expired code")).toBeInTheDocument();
    expect(sent[1]).toMatchObject({
      code: "654321",
      request_text: "Everything you hold about them, please.",
    });
    expect(sent[1]).toHaveProperty("evidence");
  });

  it("shows the server's words when a new code cannot be asked for", async () => {
    let calls = 0;
    server.use(
      http.post(`${API}/rights/nominee/start`, () => {
        calls += 1;
        return calls === 1
          ? HttpResponse.json({ ok: true, message: STARTED })
          : errorResponse("rate_limited", "Too many requests. Try again later.", 429);
      }),
    );
    const { user } = render(<NomineePage />);

    await user.type(screen.getByLabelText(/your email or mobile/i), "nominee@example.org");
    await user.click(screen.getByRole("button", { name: "Send me a code" }));
    await screen.findByText(STARTED);
    await user.click(screen.getByRole("button", { name: "Send me a new code" }));

    expect(
      await screen.findByText("Too many requests. Try again later."),
    ).toBeInTheDocument();
    expect(screen.queryByText(/a new code is on its way/i)).not.toBeInTheDocument();
  });

  it("goes back to the first step with the request text kept", async () => {
    server.use(
      http.post(`${API}/rights/nominee/start`, () =>
        HttpResponse.json({ ok: true, message: STARTED }),
      ),
    );
    const { user } = render(<NomineePage />);

    const contact = screen.getByLabelText(/your email or mobile/i);
    await user.type(contact, "nominee@example.org");
    await user.click(screen.getByRole("button", { name: "Send me a code" }));
    await user.type(await screen.findByLabelText(/^the request/i), "Everything, please.");
    expect(contact).toBeDisabled();

    await user.click(screen.getByRole("button", { name: "Change the details" }));

    expect(contact).toBeEnabled();
    expect(screen.queryByLabelText(/^the request/i)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Send me a code" }));
    expect(await screen.findByLabelText(/^the request/i)).toHaveValue(
      "Everything, please.",
    );
  });
});
