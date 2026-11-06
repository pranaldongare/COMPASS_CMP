/**
 * Breach tickets in the console (S3-08): the office's card, and the holder's.
 *
 * Every control comes from the server: the card offers assigning only once
 * the breach is recorded, a ticket's moves are the ones the server returned,
 * and a holder is offered the return only while the server says so.
 *
 * S3-09: the office can ask somebody with no console login by email, sees
 * whose login is temporary, and a holder can bring in a colleague.
 *
 * 2026-11-06: a document can go with the ticket as it is raised, and either
 * side can move the date with a reason, while the server allows it. The test
 * DOM's File loses its name on the way into a request, so the text is checked.
 */
import { HttpResponse, http } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ATTACHMENT_ACCEPT } from "@/features/breach/components/attachments";
import { BreachTicketCard } from "@/features/breach/components/my-breach-tickets";
import { TicketsCard } from "@/features/breach/components/tickets-card";
import { formatDate } from "@/lib/format";
import { keys } from "@/lib/query";
import { act, render, screen, within } from "@/test/render";
import { API, server } from "@/test/server";
import type { Breach, BreachTicket, MyBreachTicket } from "@/types";

const toast = vi.hoisted(() => ({ success: vi.fn(), error: vi.fn(), warning: vi.fn() }));
vi.mock("@/providers", () => ({ useToast: () => toast }));

const BREACH = "66666666-6666-4666-8666-666666666666";
const TICKET = "77777777-7777-4777-8777-777777777777";

/** A multipart field as the request carries it. */
const field = (body: string, name: string) =>
  new RegExp(`name="${name}"\r\n\r\n([^\r]*)`).exec(body)?.[1] ?? null;

const NEXT_YEAR = `${new Date().getFullYear() + 1}-01-15`;

const breach = (recorded: boolean) =>
  ({
    breach_uuid: BREACH,
    status: "open",
    reference: recorded ? "BR-2026-0007" : "INC-2026-0007",
    incident_reference: "INC-2026-0007",
    breach_reference: recorded ? "BR-2026-0007" : null,
  }) as Breach;

const ticket = (over: Partial<BreachTicket> = {}): BreachTicket => ({
  ticket_uuid: TICKET,
  holder_uuid: "88888888-8888-4888-8888-888888888888",
  holder_name: "Arun Shetty",
  assigned_by_name: "Priya Menon",
  parent_ticket_uuid: null,
  added_by_name: null,
  state: "returned",
  answer_by: null,
  overdue: false,
  created_at: "2026-10-05T10:00:00Z",
  unread: 2,
  last_activity_at: "2026-10-05T11:00:00Z",
  events: [],
  moves: [
    { move: "send_back", reason_required: true },
    { move: "close", reason_required: false },
    { move: "withdraw", reason_required: true },
  ],
  may_write: true,
  may_change_date: true,
  temporary_access: null,
  ...over,
});

beforeEach(() => {
  vi.clearAllMocks();
});

const DOWN = { error: { code: "unavailable", message: "Down for a moment" } };

