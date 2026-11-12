/**
 * The public report (2026-11-06): nothing goes until the form is complete, the
 * code goes to the address typed, and a wrong code costs the person nothing
 * they typed.
 */
import { describe, expect, it, vi } from "vitest";

import { ReportForm } from "@/features/report-incident/components/report-form";
import { render, screen, waitFor } from "@/test/render";
import { API, errorResponse, HttpResponse, http, server } from "@/test/server";

const RECEIPT = { reference: "INC-2026-0042", message: "Thank you." };

type Body = Record<string, unknown>;

/** Answers a code and a report, and keeps what each was sent. */
function anAcceptingServer() {
  const sent = { codes: [] as Body[], reports: [] as Body[] };
  server.use(
    http.post(`${API}/incident-reports/code`, async ({ request }) => {
      sent.codes.push((await request.json()) as Body);
      return HttpResponse.json({ message: "A code is on its way to this email address." });
    }),
    http.post(`${API}/incident-reports`, async ({ request }) => {
      sent.reports.push((await request.json()) as Body);
      return HttpResponse.json(RECEIPT, { status: 201 });
    }),
  );
  return sent;
}

type User = ReturnType<typeof render>["user"];

async function fillTheRequiredBoxes(user: User) {
  await user.type(screen.getByLabelText(/your name/i), "Asha Rao");
  await user.type(screen.getByLabelText(/your email/i), "Asha@Example.org");
  await user.type(screen.getByLabelText(/what happened in one line/i), "A laptop was stolen");
  await user.type(screen.getByLabelText(/^what happened\s*\*?$/i), "From a car, on Tuesday.");
}

async function pressSendCode(user: User) {
  await user.click(screen.getByRole("button", { name: "Send code" }));
  return screen.findByLabelText(/the code we sent/i);
}

