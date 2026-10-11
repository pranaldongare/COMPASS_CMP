/**
 * The temporary ticket holder's home (2026-10-11): figures, attention rows,
 * lists and activity all counted from the breach tickets addressed to the
 * login, and shown on the Tickets page only to a login without a dashboard.
 */
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";

import TicketsPage from "@/app/(app)/tickets/page";
import { HolderHome, holderFigures } from "@/features/breach/components/holder-home";
import { makeMe } from "@/test/fixtures";
import { render, screen, within } from "@/test/render";
import { API, server } from "@/test/server";
import type { Me, MyBreachTicket } from "@/types";

const auth = vi.hoisted(() => ({ me: null as Me | null }));

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(window.location.search),
  usePathname: () => window.location.pathname,
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn(), refresh: vi.fn() }),
}));

vi.mock("@/providers", () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn() }),
  useAuth: () => ({ me: auth.me }),
}));

vi.mock("@/providers/auth-provider", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/providers/auth-provider")>()),
  useOptionalAuth: () => ({ me: auth.me }),
}));

// Sunday 11 October 2026, mid-morning.
const NOW = new Date(2026, 9, 11, 10, 0);

const ticket = (over: Partial<MyBreachTicket> = {}): MyBreachTicket => ({
  ticket_uuid: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  breach_reference: "BR-2026-5401",
  instruction: "Pull the badge log for the server room",
  state: "issued",
  answer_by: "2026-10-11",
  created_at: "2026-10-11T08:30:00+05:30",
  unread: 0,
  last_activity_at: null,
  moves: [],
  may_add_colleague: true,
  ...over,
});

const dueToday = ticket();
const dueSoon = ticket({
  ticket_uuid: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
  breach_reference: "BR-2026-5392",
  instruction: "Export the drive's access log",
  answer_by: "2026-10-14",
  created_at: "2026-10-10T09:00:00+05:30",
});
const late = ticket({
  ticket_uuid: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
  breach_reference: "BR-2026-5300",
  answer_by: "2026-10-09",
  created_at: "2026-10-01T09:00:00+05:30",
});
const returned = ticket({
  ticket_uuid: "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
  breach_reference: "BR-2026-5310",
  state: "returned",
  answer_by: "2026-10-12",
  created_at: "2026-10-05T09:00:00+05:30",
  last_activity_at: "2026-10-09T12:00:00+05:30",
});
const closed = ticket({
  ticket_uuid: "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
  breach_reference: "BR-2026-5288",
  state: "closed",
  created_at: "2026-09-20T09:00:00+05:30",
});

describe("holderFigures", () => {
  it("counts open, returned and late tickets and finds the earliest date", () => {
    const f = holderFigures([dueSoon, dueToday, late, returned, closed], NOW);
    expect(f.open.map((t) => t.breach_reference)).toEqual([
      "BR-2026-5300",
      "BR-2026-5401",
      "BR-2026-5392",
    ]);
    expect(f.returned).toEqual([returned]);
    expect(f.late).toEqual([late]);
    expect(f.today).toEqual([dueToday]);
    expect(f.soon).toEqual([dueSoon]);
    expect(f.earliest).toBe("2026-10-09");
  });
});

