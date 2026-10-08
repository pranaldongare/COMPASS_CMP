/**
 * An outside holder's ticket on the portal (0049, 2026-10-08): the link shows
 * whose ticket it is and where a code will go; the code opens the ticket; the
 * answer asks what was done, with nothing chosen, before it can be sent.
 */
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";

import HolderTicketPage from "@/app/ticket/[token]/page";
import { render, screen } from "@/test/render";
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
    await user.click(screen.getByRole("button", { name: "Send me a code" }));
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

    await user.click(await screen.findByRole("button", { name: "Submit your answer" }));
    const send = screen.getByRole("button", { name: "Send your answer" });
    expect(send).toBeDisabled();
    for (const radio of screen.getAllByRole("radio")) expect(radio).not.toBeChecked();
    await user.type(screen.getByLabelText(/what you hold, and what you did/i), "Two boxes.");
    expect(send).toBeDisabled();
    await user.click(screen.getByLabelText("Did all of it"));
    expect(send).toBeEnabled();
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