describe("TicketsCard", () => {
  it("waits for the breach to be recorded before anyone is asked", async () => {
    server.use(http.get(`${API}/breaches/${BREACH}/tickets`, () => HttpResponse.json([])));
    render(<TicketsCard breach={breach(false)} />);

    expect(await screen.findByText("Tickets wait for the breach to be recorded")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /assign a ticket/i })).not.toBeInTheDocument();
  });

  it("lists each ticket and offers exactly the moves the server returned", async () => {
    server.use(
      http.get(`${API}/breaches/${BREACH}/tickets`, () => HttpResponse.json([ticket()])),
      http.get(`${API}/breaches/${BREACH}/tickets/${TICKET}`, () =>
        HttpResponse.json({ ticket: ticket({ unread: 0 }), instruction: "Export the log", messages: [] }),
      ),
    );
    const { user } = render(<TicketsCard breach={breach(true)} />);

    const row = (await screen.findByText("Arun Shetty")).closest("tr") as HTMLElement;
    expect(within(row).getByText("Returned")).toBeInTheDocument();
    expect(within(row).getByText("2 new")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /assign a ticket/i })).toBeInTheDocument();

    await user.click(within(row).getByRole("button", { name: /open/i }));
    const dialog = await screen.findByRole("dialog");
    for (const name of ["Send back", "Close the ticket", "Withdraw"]) {
      expect(await within(dialog).findByRole("button", { name })).toBeInTheDocument();
    }
    expect(within(dialog).queryByRole("button", { name: "Reopen" })).not.toBeInTheDocument();
  });

  it("marks a temporary login and its state", async () => {
    server.use(
      http.get(`${API}/breaches/${BREACH}/tickets`, () =>
        HttpResponse.json([
          ticket({ temporary_access: "pending" }),
          ticket({ ticket_uuid: BREACH, holder_name: "Meera Iyer", temporary_access: "ended" }),
        ]),
      ),
    );
    render(<TicketsCard breach={breach(true)} />);

    const pending = (await screen.findByText("Arun Shetty")).closest("tr") as HTMLElement;
    expect(within(pending).getByText("Temporary login · not yet signed in")).toBeInTheDocument();
    const ended = screen.getByText("Meera Iyer").closest("tr") as HTMLElement;
    expect(within(ended).getByText("Temporary login · read only")).toBeInTheDocument();
  });

  it("asks somebody without a console login by name and email", async () => {
    let sent: unknown = null;
    server.use(
      http.get(`${API}/breaches/${BREACH}/tickets`, () => HttpResponse.json([])),
      http.get(`${API}/users`, () => HttpResponse.json({ items: [], total: 0, page: 1, page_size: 25 })),
      http.post(`${API}/breaches/${BREACH}/tickets`, async ({ request }) => {
        sent = await request.json();
        return HttpResponse.json({ ticket: ticket({ temporary_access: "pending" }), instruction: "x", messages: [] });
      }),
    );
    const { user } = render(<TicketsCard breach={breach(true)} />);

    await user.click(await screen.findByRole("button", { name: /assign a ticket/i }));
    const dialog = await screen.findByRole("dialog");
    await user.click(within(dialog).getByLabelText("Someone without a console login"));
    await user.type(within(dialog).getByLabelText(/their name/i), "Meera Iyer");
    await user.type(within(dialog).getByLabelText(/their work email/i), "meera@cmp.local");
    await user.type(within(dialog).getByLabelText(/what you are asking/i), "Pull the badge log");
    await user.click(within(dialog).getByRole("button", { name: "Assign" }));

    await vi.waitFor(() =>
      expect(sent).toEqual({
        full_name: "Meera Iyer",
        email: "meera@cmp.local",
        mobile: null,
        instruction: "Pull the badge log",
        answer_by: null,
      }),
    );
    expect(toast.success).toHaveBeenCalledWith("Ticket assigned", expect.any(String));
  });

  /** Everything up to the Assign button, for a member of staff. */
  async function raise(user: ReturnType<typeof render>["user"]) {
    await user.click(await screen.findByRole("button", { name: /assign a ticket/i }));
    const dialog = await screen.findByRole("dialog");
    await within(dialog).findByRole("option", { name: /Arun Shetty/ });
    await user.selectOptions(within(dialog).getByLabelText(/^Who/), "88888888-8888-4888-8888-888888888888");
    await user.type(within(dialog).getByLabelText(/what you are asking/i), "Pull the badge log");
    return dialog;
  }

  function serveRaising(message: Parameters<typeof http.post>[1]) {
    server.use(
      http.get(`${API}/breaches/${BREACH}/tickets`, () => HttpResponse.json([])),
      http.get(`${API}/users`, () =>
        HttpResponse.json({
          items: [
            {
              uuid: "88888888-8888-4888-8888-888888888888",
              full_name: "Arun Shetty",
              email: "arun@cmp.local",
              role: "dco",
            },
          ],
          total: 1,
          page: 1,
          page_size: 25,
        }),
      ),
      http.post(`${API}/breaches/${BREACH}/tickets`, () =>
        HttpResponse.json({ ticket: ticket({ state: "issued" }), instruction: "x", messages: [] }),
      ),
      http.post(`${API}/breaches/${BREACH}/tickets/${TICKET}/messages`, message),
    );
  }

  it("sends a document chosen while raising the ticket as its first message", async () => {
    let body = "";
    serveRaising(async ({ request }) => {
      body = await request.text();
      return HttpResponse.json({ ticket: ticket(), instruction: "x", messages: [] });
    });
    const { user } = render(<TicketsCard breach={breach(true)} />);

    const dialog = await raise(user);
    await user.upload(
      within(dialog).getByLabelText(/attach a document/i),
      new File(["%PDF-1.4"], "scope.pdf", { type: "application/pdf" }),
    );
    await user.click(within(dialog).getByRole("button", { name: "Assign" }));

    await vi.waitFor(() => expect(body).not.toBe(""));
    expect(field(body, "body")).toBe("Document attached when this ticket was raised.");
    expect(body).toContain('name="evidence"');
    await vi.waitFor(() => expect(toast.success).toHaveBeenCalledWith("Ticket assigned", expect.any(String)));
    expect(toast.warning).not.toHaveBeenCalled();
  });

  it("offers what the thread takes, and sends no message when no document is chosen", async () => {
    let messages = 0;
    serveRaising(() => {
      messages += 1;
      return HttpResponse.json({ ticket: ticket(), instruction: "x", messages: [] });
    });
    const { user } = render(<TicketsCard breach={breach(true)} />);

    const dialog = await raise(user);
    const picker = within(dialog).getByLabelText(/attach a document/i);
    expect(picker).toHaveAttribute("accept", ATTACHMENT_ACCEPT);
    expect(picker.getAttribute("accept")).toContain(".docx");
    expect(within(dialog).getByText(/PDF, Word, image, saved email, CSV or text/)).toBeInTheDocument();
    await user.click(within(dialog).getByRole("button", { name: "Assign" }));

    await vi.waitFor(() => expect(toast.success).toHaveBeenCalled());
    expect(messages).toBe(0);
  });

  it("says the ticket stands when its document is refused", async () => {
    serveRaising(() =>
      HttpResponse.json(
        { error: { code: "validation_failed", message: "Evidence must be a PDF, an image or text" } },
        { status: 422 },
      ),
    );
    const { user } = render(<TicketsCard breach={breach(true)} />);

    const dialog = await raise(user);
    await user.upload(
      within(dialog).getByLabelText(/attach a document/i),
      new File(["x"], "notes.txt", { type: "text/plain" }),
    );
    await user.click(within(dialog).getByRole("button", { name: "Assign" }));

    await vi.waitFor(() =>
      expect(toast.warning).toHaveBeenCalledWith(
        "Ticket assigned, but the document was not attached",
        "Evidence must be a PDF, an image or text. Attach it on the ticket.",
      ),
    );
    expect(toast.success).not.toHaveBeenCalled();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("calls the date Resolve by on the list and on the ticket", async () => {
    const dated = ticket({ answer_by: "2026-11-20" });
    server.use(
      http.get(`${API}/breaches/${BREACH}/tickets`, () => HttpResponse.json([dated])),
      http.get(`${API}/breaches/${BREACH}/tickets/${TICKET}`, () =>
        HttpResponse.json({ ticket: dated, instruction: "x", messages: [] }),
      ),
    );
    const { user } = render(<TicketsCard breach={breach(true)} />);

    expect(await screen.findByRole("columnheader", { name: "Resolve by" })).toBeInTheDocument();
    expect(screen.queryByText("Answer by")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /open/i }));
    const dialog = await screen.findByRole("dialog");
    expect(await within(dialog).findByText(/^Resolve by /)).toBeInTheDocument();
  });

  it("keeps what is being typed through a failed read of the ticket", async () => {
    server.use(
      http.get(`${API}/breaches/${BREACH}/tickets`, () => HttpResponse.json([ticket()])),
      http.get(`${API}/breaches/${BREACH}/tickets/${TICKET}`, () =>
        HttpResponse.json({ ticket: ticket(), instruction: "x", messages: [] }),
      ),
    );
    const { user, queryClient } = render(<TicketsCard breach={breach(true)} />);

    await user.click(await screen.findByRole("button", { name: /open/i }));
    const dialog = await screen.findByRole("dialog");
    await user.type(await within(dialog).findByLabelText("Message"), "Typed, not sent");

    server.use(http.get(`${API}/breaches/${BREACH}/tickets/${TICKET}`, () => HttpResponse.json(DOWN, { status: 503 })));
    await act(async () => {
      await queryClient.refetchQueries({ queryKey: keys.breach.ticket(BREACH, TICKET) });
      await new Promise((resolve) => setTimeout(resolve, 10));
    });

    expect(queryClient.getQueryState(keys.breach.ticket(BREACH, TICKET))?.status).toBe("error");
    expect(within(dialog).queryByText("Down for a moment")).not.toBeInTheDocument();
    expect(within(dialog).getByLabelText("Message")).toHaveValue("Typed, not sent");
  });

  it("says so when the ticket cannot be read at all", async () => {
    server.use(
      http.get(`${API}/breaches/${BREACH}/tickets`, () => HttpResponse.json([ticket()])),
      http.get(`${API}/breaches/${BREACH}/tickets/${TICKET}`, () => HttpResponse.json(DOWN, { status: 503 })),
    );
    const { user } = render(<TicketsCard breach={breach(true)} />);

    await user.click(await screen.findByRole("button", { name: /open/i }));

    expect(await within(await screen.findByRole("dialog")).findByText("Down for a moment")).toBeInTheDocument();
  });

  it("moves the date with a reason, and shows the trail the server keeps", async () => {
    let sent: unknown = null;
    const moved = {
      message_uuid: "99999999-9999-4999-8999-999999999999",
      kind: "status",
      author_side: "office",
      author_name: "Priya Menon",
      body: "Resolve by changed from no date to 15 January: The vendor needs a week",
      created_at: "2026-11-06T10:00:00Z",
      evidence_hash: null,
      evidence_name: null,
    };
    server.use(
      http.get(`${API}/breaches/${BREACH}/tickets`, () => HttpResponse.json([ticket()])),
      http.get(`${API}/breaches/${BREACH}/tickets/${TICKET}`, () =>
        HttpResponse.json({ ticket: ticket(), instruction: "x", messages: sent ? [moved] : [] }),
      ),
      http.post(`${API}/breaches/${BREACH}/tickets/${TICKET}/resolve-by`, async ({ request }) => {
        sent = await request.json();
        return HttpResponse.json({ ticket: ticket(), instruction: "x", messages: [moved] });
      }),
    );
    const { user } = render(<TicketsCard breach={breach(true)} />);

    await user.click(await screen.findByRole("button", { name: /open/i }));
    const dialog = await screen.findByRole("dialog");
    await user.click(await within(dialog).findByRole("button", { name: "Change the date" }));
    expect(within(dialog).getByText(/^The holder is told\. The old date, the new date/)).toBeInTheDocument();
    const go = within(dialog).getByRole("button", { name: "Change the date" });

    await user.type(within(dialog).getByLabelText(/^New date/), NEXT_YEAR);
    expect(go).toBeDisabled();
    await user.type(within(dialog).getByLabelText(/why is it changing/i), "  The vendor needs a week ");
    expect(go).toBeEnabled();
    await user.click(go);

    await vi.waitFor(() =>
      expect(sent).toEqual({ answer_by: NEXT_YEAR, reason: "The vendor needs a week" }),
    );
    expect(await within(dialog).findByText(moved.body)).toBeInTheDocument();
    expect(within(dialog).getByText("Update")).toBeInTheDocument();
  });

  it("offers no date change once the server says it cannot move", async () => {
    const closed = ticket({ state: "closed", moves: [], may_write: false, may_change_date: false });
    server.use(
      http.get(`${API}/breaches/${BREACH}/tickets`, () => HttpResponse.json([closed])),
      http.get(`${API}/breaches/${BREACH}/tickets/${TICKET}`, () =>
        HttpResponse.json({ ticket: closed, instruction: "x", messages: [] }),
      ),
    );
    const { user } = render(<TicketsCard breach={breach(true)} />);

    await user.click(await screen.findByRole("button", { name: /open/i }));
    const dialog = await screen.findByRole("dialog");
    await within(dialog).findByText(/reopen it to write/i);
    expect(within(dialog).queryByRole("button", { name: "Change the date" })).not.toBeInTheDocument();
  });
});

