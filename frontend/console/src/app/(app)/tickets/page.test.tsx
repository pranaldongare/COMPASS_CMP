/**
 * My tasks for a holder (2026-10-08): tickets in three groups read off the
 * server's state, the answer as its own form with no outcome assumed, and a
 * message that leaves the window open.
 *
 * Answering and messaging are two tabs (2026-11-12): side by side, a holder
 * typed the answer into the message box, pressed Send, and took the ticket
 * for answered. The window opens on "Answer the ticket" while one is due;
 * "Messages" says a message is not an answer, and its button says what it
 * sends.
 */
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";

import TicketsPage from "@/app/(app)/tickets/page";
import { render, screen, within } from "@/test/render";
import { API, server } from "@/test/server";
import type { MyTicket } from "@/types";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(window.location.search),
  usePathname: () => window.location.pathname,
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn(), refresh: vi.fn() }),
}));

vi.mock("@/providers", () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn() }),
}));

const ticket = (over: Partial<MyTicket> = {}): MyTicket => ({
  holder_uuid: "33333333-3333-4333-8333-333333333333",
  request_uuid: "44444444-4444-4444-8444-444444444444",
  reference: "DSAR-2026-0012",
  request_type: "access",
  request_status: "awaiting_holders",
  label: "Survey platform",
  subject_name: null,
  instruction: "Export every record of her",
  ticket_status: "issued",
  issued_at: "2026-10-02T10:00:00Z",
  due_at: "2026-10-20T18:29:00Z",
  escalated_at: null,
  returned_at: null,
  return_summary: null,
  return_outcome: null,
  return_evidence_hash: null,
  brief: null,
  message_count: 0,
  unread_for_holder: 0,
  last_reminded_at: null,
  reminders_sent: 0,
  return_evidence_name: null,
  sent_back_at: null,
  sent_back_reason: null,
  sent_back_count: 0,
  consent_uuid: null,
  consent_project: null,
  consent_notice_code: null,
  consent_notice_version: null,
  consent_at: null,
  consent_purposes: null,
  accepted_at: null,
  state: "waiting",
  state_label: "To answer",
  overdue: false,
  ...over,
});

const todo = ticket();
const review = ticket({
  holder_uuid: "55555555-5555-4555-8555-555555555555",
  reference: "DSAR-2026-0013",
  ticket_status: "returned",
  returned_at: "2026-10-05T10:00:00Z",
  return_summary: "Exported the survey rows",
  return_outcome: "partial",
  state: "review",
  state_label: "Answered - with the Privacy Office",
});

function serve(tickets: MyTicket[], onMessage?: () => void) {
  server.use(
    http.get(`${API}/tickets`, () => HttpResponse.json(tickets)),
    http.get(`${API}/breach-tickets`, () => HttpResponse.json([])),
    http.get(`${API}/tickets/:uuid`, ({ params }) =>
      HttpResponse.json({ ticket: tickets.find((t) => t.holder_uuid === params.uuid), messages: [] }),
    ),
    http.post(`${API}/tickets/:uuid/messages`, ({ params }) => {
      onMessage?.();
      return HttpResponse.json({ ticket: tickets.find((t) => t.holder_uuid === params.uuid), messages: [] });
    }),
  );
}

