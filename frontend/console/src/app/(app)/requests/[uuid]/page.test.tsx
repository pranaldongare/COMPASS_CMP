/**
 * One rights request, as the DPO works it (2026-10-07).
 *
 * What is pinned: the next step - In progress, and the rest the server offers
 * - is the first thing the page opens on, ahead of the request, so it is not
 * a search; identity, holders and the response are tabs of their own
 * (2026-10-10), and the old card anchors open them; refusing is a button that
 * says what it does; the documents the requester sent are listed with the
 * request, each one downloadable; and the reports the requester sent through
 * the public link that an office dismissed are on the holders tab (0065).
 */
import { HttpResponse, http } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import RequestPage from "@/app/(app)/requests/[uuid]/page";
import { makeMe, makeRequestDetail } from "@/test/fixtures";
import { render, screen, within } from "@/test/render";
import { API, server } from "@/test/server";
import type { RightsRequestDetail } from "@/types";

const UUID = "99999999-9999-4999-8999-999999999999";

vi.mock("next/navigation", () => ({
  useParams: () => ({ uuid: UUID }),
  useSearchParams: () => new URLSearchParams(window.location.search),
  usePathname: () => window.location.pathname,
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn(), refresh: vi.fn() }),
}));

vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: React.AnchorHTMLAttributes<HTMLAnchorElement>) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

vi.mock("@/providers", () => ({
  useAuth: () => ({ me: makeMe({ role: "dpo", nav: ["dashboard", "requests", "audit"] }) }),
  useToast: () => ({ success: vi.fn(), error: vi.fn(), warning: vi.fn() }),
}));

function serve(over: Partial<RightsRequestDetail>) {
  server.use(
    http.get(`${API}/requests/${UUID}`, () => HttpResponse.json(makeRequestDetail(over))),
    http.get(`${API}/users`, () =>
      HttpResponse.json({ items: [], next_cursor: null, total: 0 }),
    ),
  );
}

const verified: Partial<RightsRequestDetail> = {
  status: "received",
  verification_status: "verified",
  classified_at: "2026-10-07T09:00:00Z",
  transitions: [{ to: "in_progress", allowed: true, via: "transition" }],
};

// The tab lives in the address's fragment; each test starts on the overview.
beforeEach(() => {
  window.history.replaceState(null, "", `/requests/${UUID}`);
});