/**
 * A browser west of Greenwich, whichever zone the test runs in: there, a date
 * with no time read by `new Date` is the evening of the day before.
 */
function readDatesWestOfGreenwich() {
  vi.stubGlobal(
    "Date",
    class extends Date {
      constructor(...args: unknown[]) {
        const [day] = args;
        if (typeof day === "string" && /^\d{4}-\d{2}-\d{2}$/.test(day)) {
          const [y, m, d] = day.split("-").map(Number);
          super(y, m - 1, d - 1, 19);
        } else {
          super(...(args as [number]));
        }
      }
    },
  );
}

/** A day counted from today, as the API writes it and as the reader sees it. */
function aDayFromToday(days: number) {
  const on = new Date();
  on.setDate(on.getDate() + days);
  const pad = (n: number) => String(n).padStart(2, "0");
  return {
    wire: `${on.getFullYear()}-${pad(on.getMonth() + 1)}-${pad(on.getDate())}`,
    seen: formatDate(on),
  };
}

const mine = (over: Partial<MyBreachTicket> = {}): MyBreachTicket => ({
  ticket_uuid: TICKET,
  breach_reference: "BR-2026-0007",
  instruction: "Export the drive's access log",
  state: "issued",
  answer_by: null,
  created_at: "2026-10-05T10:00:00Z",
  unread: 1,
  last_activity_at: null,
  moves: [{ move: "return", reason_required: false }],
  may_add_colleague: true,
  may_change_date: true,
  ...over,
});

