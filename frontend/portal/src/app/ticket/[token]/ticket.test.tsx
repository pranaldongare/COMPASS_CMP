/**
 * An outside holder's ticket on the portal (0049, 2026-10-08): the link shows
 * whose ticket it is and where a code will go; the code opens the ticket; the
 * answer asks what was done, with nothing chosen, before it can be sent.
 */
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";

import HolderTicketPage from "@/app/ticket/[token]/page";
import { render, screen, within } from "@/test/render";
import { API, server } from "@/test/server";

const TOKEN = "abcdefghijklmnopqrstuvwxyz0123456789ABCDEFG";

vi.mock("next/navigation", () => ({
  useParams: () => ({ token: TOKEN }),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  usePathname: () => `/ticket/${TOKEN}`,
}));

const link = (signedIn: boolean) => ({
  reference: "RR-2026-000042",
  holder_label: "Vendor archive",
  request_type: "access",
  code_goes_to: "k•••@vendor.example",
  state: "waiting",
  state_label: "To answer",
  due_at: "2026-10-20T18:29:00Z",
  signed_in: signedIn,
});

const detail = {
  ticket: {
    holder_uuid: "h1",
    reference: "RR-2026-000042",
    request_type: "access",
    request_status: "awaiting_holders",
    label: "Vendor archive",
    instruction: "Tell us what your archive holds on her.",
    ticket_status: "issued",
    due_at: "2026-10-20T18:29:00Z",
    returned_at: null,
    return_summary: null,
    return_outcome: null,
    sent_back_at: null,
    sent_back_reason: null,
    accepted_at: null,
    state: "waiting",
    state_label: "To answer",
    overdue: false,
  },
  messages: [
    {
      message_uuid: "m1",
      author_side: "system",
      author_name: null,
      kind: "brief",
      body: "About: the person named.",
      evidence_hash: null,
      evidence_name: null,
      created_at: "2026-10-02T10:00:00Z",
    },
  ],
  items: [],
};

describe("an outside holder's ticket", () => {
  it("opens with a code sent to the ticket's address, then shows what is asked", async () => {
    let verified = false;
    server.use(
      http.get(`${API}/holder-tickets/${TOKEN}`, () => HttpResponse.json(link(false))),
      http.post(`${API}/holder-tickets/${TOKEN}/code`, () =>
        HttpResponse.json({ ok: true, message: "A code is on its way." }),
      ),
      http.post(`${API}/holder-tickets/${TOKEN}/verify`, () => {
        verified = true;
        return HttpResponse.json({ ok: true });
      }),
      http.get(`${API}/holder-tickets/${TOKEN}/ticket`, () =>
        verified ? HttpResponse.json(detail) : HttpResponse.json({ error: { code: "code_needed", message: "x", request_id: "t" } }, { status: 401 }),
      ),
    );
    const { user } = render(<HolderTicketPage />);

    expect(await screen.findByText("k•••@vendor.example")).toBeInTheDocument();
    expect(screen.queryByText(/tell us what your archive holds/i)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Send code" }));
    await user.type(await screen.findByLabelText(/six-digit code/i), "123456");
    await user.click(screen.getByRole("button", { name: "Open the ticket" }));

    expect(await screen.findByText("Tell us what your archive holds on her.")).toBeInTheDocument();
    expect(screen.getByText("About: the person named.")).toBeInTheDocument();
  });

  it("asks what was done, with nothing chosen, before the answer can go", async () => {
    server.use(
      http.get(`${API}/holder-tickets/${TOKEN}`, () => HttpResponse.json(link(true))),
      http.get(`${API}/holder-tickets/${TOKEN}/ticket`, () => HttpResponse.json(detail)),
    );
    const { user } = render(<HolderTicketPage />);

    // The page opens on the answer (2026-11-12): no button to find it behind.
    expect(await screen.findByRole("tab", { name: /answer the ticket/i })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    const answer = within(screen.getByRole("tabpanel", { name: /answer the ticket/i }));
    const submit = answer.getByRole("button", { name: "Submit answer" });
    expect(submit).toBeDisabled();
    for (const radio of answer.getAllByRole("radio")) expect(radio).not.toBeChecked();
    await user.type(answer.getByLabelText(/what you hold, and what you did/i), "Two boxes.");
    expect(submit).toBeDisabled();
    await user.click(answer.getByLabelText("Did all of it"));
    expect(submit).toBeEnabled();
  });

  it("keeps messages on their own tab, and says a message is not an answer", async () => {
    let written: string | null = null;
    server.use(
      http.get(`${API}/holder-tickets/${TOKEN}`, () => HttpResponse.json(link(true))),
      http.get(`${API}/holder-tickets/${TOKEN}/ticket`, () => HttpResponse.json(detail)),
      http.post(`${API}/holder-tickets/${TOKEN}/messages`, async ({ request }) => {
        written = await request.text();
        return HttpResponse.json(detail);
      }),
    );
    const { user } = render(<HolderTicketPage />);
    const answer = within(await screen.findByRole("tabpanel", { name: /answer the ticket/i }));
    expect(answer.queryByRole("button", { name: /send message/i })).not.toBeInTheDocument();
    await user.type(answer.getByLabelText(/what you hold, and what you did/i), "Two boxes.");

    await user.click(screen.getByRole("tab", { name: /messages/i }));
    const messages = within(screen.getByRole("tabpanel", { name: /messages/i }));
    expect(messages.getByText(/a message does not answer the ticket/i)).toBeInTheDocument();
    expect(messages.queryByRole("button", { name: "Submit answer" })).not.toBeInTheDocument();
    await user.type(messages.getByLabelText(/message to the privacy office/i), "Which archive?");
    await user.click(messages.getByRole("button", { name: "Send message" }));
    await vi.waitFor(() => expect(written).toMatch(/Which archive\?/));

    // Back on the answer, what was typed there is still there.
    await user.click(messages.getByRole("button", { name: "Answer the ticket" }));
    expect(answer.getByLabelText(/what you hold, and what you did/i)).toHaveValue("Two boxes.");
  });

  it("says a link that opens nothing is not valid, and nothing more", async () => {
    server.use(
      http.get(`${API}/holder-tickets/${TOKEN}`, () =>
        HttpResponse.json({ error: { code: "not_found", message: "x", request_id: "t" } }, { status: 404 }),
      ),
    );
    render(<HolderTicketPage />);
    expect(await screen.findByText("This link is not valid")).toBeInTheDocument();
  });
});
