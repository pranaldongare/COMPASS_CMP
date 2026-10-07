/**
 * One rights request, as the DPO works it (2026-10-07).
 *
 * What is pinned: the next step - In progress, and the rest the server offers
 * - comes straight after step 4, before the holders, so it is not a search;
 * refusing is a button that says what it does; and the documents the
 * requester sent are listed with the request, each one downloadable.
 */
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";

import RequestPage from "@/app/(app)/requests/[uuid]/page";
import { makeMe, makeRequestDetail } from "@/test/fixtures";
import { render, screen } from "@/test/render";
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

describe("RequestPage", () => {
  it("puts the next step straight after classification, before the holders", async () => {
    serve(verified);
    render(<RequestPage />);
    const next = await screen.findByRole("heading", { name: "Next step" });
    const classification = screen.getByRole("heading", { name: "Identity and classification" });
    const holders = screen.getByRole("heading", { name: "Holders" });
    const follows = (a: Element, b: Element) =>
      Boolean(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);
    expect(follows(classification, next)).toBe(true);
    expect(follows(next, holders)).toBe(true);
    expect(screen.getByRole("button", { name: /In progress/ })).toBeEnabled();
    expect(screen.getByRole("link", { name: /Move to in progress/i })).toHaveAttribute(
      "href",
      "#actions",
    );
    // Nothing to respond with yet, so no empty response heading.
    expect(screen.queryByRole("heading", { name: "Response and outcome" })).not.toBeInTheDocument();
  });

  it("makes refusing a button that says what it does", async () => {
    serve({ ...verified, classified_at: null });
    const { user } = render(<RequestPage />);
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
    expect(screen.getByRole("button", { name: "Download id-proof.pdf" })).toBeInTheDocument();
  });
});
