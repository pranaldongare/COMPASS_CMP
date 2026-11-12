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
  has_address: true,
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
  it("shows each holder's state in words, and an answer to review before anything else", () => {
    render(<HoldersCard request={request([holder()])} />);

    const row = screen.getByText("Samsung R&D Bangalore").closest("tr") as HTMLElement;
    // Partly done is not a success: the badge says so.
    expect(within(row).getByText(/answered - review · /i)).toBeInTheDocument();
    // Read before accepted (2026-10-30): the row opens the answer, it does not accept it.
    expect(within(row).getByRole("button", { name: /review the answer/i })).toBeInTheDocument();
    expect(within(row).queryByRole("button", { name: "Accept the answer" })).not.toBeInTheDocument();
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

    await user.click(screen.getByRole("button", { name: /review the answer/i }));
    const dialog = await screen.findByRole("dialog");
    // The answer first, then the move.
    const answer = within(dialog).getByText("Some rows are under a legal hold");
    const accept = within(dialog).getByRole("button", { name: "Accept the answer" });
    expect(answer.compareDocumentPosition(accept) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    await user.click(accept);
    expect(within(dialog).getByText(/the response will say what was not done/i)).toBeInTheDocument();
    expect(accepted).toBe(false);
    await user.click(within(dialog).getByRole("button", { name: "Accept the answer" }));
    await vi.waitFor(() => expect(accepted).toBe(true));
  });

  it("opens the ticket's messages from the new-messages badge", async () => {
    thread();
    const { user } = render(<HoldersCard request={request([holder({ unread_for_office: 2 })])} />);
    await user.click(screen.getByRole("button", { name: /read 2 new messages from samsung/i }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText("Messages")).toBeInTheDocument();
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

  it("puts Send back beside Accept, not under More, and takes the reason there", async () => {
    // 2026-11-12: it was the only thing under More, and the officer reviewing
    // an answer did not find it.
    let sent: unknown = null;
    thread();
    server.use(
      http.post(`${API}/requests/${REQUEST}/holders/${HOLDER}/send-back`, async ({ request }) => {
        sent = await request.json();
        return HttpResponse.json(holder());
      }),
    );
    const { user } = render(<HoldersCard request={request([holder()])} />);
    await user.click(screen.getByRole("button", { name: /review the answer/i }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByRole("button", { name: "Accept the answer" })).toBeInTheDocument();
    expect(within(dialog).queryByRole("button", { name: /more/i })).not.toBeInTheDocument();

    await user.click(within(dialog).getByRole("button", { name: "Send back" }));
    await user.type(within(dialog).getByLabelText(/what is missing or wrong/i), "The export is missing");
    await user.click(within(dialog).getByRole("button", { name: "Send it back" }));
    await vi.waitFor(() => expect(sent).toMatchObject({ reason: "The export is missing" }));

    // Sent, and the window stays open: closing it does not then ask about
    // the reason that has gone.
    await vi.waitFor(() =>
      expect(within(dialog).queryByLabelText(/what is missing or wrong/i)).not.toBeInTheDocument(),
    );
    await user.click(within(dialog).getByRole("button", { name: "Close" }));
    expect(screen.queryByText(/not saved/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("does not ask about a move given up with its own Cancel, and still asks about a message", async () => {
    thread();
    const { user } = render(<HoldersCard request={request([holder()])} />);
    await user.click(screen.getByRole("button", { name: /review the answer/i }));
    const dialog = await screen.findByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: "Send back" }));
    await user.type(within(dialog).getByLabelText(/what is missing or wrong/i), "Not this");
    await user.click(within(dialog).getByRole("button", { name: "Cancel" }));

    await user.type(await within(dialog).findByLabelText("Message"), "One question first");
    await user.click(within(dialog).getByRole("button", { name: "Close" }));
    expect(screen.getByText(/not saved/i)).toBeInTheDocument();
  });

  it("sends a project with no processor on record to a DCO Admin the officer chooses", async () => {
    // 0069, and the product owner's rule: a DCO Admin, not the project's own
    // owner; an office with several chooses one here.
    let body: unknown = null;
    let asked: string | null = null;
    server.use(
      http.get(`${API}/users/staff`, ({ request }) => {
        asked = new URL(request.url).searchParams.get("role");
        return HttpResponse.json([
          { uuid: "a1a1a1a1-a1a1-4a1a-8a1a-a1a1a1a1a1a1", full_name: "Zoya Khan", email: "zoya@example.org", role: "dco_admin" },
          { uuid: "b2b2b2b2-b2b2-4b2b-8b2b-b2b2b2b2b2b2", full_name: "Arun Shetty", email: "arun@example.org", role: "dco_admin" },
        ]);
      }),
      http.post(`${API}/requests/${REQUEST}/holders/${HOLDER}/confirm`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(holder());
      }),
    );
    const unnamed = holder({
      label: "Gait Study 2026 · DCO Admin",
      derived_from: "project_owner",
      evidence: { project: "p-1", is_activity: false, consents: ["c-1"] },
      project_uuid: "55555555-5555-4555-8555-555555555555",
      project_name: "Gait Study 2026",
      is_activity: false,
      confirmed_at: null,
      ticket_status: "pending",
      issued_at: null,
      returned_at: null,
      return_summary: null,
      return_outcome: null,
      channel: "email",
      responder_user_uuid: null,
      responder_user_name: null,
      has_address: false,
      state: "not_confirmed",
      state_label: "Not confirmed",
      moves: [move("confirm", "Confirm who answers", true), move("remove", "Remove")],
    });
    const { user } = render(<HoldersCard request={request([unnamed])} />);
    expect(screen.getByText(/choose who answers before sending/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Confirm who answers" }));
    const dialog = await screen.findByRole("dialog");
    const which = await within(dialog).findByLabelText(/which dco admin answers/i);
    expect(asked).toBe("dco_admin");
    // Nobody chosen yet, nothing to confirm.
    expect(within(dialog).getByRole("button", { name: "Confirm" })).toBeDisabled();
    // In name order, each with the address that tells two apart.
    expect(within(which).getAllByRole("option").map((o) => o.textContent)).toEqual([
      "Choose…",
      "Arun Shetty · arun@example.org",
      "Zoya Khan · zoya@example.org",
    ]);
    await user.selectOptions(which, "Zoya Khan · zoya@example.org");
    await user.click(within(dialog).getByRole("button", { name: "Confirm" }));
    await vi.waitFor(() =>
      expect(body).toEqual({ responder_user_uuid: "a1a1a1a1-a1a1-4a1a-8a1a-a1a1a1a1a1a1" }),
    );
  });

  it("confirms an activity's HR owner as found, without retyping them", async () => {
    let body: unknown = null;
    server.use(
      http.post(`${API}/requests/${REQUEST}/holders/${HOLDER}/confirm`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(holder());
      }),
    );
    const owner = holder({
      label: "CSR day · HR owner",
      derived_from: "project_owner",
      evidence: { project: "p-2", is_activity: true, consents: ["c-2"] },
      project_uuid: "56565656-5656-4656-8656-565656565656",
      project_name: "CSR day",
      is_activity: true,
      confirmed_at: null,
      ticket_status: "pending",
      issued_at: null,
      returned_at: null,
      return_summary: null,
      return_outcome: null,
      responder_name: "Arun Shetty",
      responder_contact: "arun@example.org",
      responder_user_uuid: "b2b2b2b2-b2b2-4b2b-8b2b-b2b2b2b2b2b2",
      state: "not_confirmed",
      state_label: "Not confirmed",
      moves: [move("confirm", "Confirm who answers", true), move("remove", "Remove")],
    });
    const { user } = render(<HoldersCard request={request([owner])} />);
    await user.click(screen.getByRole("button", { name: "Confirm who answers" }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText(/runs this activity and answers in the console/i)).toHaveTextContent(
      "Arun Shetty",
    );
    // Not typed into the boxes: typing over an account means email instead.
    expect(within(dialog).queryByLabelText(/their email/i)).not.toBeInTheDocument();
    await user.click(within(dialog).getByRole("button", { name: "Confirm" }));
    await vi.waitFor(() => expect(body).toEqual({ responder_name: null, responder_contact: null }));
  });

  it("lists the consents nobody could be found for, once the records have been read", () => {
    const unowned = {
      consent_uuid: "66666666-6666-4666-8666-666666666666",
      project_uuid: "77777777-7777-4777-8777-777777777777",
      project_name: "Walk Study",
      is_activity: false,
      notice_code: "NTC-WALK",
      notice_version: 2,
      at: "2026-10-03T10:00:00Z",
      withdrawal: false,
    };
    const { unmount } = render(
      <HoldersCard
        request={makeRequestDetail({
          request_uuid: REQUEST,
          status: "in_progress",
          holders: [],
          holders_derived_at: "2026-11-12T09:00:00Z",
          unowned_consents: [unowned],
        })}
      />,
    );
    expect(screen.getByText("1 consent has nobody to ask")).toBeInTheDocument();
    const listed = within(screen.getByRole("list", { name: "Consents with nobody to ask" }));
    expect(listed.getByRole("link", { name: "Walk Study" })).toHaveAttribute(
      "href",
      "/projects/77777777-7777-4777-8777-777777777777",
    );
    expect(listed.getByText(/NTC-WALK v2/)).toBeInTheDocument();
    // Read, and nobody found: said as an answer, not as "not yet".
    expect(screen.getByText(/the records name nobody/i)).toBeInTheDocument();
    unmount();

    // Before the records are read there is nothing to say about them.
    render(<HoldersCard request={makeRequestDetail({ request_uuid: REQUEST, status: "in_progress", holders: [] })} />);
    expect(screen.getByText(/no holders yet/i)).toBeInTheDocument();
    expect(screen.queryByText(/nobody to ask/i)).not.toBeInTheDocument();
  });

  it("moves a waiting ticket's date beside the date itself, with the reason, and not from the menu", async () => {
    // 2026-11-12: a breach ticket's date could be moved and a rights ticket's
    // could not.
    let sent: { due_at: string; reason: string } | null = null;
    thread();
    server.use(
      http.post(`${API}/requests/${REQUEST}/holders/${HOLDER}/answer-by`, async ({ request }) => {
        sent = (await request.json()) as { due_at: string; reason: string };
        return HttpResponse.json(holder());
      }),
    );
    const waiting = holder({
      ticket_status: "issued",
      returned_at: null,
      return_summary: null,
      return_outcome: null,
      state: "waiting",
      state_label: "Waiting",
      due_at: "2030-01-10T18:29:00Z",
      moves: [
        move("record_answer", "Record their answer for them"),
        move("message", "Write to them"),
        move("remind", "Send a reminder"),
        move("change_date", "Change the date"),
        move("withdraw", "Withdraw"),
      ],
    });
    const { user } = render(
      <HoldersCard
        request={makeRequestDetail({
          request_uuid: REQUEST,
          status: "awaiting_holders",
          due_at: "2030-02-01T10:00:00Z",
          holders: [waiting],
        })}
      />,
    );
    await user.click(screen.getByRole("button", { name: "Samsung R&D Bangalore" }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText(/^Answer by /)).toBeInTheDocument();

    await user.click(within(dialog).getByRole("button", { name: "Change the date" }));
    expect(within(dialog).getByText(/^Arun Shetty is told\./)).toBeInTheDocument();
    const go = within(dialog).getByRole("button", { name: "Change the date" });
    const date = within(dialog).getByLabelText(/^new answer by date/i);
    // Never past the response the ticket feeds: the picker stops the day before.
    expect(date).toHaveAttribute("max", "2030-01-31");
    await user.clear(date);
    await user.type(date, "2030-01-20");
    expect(go).toBeDisabled();
    await user.type(within(dialog).getByLabelText(/^reason/i), "Their archive is offline until Friday");
    await user.click(go);

    await vi.waitFor(() => expect(sent).not.toBeNull());
    expect(sent!.reason).toBe("Their archive is offline until Friday");
    // The end of the chosen day, in the officer's own calendar.
    expect(new Date(sent!.due_at).getTime()).toBe(new Date(2030, 0, 20, 23, 59).getTime());

    // Not one of the things under More: it sits with the date.
    await user.click(within(dialog).getByRole("button", { name: /more/i }));
    expect(await screen.findByRole("menuitem", { name: "Send a reminder" })).toBeInTheDocument();
    expect(screen.queryByRole("menuitem", { name: "Change the date" })).not.toBeInTheDocument();
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

  it("warns of a holder with no email, and corrects a mistyped one", async () => {
    let body: unknown = null;
    server.use(
      http.post(`${API}/requests/${REQUEST}/holders/${HOLDER}/correct-contact`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(holder());
      }),
      http.get(`${API}/requests/${REQUEST}/holders/${HOLDER}/thread`, () =>
        HttpResponse.json({ holder: holder(), messages: [] }),
      ),
    );
    const open = holder({
      ticket_status: "issued",
      channel: "email",
      responder_contact: "keepr@vendor.example",
      return_summary: null,
      return_outcome: null,
      state: "waiting",
      state_label: "Waiting",
      moves: [move("record_answer", "Record their answer", true), move("correct_contact", "Correct their email")],
    });
    const { user, unmount } = render(<HoldersCard request={request([open])} />);
    await user.click(screen.getByRole("button", { name: "Samsung R&D Bangalore" }));
    const dialog = await screen.findByRole("dialog");
    // The only other move: a button, not a menu of one.
    expect(within(dialog).queryByRole("button", { name: /more/i })).not.toBeInTheDocument();
    await user.click(within(dialog).getByRole("button", { name: "Correct their email" }));
    const email = within(dialog).getByLabelText(/their email/i);
    await user.clear(email);
    await user.type(email, "keeper@vendor.example");
    await user.click(within(dialog).getByRole("button", { name: "Correct and send again" }));
    await vi.waitFor(() =>
      expect(body).toEqual({ responder_contact: "keeper@vendor.example", responder_name: null }),
    );
    unmount();

    render(<HoldersCard request={request([holder({ has_address: false, state: "not_sent", moves: [] })])} />);
    expect(screen.getByText(/no email - add one before sending/i)).toBeInTheDocument();
  });
});