describe("HolderHome", () => {
  it("greets, counts and lists from the tickets alone", () => {
    render(
      <HolderHome
        tickets={[dueToday, dueSoon, returned, closed]}
        name="Vikram Kulkarni"
        now={NOW}
      />,
    );

    expect(screen.getByText("Temporary access")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Good day, Vikram" })).toBeInTheDocument();
    expect(
      screen.getByText("You were asked to help with a breach. Your tickets are below."),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /open my tickets/i })).toHaveAttribute(
      "href",
      "#breach-tickets",
    );

    // Figures: two open, one due today, one answered, the earliest date today.
    const open = screen.getByRole("link", { name: /tickets open/i });
    expect(open).toHaveTextContent("2");
    expect(open).toHaveTextContent("1 due today");
    const today = screen.getByRole("link", { name: /^due today/i });
    expect(today).toHaveTextContent("1");
    expect(today).toHaveAttribute("href", `/tickets?breach_ticket=${dueToday.ticket_uuid}`);
    expect(screen.getByRole("link", { name: /^answered/i })).toHaveTextContent("1");
    expect(screen.getByRole("link", { name: /earliest answer-by/i })).toHaveTextContent(
      "11 Oct",
    );

    // Needs attention: the one due today, then the one due within the week.
    const rows = within(screen.getByTestId("holder-attention")).getAllByRole("link");
    expect(rows.map((r) => r.textContent)).toEqual([
      expect.stringContaining("Ticket due today"),
      expect.stringContaining("Ticket due within 7 days"),
    ]);

    // The lists: open tickets with their dates; returned ones apart.
    const mine = screen.getByRole("list", { name: "Your breach tickets" });
    expect(within(mine).getAllByRole("link")).toHaveLength(2);
    expect(within(mine).getByText("Due today")).toBeInTheDocument();
    expect(within(mine).getByText("Due 14 Oct")).toBeInTheDocument();
    const answered = screen.getByRole("list", { name: "Answered" });
    expect(within(answered).getByText("BR-2026-5310")).toBeInTheDocument();
    expect(within(answered).getByRole("link")).toHaveAttribute(
      "href",
      `/tickets?breach_ticket=${returned.ticket_uuid}`,
    );

    // Activity: newest first, from the issue and message times.
    const activity = within(
      screen.getByRole("list", { name: "Recent activity" }),
    ).getAllByRole("listitem");
    expect(activity[0]).toHaveTextContent("Ticket on BR-2026-5401 issued to you");
    expect(activity[1]).toHaveTextContent("Ticket on BR-2026-5392 issued to you");
    expect(activity[2]).toHaveTextContent(
      "Latest message on BR-2026-5310, now with the Privacy Office",
    );
  });

  it("marks a ticket past its date late", () => {
    render(<HolderHome tickets={[late]} name="Vikram" now={NOW} />);
    const rows = within(screen.getByTestId("holder-attention")).getAllByRole("link");
    expect(rows).toHaveLength(1);
    expect(rows[0]).toHaveTextContent("Ticket past its date");
    expect(screen.getByRole("link", { name: /earliest answer-by/i })).toHaveTextContent(
      "2 days late",
    );
  });

  it("says so in one line when nothing is waiting", () => {
    render(<HolderHome tickets={[returned]} name="Vikram" now={NOW} />);
    expect(screen.getByText("Nothing is waiting on you.")).toBeInTheDocument();
    expect(screen.getByText("Nothing waiting on you.")).toBeInTheDocument();
  });
});

describe("on the Tickets page", () => {
  function serve(breach: MyBreachTicket[]) {
    server.use(
      http.get(`${API}/tickets`, () => HttpResponse.json([])),
      http.get(`${API}/breach-tickets`, () => HttpResponse.json(breach)),
    );
  }

  it("opens a breach-only login's page with the summary above its tickets", async () => {
    auth.me = makeMe({ role: "breach_holder", full_name: "Vikram Kulkarni" });
    serve([dueToday]);
    render(<TicketsPage />);
    expect(await screen.findByTestId("holder-home")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Good day, Vikram" })).toBeInTheDocument();
    expect(document.getElementById("breach-tickets")).toContainElement(
      screen.getByTestId("breach-ticket"),
    );
  });

  it("is not shown to staff with a dashboard", async () => {
    auth.me = makeMe({ role: "dco" });
    serve([dueToday]);
    render(<TicketsPage />);
    expect(await screen.findByTestId("breach-ticket")).toBeInTheDocument();
    expect(screen.queryByTestId("holder-home")).not.toBeInTheDocument();
  });
});