describe("RequestPage", () => {
  it("opens on the next step, ahead of the request; identity and holders have tabs", async () => {
    serve(verified);
    render(<RequestPage />);
    const next = await screen.findByRole("heading", { name: "Next step" });
    const theRequest = screen.getByRole("heading", { name: "The request" });
    const follows = (a: Element, b: Element) =>
      Boolean(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);
    expect(follows(next, theRequest)).toBe(true);
    expect(screen.getByRole("tab", { name: "Overview" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(
      screen.getByRole("tab", { name: /Identity & classification/ }),
    ).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Holders/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /In progress/ })).toBeEnabled();
    expect(screen.getByRole("link", { name: /Move to in progress/i })).toHaveAttribute(
      "href",
      "#actions",
    );
  });

  it("says there is nothing to respond with yet, rather than an empty form", async () => {
    serve(verified);
    const { user } = render(<RequestPage />);
    await user.click(await screen.findByRole("tab", { name: /Response/ }));
    expect(screen.getByText("Nothing to respond with yet")).toBeInTheDocument();
  });

  it("opens the holders tab from the old holders anchor", async () => {
    window.history.replaceState(null, "", `/requests/${UUID}#holders`);
    serve(verified);
    render(<RequestPage />);
    expect(await screen.findByRole("tab", { name: /Holders/ })).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });

  it("makes refusing a button that says what it does", async () => {
    serve({ ...verified, classified_at: null });
    const { user } = render(<RequestPage />);
    await user.click(await screen.findByRole("tab", { name: /Identity & classification/ }));
    const refuse = await screen.findByRole("button", { name: /Refuse this request/ });
    expect(screen.getByText(/Not a rights request, or cannot be met/)).toBeInTheDocument();
    expect(refuse).toHaveAttribute("aria-expanded", "false");
    await user.click(refuse);
    expect(screen.getByRole("button", { name: /Keep the request/ })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
    expect(screen.getByLabelText(/Reason, in writing/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Refuse and close" })).toBeDisabled();
  });

  it("sends a refusal with the documents it rests on", async () => {
    // 2026-11-12: a response could carry files and a refusal could not.
    // The form as it went, as text: reading it as a form does not finish
    // under this test's environment.
    let sent: string | null = null;
    serve({ ...verified, classified_at: null });
    server.use(
      http.post(`${API}/requests/${UUID}/refuse`, async ({ request }) => {
        sent = await request.text();
        return HttpResponse.json(makeRequestDetail({ status: "closed", outcome: "refused" }));
      }),
    );
    const { user } = render(<RequestPage />);
    await user.click(await screen.findByRole("tab", { name: /Identity & classification/ }));
    await user.click(await screen.findByRole("button", { name: /Refuse this request/ }));
    await user.type(screen.getByLabelText(/Reason, in writing/), "The retention floor has not passed.");

    expect(screen.getByRole("button", { name: "Attach files" })).toBeInTheDocument();
    const schedule = new File(["%PDF-1.4"], "retention-schedule.pdf", { type: "application/pdf" });
    await user.upload(screen.getByLabelText(/Documents sent with the refusal/), schedule);
    expect(screen.getByText("retention-schedule.pdf")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Attach more files" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Refuse and close" }));
    // Asked first (2026-11-12), saying what the requester is sent; nothing goes before the yes.
    const question = await screen.findByRole("dialog", { name: /Refuse .* and close it\?/ });
    expect(within(question).getByText(/The requester is emailed your reason and the name of the 1 document attached/)).toBeInTheDocument();
    expect(sent).toBeNull();
    await user.click(within(question).getByRole("button", { name: "Refuse and close" }));
    await vi.waitFor(() => expect(sent).not.toBeNull());
    expect(sent).toMatch(/name="reason"\r\n\r\nThe retention floor has not passed\./);
    // The file is a part of the form. Its name is not asserted: this test's
    // FormData is not the browser's, and names every file "blob".
    expect(sent).toMatch(/name="files"; filename="[^"]+"\r\nContent-Type: application\/pdf/);
  });

  it("lists the documents the requester sent, each one downloadable", async () => {
    serve({
      ...verified,
      attachments: [
        {
          attachment_uuid: "abababab-abab-4bab-8bab-abababababab",
          file_name: "id-proof.pdf",
          size_bytes: 2048,
          content_type: "application/pdf",
          added_at: "2026-10-07T09:01:00Z",
        },
      ],
    });
    render(<RequestPage />);
    expect(await screen.findByText(/Documents from the requester · 1/)).toBeInTheDocument();
    expect(screen.getByText("id-proof.pdf")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Download id-proof.pdf" }),
    ).toBeInTheDocument();
  });

  it("shows the reports from the public link on the holders tab of an access or erasure request, not on a grievance", async () => {
    const found = {
      looked: true,
      not_looked_because: null,
      items: [
        {
          report_uuid: "cdcdcdcd-cdcd-4dcd-8dcd-cdcdcdcdcdcd",
          reference: "INC-2026-0041",
          reporter_name: "Meera Iyer",
          reporter_email: "meera.iyer@example.com",
          title: "A test by the helpdesk",
          received_at: "2026-11-05T09:00:00Z",
          dismissed_at: "2026-11-05T12:00:00Z",
          reporter_erased_at: null,
        },
      ],
      total: 1,
      erased: 0,
      may_erase: true,
      erase_blocked_by: null,
    };
    for (const request_type of ["access", "erasure"] as const) {
      window.history.replaceState(null, "", `/requests/${UUID}#public-reports`);
      serve({ ...verified, request_type, status: "in_progress", public_reports: found });
      const { unmount } = render(<RequestPage />);
      expect(await screen.findByRole("tab", { name: /Holders/ })).toHaveAttribute(
        "aria-selected",
        "true",
      );
      const card = (
        await screen.findByRole("heading", { name: "Reports from the public link" })
      ).closest("#public-reports") as HTMLElement;
      expect(within(card).getByText("INC-2026-0041")).toBeInTheDocument();
      unmount();
    }

    for (const over of [
      { request_type: "erasure" as const, public_reports: null },
      { request_type: "grievance" as const, public_reports: found },
    ]) {
      window.history.replaceState(null, "", `/requests/${UUID}`);
      serve({ ...verified, ...over });
      const { unmount } = render(<RequestPage />);
      await screen.findByRole("heading", { name: "Next step" });
      expect(
        screen.queryByRole("heading", { name: "Reports from the public link" }),
      ).not.toBeInTheDocument();
      unmount();
    }
  });
});