describe("a Resolve by date, read west of Greenwich", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("is the day it was set for on the office's list and on the ticket", async () => {
    const { wire, seen } = aDayFromToday(3);
    readDatesWestOfGreenwich();
    server.use(
      http.get(`${API}/breaches/${BREACH}/tickets`, () => HttpResponse.json([ticket({ answer_by: wire })])),
      http.get(`${API}/breaches/${BREACH}/tickets/${TICKET}`, () =>
        HttpResponse.json({ ticket: ticket({ answer_by: wire }), instruction: "x", messages: [] }),
      ),
    );
    const { user } = render(<TicketsCard breach={breach(true)} />);

    expect(await screen.findByText(seen)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Open" }));
    expect(await within(await screen.findByRole("dialog")).findByText(`Resolve by ${seen}`)).toBeInTheDocument();
  });

  it("is the day it was set for on the holder's card, and not late on that day", () => {
    const { wire, seen } = aDayFromToday(0);
    readDatesWestOfGreenwich();
    render(<BreachTicketCard ticket={mine({ answer_by: wire })} />);
    const date = screen.getByText(`Resolve by ${seen}`);
    expect(date).not.toHaveClass("text-danger-text");
  });

  it("is late the day after", () => {
    const { wire, seen } = aDayFromToday(-1);
    readDatesWestOfGreenwich();
    render(<BreachTicketCard ticket={mine({ answer_by: wire })} />);
    expect(screen.getByText(`Resolve by ${seen}`)).toHaveClass("text-danger-text");
  });
});

