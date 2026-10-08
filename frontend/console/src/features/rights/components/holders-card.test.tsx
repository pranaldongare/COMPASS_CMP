/**
 * The holders card (2026-10-08): a guided path, one table, one ticket dialog,
 * and only the moves the server returned - the main one first, the rest under
 * More. An answer counts once the office accepts it.
 */
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";

import { HoldersCard } from "@/features/rights/components/holders-card";
import { makeRequestDetail } from "@/test/fixtures";
import { render, screen, within } from "@/test/render";
import { API, server } from "@/test/server";
import type { RightsHolder, TicketMove } from "@/types";

vi.mock("@/providers", () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn() }),
}));

const REQUEST = "11111111-1111-4111-8111-111111111111";
const HOLDER = "22222222-2222-4222-8222-222222222222";

const move = (name: TicketMove["move"], label: string, primary = false): TicketMove => ({
  move: name,
  label,
  primary,
  reason_required: false,
  sends_email: false,
  needs_date: false,
});

const holder = (over: Partial<RightsHolder> = {}): RightsHolder => ({
  holder_uuid: HOLDER,
  label: "Samsung R&D Bangalore",
  derived_from: "export_line",
  evidence: {},
  processor_uuid: null,
  processor_name: null,
  is_in_house: true,
  confirmed_at: "2026-10-01T10:00:00Z",
  confirmed_by_name: "Priya Menon",
  ticket_status: "returned",
  instruction: "Erase every record of her in the survey store",
  responder_name: null,
  responder_contact: null,
  issued_at: "2026-10-02T10:00:00Z",
  due_at: "2026-10-10T18:29:00Z",
  escalated_at: null,
  returned_at: "2026-10-05T10:00:00Z",
  return_summary: "Some rows are under a legal hold",
  return_outcome: "partial",
  return_evidence_hash: null,
  created_at: "2026-10-01T09:00:00Z",
  channel: "portal",
  respondent_uuid: null,
  responder_user_uuid: null,
  responder_user_name: "Arun Shetty",
  contact_log: [],
  brief: null,
  message_count: 0,
  unread_for_office: 0,
  seen_at: null,
  last_reminded_at: null,
  reminders_sent: 0,
  return_evidence_name: null,
  sent_back_at: null,
  sent_back_reason: null,
  sent_back_count: 0,
  link_issued_at: null,
  temporary_access: null,
  accepted_at: null,
  accepted_by_name: null,
  last_activity_at: "2026-10-05T10:00:00Z",
  state: "review",
  state_label: "Answered - review",
  overdue: false,
  moves: [move("accept", "Accept the answer", true), move("send_back", "Send back"), move("message", "Write to them")],
  ...over,
});

const request = (holders: RightsHolder[], status: "awaiting_holders" | "closed" = "awaiting_holders") =>
  makeRequestDetail({ request_uuid: REQUEST, status, holders });

function thread() {
  server.use(
    http.get(`${API}/requests/${REQUEST}/holders/${HOLDER}/thread`, () =>
      HttpResponse.json({ holder: holder(), messages: [] }),
    ),
  );
}

describe("HoldersCard", () => {
  it("shows each holder's state in words and offers the server's main move on its row", () => {
    render(<HoldersCard request={request([holder()])} />);

    const row = screen.getByText("Samsung R&D Bangalore").closest("tr") as HTMLElement;
    // Partly done is not a success: the badge says so.
    expect(within(row).getByText(/answered - review · /i)).toBeInTheDocument();
    expect(within(row).getByRole("button", { name: "Accept the answer" })).toBeInTheDocument();
    expect(screen.getByText("Review answers").closest("[aria-current]")).toHaveAttribute("aria-current", "step");
  });

  it("accepts an answer only after saying what accepting a partial answer means", async () => {
    thread();
    let accepted = false;
    server.use(
      http.post(`${API}/requests/${REQUEST}/holders/${HOLDER}/accept`, () => {
        accepted = true;
        return HttpResponse.json(holder({ state: "accepted", accepted_at: "2026-10-06T10:00:00Z" }));
      }),
    );
    const { user } = render(<HoldersCard request={request([holder()])} />);

    await user.click(screen.getByRole("button", { name: "Accept the answer" }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText(/the response will say what was not done/i)).toBeInTheDocument();
    expect(accepted).toBe(false);
    await user.click(within(dialog).getByRole("button", { name: "Accept the answer" }));
    await vi.waitFor(() => expect(accepted).toBe(true));
  });

  it("puts the other moves under More, and none the server did not send", async () => {
    thread();
    const overdue = holder({
      ticket_status: "issued",
      returned_at: null,
      return_summary: null,
      return_outcome: null,
      state: "overdue",
      state_label: "Overdue",
      overdue: true,
      moves: [
        move("final_reminder", "Send final reminder", true),
        move("record_answer", "Record their answer for them"),
        move("message", "Write to them"),
        move("remind", "Send a reminder"),
      ],
    });
    const { user } = render(<HoldersCard request={request([overdue])} />);

    await user.click(screen.getByRole("button", { name: "Samsung R&D Bangalore" }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByRole("button", { name: "Send final reminder" })).toBeInTheDocument();
    await user.click(within(dialog).getByRole("button", { name: /more/i }));
    expect(await screen.findByRole("menuitem", { name: "Send a reminder" })).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: "Record their answer for them" })).toBeInTheDocument();
    expect(screen.queryByRole("menuitem", { name: /withdraw/i })).not.toBeInTheDocument();
  });

  it("offers sending tickets once holders are confirmed, and finding them only while the request is worked", () => {
    const unsent = holder({
      ticket_status: "pending",
      issued_at: null,
      returned_at: null,
      return_summary: null,
      return_outcome: null,
      state: "not_sent",
      state_label: "Not sent",
      moves: [move("remove", "Remove")],
    });
    const { unmount } = render(<HoldersCard request={request([unsent])} />);
    expect(screen.getByRole("button", { name: "Send tickets" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /find who holds the data/i })).toBeInTheDocument();
    unmount();

    render(<HoldersCard request={request([holder({ moves: [] })], "closed")} />);
    expect(screen.queryByRole("button", { name: /find who holds the data/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Send tickets" })).not.toBeInTheDocument();
  });

  it("says how each holder answers: a temporary login, or a link for an outside holder", () => {
    render(
      <HoldersCard
        request={request([
          holder({ temporary_access: "pending" }),
          holder({
            holder_uuid: "33333333-3333-4333-8333-333333333333",
            label: "Vendor archive",
            channel: "email",
            link_issued_at: "2026-10-02T10:00:00Z",
          }),
        ])}
      />,
    );

    const ours = screen.getByText("Samsung R&D Bangalore").closest("tr") as HTMLElement;
    expect(within(ours).getByText(/temporary login · not yet signed in/)).toBeInTheDocument();
    const theirs = screen.getByText("Vendor archive").closest("tr") as HTMLElement;
    expect(within(theirs).getByText(/outside · answers by link/i)).toBeInTheDocument();
  });
});
