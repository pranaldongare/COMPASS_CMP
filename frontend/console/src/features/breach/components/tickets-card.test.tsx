/**
 * Breach tickets in the console (S3-08): the office's card, and the holder's.
 *
 * Every control comes from the server: the card offers assigning only once
 * the breach is recorded, a ticket's moves are the ones the server returned,
 * and a holder is offered the return only while the server says so.
 */
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";

import { BreachTicketCard } from "@/features/breach/components/my-breach-tickets";
import { TicketsCard } from "@/features/breach/components/tickets-card";
import { render, screen, within } from "@/test/render";
import { API, server } from "@/test/server";
import type { Breach, BreachTicket, MyBreachTicket } from "@/types";

vi.mock("@/providers", () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn() }),
}));

const BREACH = "66666666-6666-4666-8666-666666666666";
const TICKET = "77777777-7777-4777-8777-777777777777";

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
  ...over,
});

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
});

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
  ...over,
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
});