describe("My tasks", () => {
  it("groups tickets by the server's state and shows what an answer said it did", async () => {
    serve([todo, review]);
    render(<TicketsPage />);

    const toDo = (await screen.findByRole("heading", { name: /to do · 1/i })).closest("section") as HTMLElement;
    expect(within(toDo).getByText("DSAR-2026-0012")).toBeInTheDocument();
    const waiting = screen.getByRole("heading", { name: /waiting on the privacy office · 1/i }).closest("section") as HTMLElement;
    expect(within(waiting).getByText("DSAR-2026-0013")).toBeInTheDocument();
    expect(within(waiting).getByText("Did only part of it")).toBeInTheDocument();
    expect(screen.queryByText("Rights requests")).not.toBeInTheDocument();
  });

  it("asks what was done before an answer can be sent, with nothing chosen for them", async () => {
    serve([todo]);
    const { user } = render(<TicketsPage />);

    await user.click(await screen.findByRole("button", { name: /^answer/i }));
    const dialog = await screen.findByRole("dialog");
    // The window opens on the answer: no button to find it behind.
    expect(await within(dialog).findByRole("tab", { name: /answer the ticket/i })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    const answer = within(within(dialog).getByRole("tabpanel", { name: /answer the ticket/i }));
    const submit = answer.getByRole("button", { name: "Submit answer" });
    expect(submit).toBeDisabled();
    for (const radio of answer.getAllByRole("radio")) expect(radio).not.toBeChecked();
    await user.type(answer.getByLabelText(/what you hold, and what you did/i), "Exported it");
    expect(submit).toBeDisabled();
    await user.click(answer.getByLabelText("Did all of it"));
    expect(submit).toBeEnabled();
  });

  it("keeps answering and messaging apart, and says a message is not an answer", async () => {
    let sent = 0;
    let returned: string | null = null;
    serve([todo], () => (sent += 1));
    server.use(
      http.post(`${API}/tickets/:uuid/return`, async ({ request }) => {
        returned = await request.text();
        return HttpResponse.json({ ticket: todo, messages: [] });
      }),
    );
    const { user } = render(<TicketsPage />);

    await user.click(await screen.findByRole("button", { name: /^answer/i }));
    const dialog = await screen.findByRole("dialog");
    const answer = within(await within(dialog).findByRole("tabpanel", { name: /answer the ticket/i }));
    // Nothing on the answer tab sends a message.
    expect(answer.queryByRole("button", { name: /send message/i })).not.toBeInTheDocument();
    await user.type(answer.getByLabelText(/what you hold, and what you did/i), "Exported it");

    await user.click(within(dialog).getByRole("tab", { name: /messages/i }));
    const messages = within(within(dialog).getByRole("tabpanel", { name: /messages/i }));
    expect(messages.getByText(/a message does not answer the ticket/i)).toBeInTheDocument();
    expect(messages.queryByRole("button", { name: "Submit answer" })).not.toBeInTheDocument();
    await user.type(messages.getByRole("textbox", { name: "Message" }), "Which store do you mean?");
    await user.click(messages.getByRole("button", { name: "Send message" }));
    await vi.waitFor(() => expect(sent).toBe(1));
    expect(returned).toBeNull();
    // The window stays open, and the answer half-typed on the other tab is
    // still there.
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    await user.click(messages.getByRole("button", { name: "Answer the ticket" }));
    expect(answer.getByLabelText(/what you hold, and what you did/i)).toHaveValue("Exported it");

    await user.click(answer.getByLabelText("Did all of it"));
    await user.click(answer.getByRole("button", { name: "Submit answer" }));
    await vi.waitFor(() => expect(returned).toMatch(/name="summary"\r\n\r\nExported it/));
    await vi.waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });

  it("lets the holder move the date their answer is due, with the reason", async () => {
    // 2026-11-12: as on a breach ticket; the Privacy Office is told.
    let sent: { due_at: string; reason: string } | null = null;
    const dated = ticket({
      due_at: "2030-01-10T18:29:00Z",
      may_change_date: true,
      request_due_at: "2030-02-01T10:00:00Z",
    });
    serve([dated]);
    server.use(
      http.post(`${API}/tickets/:uuid/answer-by`, async ({ request }) => {
        sent = (await request.json()) as { due_at: string; reason: string };
        return HttpResponse.json(dated);
      }),
    );
    const { user } = render(<TicketsPage />);
    await user.click(await screen.findByRole("button", { name: /^answer/i }));
    const dialog = await screen.findByRole("dialog");
    await user.click(await within(dialog).findByRole("button", { name: "Change the date" }));
    expect(within(dialog).getByText(/^The Privacy Office is told\./)).toBeInTheDocument();
    const date = within(dialog).getByLabelText(/^new answer by date/i);
    expect(date).toHaveAttribute("max", "2030-01-31");
    // It opens on the date the ticket has; a new one is put in its place.
    expect(date).toHaveValue("2030-01-10");
    await user.clear(date);
    await user.type(date, "2030-01-18");
    await user.type(within(dialog).getByLabelText(/^reason/i), "On leave until the 15th");
    await user.click(within(dialog).getByRole("button", { name: "Change the date" }));

    await vi.waitFor(() => expect(sent).not.toBeNull());
    expect(sent!.reason).toBe("On leave until the 15th");
    expect(new Date(sent!.due_at).getTime()).toBe(new Date(2030, 0, 18, 23, 59).getTime());
  });

  it("offers no date change on a ticket that is not waiting on the holder", async () => {
    serve([review]);
    const { user } = render(<TicketsPage />);
    await user.click(await screen.findByRole("button", { name: /^open/i }));
    const dialog = await screen.findByRole("dialog");
    await within(dialog).findByRole("button", { name: "Send message" });
    expect(within(dialog).queryByRole("button", { name: "Change the date" })).not.toBeInTheDocument();
  });

  it("shows only the messages once the answer is with the office", async () => {
    serve([review]);
    const { user } = render(<TicketsPage />);
    await user.click(await screen.findByRole("button", { name: /^open/i }));
    const dialog = await screen.findByRole("dialog");
    expect(await within(dialog).findByRole("button", { name: "Send message" })).toBeInTheDocument();
    expect(within(dialog).queryByRole("tab")).not.toBeInTheDocument();
    expect(within(dialog).queryByRole("button", { name: "Submit answer" })).not.toBeInTheDocument();
  });
});