describe("ReportForm", () => {
  it("sends nothing until the four required boxes are filled", async () => {
    const sent = anAcceptingServer();
    const { user } = render(<ReportForm onDone={() => {}} />);
    await user.click(screen.getByRole("button", { name: "Send code" }));

    expect(await screen.findByText(/give your name/i)).toBeInTheDocument();
    expect(screen.getByText(/an email address is required/i)).toBeInTheDocument();
    expect(screen.getByText(/say in a line what happened/i)).toBeInTheDocument();
    expect(screen.getByText(/^say what happened/i)).toBeInTheDocument();
    expect(sent.codes).toEqual([]);
  });

  it("sends a code to the address, then the report with it", async () => {
    const sent = anAcceptingServer();
    const onDone = vi.fn();
    const { user } = render(<ReportForm onDone={onDone} />);
    await fillTheRequiredBoxes(user);
    expect(screen.queryByLabelText(/the code we sent/i)).not.toBeInTheDocument();

    const code = await pressSendCode(user);
    expect(sent.codes).toEqual([{ email: "asha@example.org" }]);
    expect(sent.reports).toEqual([]);
    expect(screen.getByText(/on its way/i)).toBeInTheDocument();
    expect(code).toHaveFocus();

    await user.type(code, "123456");
    await user.click(screen.getByRole("button", { name: /send the report/i }));
    await waitFor(() => expect(onDone).toHaveBeenCalledWith(RECEIPT));
    expect(sent.reports).toEqual([
      {
        name: "Asha Rao",
        email: "asha@example.org",
        code: "123456",
        title: "A laptop was stolen",
        incident_details: "From a car, on Tuesday.",
        noticed_at: null,
        origin: null,
        discovery: null,
        affected_systems: null,
        impact_scale: null,
        countries_involved: null,
        data_nature: null,
        subject_types: null,
        entities_involved: null,
        third_parties: null,
        cyber_attack: null,
      },
    ]);
  });

  it("sends the optional details and the time, with its offset", async () => {
    const sent = anAcceptingServer();
    const onDone = vi.fn();
    const { user } = render(<ReportForm onDone={onDone} />);
    await fillTheRequiredBoxes(user);
    await user.type(screen.getByLabelText(/when did you notice it/i), "2026-11-02T09:30");
    await user.click(screen.getByText(/more details \(optional\)/i));
    await user.type(screen.getByLabelText(/where it started/i), "The sales team");
    await user.type(screen.getByLabelText(/kinds of personal data/i), "Names and mobiles");
    await user.click(screen.getByRole("radio", { name: /not sure/i }));

    await user.type(await pressSendCode(user), "123456");
    await user.click(screen.getByRole("button", { name: /send the report/i }));
    await waitFor(() => expect(onDone).toHaveBeenCalled());
    expect(sent.reports[0]).toMatchObject({
      noticed_at: new Date("2026-11-02T09:30").toISOString(),
      origin: "The sales team",
      data_nature: "Names and mobiles",
      cyber_attack: "unknown",
      discovery: null,
    });
  });

  it("says a time in the future is one, before asking for a code", async () => {
    const sent = anAcceptingServer();
    const { user } = render(<ReportForm onDone={() => {}} />);
    await fillTheRequiredBoxes(user);
    await user.type(screen.getByLabelText(/when did you notice it/i), "2099-01-01T09:30");
    await user.click(screen.getByRole("button", { name: "Send code" }));
    expect(await screen.findByText(/this time is in the future/i)).toBeInTheDocument();
    expect(sent.codes).toEqual([]);
  });

  it("asks for the code before sending the report", async () => {
    const sent = anAcceptingServer();
    const { user } = render(<ReportForm onDone={() => {}} />);
    await fillTheRequiredBoxes(user);
    await pressSendCode(user);
    await user.click(screen.getByRole("button", { name: /send the report/i }));
    expect(await screen.findByText(/enter the code we sent you/i)).toBeInTheDocument();
    expect(sent.reports).toEqual([]);
  });

  it("keeps everything typed when the code is wrong", async () => {
    let tries = 0;
    anAcceptingServer();
    server.use(
      http.post(`${API}/incident-reports`, () => {
        tries += 1;
        return tries === 1
          ? errorResponse("otp_invalid", "Invalid or expired code", 400, { field: "code" })
          : HttpResponse.json(RECEIPT, { status: 201 });
      }),
    );
    const onDone = vi.fn();
    const { user } = render(<ReportForm onDone={onDone} />);
    await fillTheRequiredBoxes(user);
    const code = await pressSendCode(user);
    await user.type(code, "000000");
    await user.click(screen.getByRole("button", { name: /send the report/i }));

    expect(await screen.findByText(/invalid or expired code/i)).toBeInTheDocument();
    expect(onDone).not.toHaveBeenCalled();
    expect(screen.getByLabelText(/your name/i)).toHaveValue("Asha Rao");
    expect(screen.getByLabelText(/what happened in one line/i)).toHaveValue("A laptop was stolen");
    expect(screen.getByLabelText(/^what happened\s*\*?$/i)).toHaveValue("From a car, on Tuesday.");

    await user.clear(code);
    await user.type(code, "123456");
    await user.click(screen.getByRole("button", { name: /send the report/i }));
    await waitFor(() => expect(onDone).toHaveBeenCalledWith(RECEIPT));
  });

  it("sends a new code past whatever is in the box", async () => {
    const sent = anAcceptingServer();
    const { user } = render(<ReportForm onDone={() => {}} />);
    await fillTheRequiredBoxes(user);
    const code = await pressSendCode(user);
    await user.type(code, "abc");
    await user.click(screen.getByRole("button", { name: /send a new code/i }));
    expect(await screen.findByText(/we have sent a new code/i)).toBeInTheDocument();
    expect(sent.codes).toHaveLength(2);
    expect(code).toHaveValue("");
  });

  it("goes back to the first step when the address changes", async () => {
    anAcceptingServer();
    const { user } = render(<ReportForm onDone={() => {}} />);
    await fillTheRequiredBoxes(user);
    await pressSendCode(user);
    await user.type(screen.getByLabelText(/your email/i), "m");
    expect(screen.queryByLabelText(/the code we sent/i)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send code" })).toBeInTheDocument();
  });

  it("lets a stray letter in the code box go with the address it was for", async () => {
    const sent = anAcceptingServer();
    const { user } = render(<ReportForm onDone={() => {}} />);
    await fillTheRequiredBoxes(user);
    await user.type(await pressSendCode(user), "abc");
    await user.type(screen.getByLabelText(/your email/i), "m");

    await user.click(screen.getByRole("button", { name: "Send code" }));
    const code = await screen.findByLabelText(/the code we sent/i);
    expect(sent.codes).toEqual([{ email: "asha@example.org" }, { email: "asha@example.orgm" }]);
    expect(code).toHaveValue("");
  });

  it("shows a refused code request beside the buttons, and how long to wait", async () => {
    const scroll = vi.fn();
    Element.prototype.scrollIntoView = scroll;
    server.use(
      http.post(`${API}/incident-reports/code`, () =>
        errorResponse("rate_limited", "Too many codes for this address. Try again later.", 429, {
          retry_after_s: 600,
        }),
      ),
    );
    const { user, container } = render(<ReportForm onDone={() => {}} />);
    await fillTheRequiredBoxes(user);
    const button = screen.getByRole("button", { name: "Send code" });
    await user.click(button);
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/too many codes.*about 10 minutes/i);
    expect(screen.getByLabelText(/your name/i)).toHaveValue("Asha Rao");

    // Below everything that can be typed in, and right above the button.
    const follows = (a: Element, b: Element) =>
      Boolean(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);
    expect(follows(container.querySelector("details") as Element, alert)).toBe(true);
    expect(follows(alert, button)).toBe(true);

    // It pushes the button down, so it is brought back into view as well.
    expect(scroll).toHaveBeenCalledWith({ block: "center" });
  });

  it("shows a refused report beside the buttons too, below the code", async () => {
    Element.prototype.scrollIntoView = vi.fn();
    anAcceptingServer();
    server.use(
      http.post(`${API}/incident-reports`, () => errorResponse("server_error", "Something failed", 500)),
    );
    const { user } = render(<ReportForm onDone={() => {}} />);
    await fillTheRequiredBoxes(user);
    const code = await pressSendCode(user);
    await user.type(code, "123456");
    const button = screen.getByRole("button", { name: /send the report/i });
    await user.click(button);

    const alert = (await screen.findAllByRole("alert")).at(-1) as Element;
    expect(code.compareDocumentPosition(alert) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(alert.compareDocumentPosition(button) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("opens the fold when the server faults a field inside it", async () => {
    anAcceptingServer();
    server.use(
      http.post(`${API}/incident-reports`, () =>
        errorResponse("validation_failed", "Too long", 422, { field: "origin" }),
      ),
    );
    const { user, container } = render(<ReportForm onDone={() => {}} />);
    const fold = container.querySelector("details");
    expect(fold).not.toHaveAttribute("open");
    await fillTheRequiredBoxes(user);
    await user.type(await pressSendCode(user), "123456");
    await user.click(screen.getByRole("button", { name: /send the report/i }));
    expect(await screen.findByText(/too long/i)).toBeInTheDocument();
    expect(fold).toHaveAttribute("open");
  });
});