describe("BreachTicketCard", () => {
  it("shows the reference and the instruction, and offers the return while it is open", async () => {
    server.use(
      http.get(`${API}/breach-tickets/${TICKET}`, () => HttpResponse.json({ ticket: mine(), messages: [] })),
    );
    const { user } = render(<BreachTicketCard ticket={mine()} />);

    expect(screen.getByText("BR-2026-0007")).toBeInTheDocument();
    expect(screen.getByText("Export the drive's access log")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /respond/i }));
    const dialog = await screen.findByRole("dialog");
    expect(await within(dialog).findByText("This is my return")).toBeInTheDocument();
  });

  it("offers no return once it is returned, and nothing to write once closed", async () => {
    const closed = mine({ state: "closed", moves: [] });
    server.use(
      http.get(`${API}/breach-tickets/${TICKET}`, () => HttpResponse.json({ ticket: closed, messages: [] })),
    );
    const { user } = render(<BreachTicketCard ticket={closed} />);

    await user.click(screen.getByRole("button", { name: /open/i }));
    const dialog = await screen.findByRole("dialog");
    expect(await within(dialog).findByText(/nothing further is needed from you/i)).toBeInTheDocument();
    expect(within(dialog).queryByText("This is my return")).not.toBeInTheDocument();
  });

  it("brings in a colleague with a note, while the server allows it", async () => {
    let sent: unknown = null;
    server.use(
      http.post(`${API}/breach-tickets/${TICKET}/colleagues`, async ({ request }) => {
        sent = await request.json();
        return HttpResponse.json({ ticket: mine(), messages: [] });
      }),
    );
    const { user } = render(<BreachTicketCard ticket={mine()} />);

    await user.click(screen.getByRole("button", { name: /add a colleague/i }));
    const dialog = await screen.findByRole("dialog");
    await user.type(within(dialog).getByLabelText(/their work email/i), "ravi@cmp.local");
    await user.type(within(dialog).getByLabelText(/what you are asking/i), "Check the VPN logs");
    await user.click(within(dialog).getByRole("button", { name: "Add" }));

    await vi.waitFor(() =>
      expect(sent).toEqual({ full_name: "", email: "ravi@cmp.local", mobile: null, note: "Check the VPN logs" }),
    );
  });

  it("offers no colleague once the server says the ticket is not open", () => {
    render(<BreachTicketCard ticket={mine({ state: "closed", moves: [], may_add_colleague: false })} />);
    expect(screen.queryByRole("button", { name: /add a colleague/i })).not.toBeInTheDocument();
  });

  it("closes the window once a message is sent, without asking about it", async () => {
    let sent = 0;
    server.use(
      http.get(`${API}/breach-tickets/${TICKET}`, () => HttpResponse.json({ ticket: mine(), messages: [] })),
      http.post(`${API}/breach-tickets/${TICKET}/messages`, () => {
        sent += 1;
        return HttpResponse.json({ ticket: mine(), messages: [] });
      }),
    );
    const { user } = render(<BreachTicketCard ticket={mine()} />);

    await user.click(screen.getByRole("button", { name: /respond/i }));
    const dialog = await screen.findByRole("dialog");
    await user.type(await within(dialog).findByLabelText("Message"), "Pulled the log; uploading it now");
    await user.click(within(dialog).getByTestId("composer-send"));

    await vi.waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(sent).toBe(1);
    expect(screen.queryByText(/not saved/i)).not.toBeInTheDocument();
  });

  it("keeps what is being typed through a failed read of the ticket", async () => {
    server.use(
      http.get(`${API}/breach-tickets/${TICKET}`, () => HttpResponse.json({ ticket: mine(), messages: [] })),
    );
    const { user, queryClient } = render(<BreachTicketCard ticket={mine()} />);

    await user.click(screen.getByRole("button", { name: /respond/i }));
    const dialog = await screen.findByRole("dialog");
    await user.type(await within(dialog).findByLabelText("Message"), "Typed, not sent");

    server.use(http.get(`${API}/breach-tickets/${TICKET}`, () => HttpResponse.json(DOWN, { status: 503 })));
    await act(async () => {
      await queryClient.refetchQueries({ queryKey: keys.breach.myTicket(TICKET) });
      await new Promise((resolve) => setTimeout(resolve, 10));
    });

    expect(queryClient.getQueryState(keys.breach.myTicket(TICKET))?.status).toBe("error");
    expect(within(dialog).queryByText(/Something went wrong at our end/)).not.toBeInTheDocument();
    expect(within(dialog).getByLabelText("Message")).toHaveValue("Typed, not sent");
  });

  it("says so when the ticket cannot be read at all", async () => {
    server.use(http.get(`${API}/breach-tickets/${TICKET}`, () => HttpResponse.json(DOWN, { status: 503 })));
    const { user } = render(<BreachTicketCard ticket={mine()} />);

    await user.click(screen.getByRole("button", { name: /respond/i }));

    expect(await within(await screen.findByRole("dialog")).findByText(/Something went wrong at our end/)).toBeInTheDocument();
  });

  it("takes the same files in a reply as when the ticket was raised", async () => {
    server.use(
      http.get(`${API}/breach-tickets/${TICKET}`, () => HttpResponse.json({ ticket: mine(), messages: [] })),
    );
    const { user } = render(<BreachTicketCard ticket={mine()} />);

    await user.click(screen.getByRole("button", { name: /respond/i }));
    const dialog = await screen.findByRole("dialog");
    expect(await within(dialog).findByLabelText("Attach a file")).toHaveAttribute("accept", ATTACHMENT_ACCEPT);
    expect(within(dialog).getByText(/PDF, Word, image, saved email/)).toBeInTheDocument();
  });

  it("calls the date Resolve by", () => {
    render(<BreachTicketCard ticket={mine({ answer_by: "2030-01-15" })} />);
    expect(screen.getByText(/^Resolve by /)).toBeInTheDocument();
    expect(screen.queryByText(/^Answer by/)).not.toBeInTheDocument();
  });

  it("moves the date from the window, saying why, and the office is told", async () => {
    let sent: unknown = null;
    server.use(
      http.get(`${API}/breach-tickets/${TICKET}`, () => HttpResponse.json({ ticket: mine(), messages: [] })),
      http.post(`${API}/breach-tickets/${TICKET}/resolve-by`, async ({ request }) => {
        sent = await request.json();
        return HttpResponse.json({ ticket: mine({ answer_by: NEXT_YEAR }), messages: [] });
      }),
    );
    const { user } = render(<BreachTicketCard ticket={mine()} />);

    await user.click(screen.getByRole("button", { name: /respond/i }));
    const dialog = await screen.findByRole("dialog");
    await user.click(await within(dialog).findByRole("button", { name: "Change the date" }));
    expect(within(dialog).getByText(/^The Privacy Office is told\./)).toBeInTheDocument();
    await user.type(within(dialog).getByLabelText(/^New date/), NEXT_YEAR);
    await user.type(within(dialog).getByLabelText(/why is it changing/i), "Waiting on the vendor");
    await user.click(within(dialog).getByRole("button", { name: "Change the date" }));

    await vi.waitFor(() => expect(sent).toEqual({ answer_by: NEXT_YEAR, reason: "Waiting on the vendor" }));
    await vi.waitFor(() =>
      expect(toast.success).toHaveBeenCalledWith("Date changed", "The Privacy Office is told."),
    );
  });

  it("offers no date change once the server says it cannot move", async () => {
    const closed = mine({ state: "closed", moves: [], may_change_date: false });
    server.use(
      http.get(`${API}/breach-tickets/${TICKET}`, () => HttpResponse.json({ ticket: closed, messages: [] })),
    );
    const { user } = render(<BreachTicketCard ticket={closed} />);

    await user.click(screen.getByRole("button", { name: /open/i }));
    const dialog = await screen.findByRole("dialog");
    await within(dialog).findByText(/nothing further is needed from you/i);
    expect(within(dialog).queryByRole("button", { name: "Change the date" })).not.toBeInTheDocument();
  });
});
