/**
 * My tasks for a holder (2026-10-08): tickets in three groups read off the
 * server's state, the answer as its own form with no outcome assumed, and a
 * message that leaves the window open.
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
    await user.click(await within(dialog).findByRole("button", { name: "Submit your answer" }));
    const send = within(dialog).getByRole("button", { name: "Send your answer" });
    expect(send).toBeDisabled();
    for (const radio of within(dialog).getAllByRole("radio")) expect(radio).not.toBeChecked();
    await user.type(within(dialog).getByLabelText(/what you hold, and what you did/i), "Exported it");
    expect(send).toBeDisabled();
    await user.click(within(dialog).getByLabelText("Did all of it"));
    expect(send).toBeEnabled();
  });

  it("keeps the window open after a message", async () => {
    let sent = 0;
    serve([todo], () => (sent += 1));
    const { user } = render(<TicketsPage />);

    await user.click(await screen.findByRole("button", { name: /^answer/i }));
    const dialog = await screen.findByRole("dialog");
    await user.type(await within(dialog).findByRole("textbox"), "Which store do you mean?");
    await user.click(within(dialog).getByRole("button", { name: /^send$/i }));
    await vi.waitFor(() => expect(sent).toBe(1));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });
});
