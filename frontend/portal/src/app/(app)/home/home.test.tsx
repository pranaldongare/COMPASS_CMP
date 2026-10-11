/**
 * Her home (2026-10-11): every figure and row is counted from her own
 * records, and opens them.
 *
 * What these hold: the figures read her consents the way My consents does
 * (anything still granted is active; a withdrawal with nothing left is
 * withdrawn), open requests give the soonest due date, "Needs attention" lists
 * only what the data says - a late request, a response to download, a
 * nomination naming her - and a quiet day says so in one line.
 */
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";

import HomePage from "@/app/(app)/home/page";
import { makeClock, makeMe, makeMyRequest } from "@/test/fixtures";
import { render, screen, within } from "@/test/render";
import { API, server } from "@/test/server";
import type { AuditEntry, MyConsent } from "@/types";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => "/home",
}));
vi.mock("@/providers", () => ({
  useAuth: () => ({ me: makeMe({ role: "data_subject", full_name: "Anjali Verma" }) }),
}));

function consent(overrides: Partial<MyConsent>): MyConsent {
  return {
    consent_uuid: "11111111-1111-4111-8111-111111111111",
    project_uuid: "22222222-2222-4222-8222-222222222222",
    project_name: "Gait Identification",
    notice_uuid: "33333333-3333-4333-8333-333333333333",
    notice_code: "NTC-GAIT",
    version: 1,
    language_code: "english",
    affirmative_action_at: "2026-09-20T10:00:00Z",
    is_withdrawal: false,
    granted_count: 2,
    purpose_count: 2,
    ...overrides,
  } as MyConsent;
}

const CONSENTS = [
  consent({}),
  consent({
    consent_uuid: "44444444-4444-4444-8444-444444444444",
    project_uuid: "55555555-5555-4555-8555-555555555555",
    project_name: "Fingerprint QA",
    notice_code: "NTC-FP",
    is_withdrawal: true,
    granted_count: 0,
    affirmative_action_at: "2026-09-12T10:00:00Z",
  }),
  consent({
    consent_uuid: "66666666-6666-4666-8666-666666666666",
    project_uuid: "77777777-7777-4777-8777-777777777777",
    project_name: "Retail Footfall",
    notice_code: "NTC-RETAIL",
    granted_count: 1,
  }),
];

const OPEN = makeMyRequest({
  request_uuid: "88888888-8888-4888-8888-888888888888",
  reference: "RR-2026-018527",
  due_at: "2027-01-08T09:00:00+05:30",
});
const LATE = makeMyRequest({
  request_uuid: "99999999-9999-4999-8999-999999999990",
  reference: "RR-2026-018400",
  status: "in_progress",
  due_at: "2026-10-01T09:00:00+05:30",
  clock: makeClock({ overdue: true, days_remaining: -10 }),
});

const UPDATE = {
  log_uuid: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  event_type: "consent.withdrawn",
  occurred_at: "2026-09-12T10:00:00Z",
  actor_name: null,
  entity_type: "consent",
  entity_id: "44444444-4444-4444-8444-444444444444",
  entity_label: "Fingerprint QA",
} as unknown as AuditEntry;

function serve({ requests = [OPEN], updates = [UPDATE], naming = [] as unknown[] } = {}) {
  server.use(
    http.get(`${API}/me/consents`, () => HttpResponse.json(CONSENTS)),
    http.get(`${API}/me/requests`, () => HttpResponse.json(requests)),
    http.get(`${API}/me/nominee-of`, () => HttpResponse.json(naming)),
    http.get(`${API}/notifications`, () =>
      HttpResponse.json({ items: updates, total: updates.length }),
    ),
  );
}

describe("Home", () => {
  it("greets her by first name and offers to make a request", async () => {
    serve();
    render(<HomePage />);
    expect(
      screen.getByRole("heading", { level: 1, name: "Good day, Anjali" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /make a request/i })).toHaveAttribute(
      "href",
      "/my-requests?new=1",
    );
  });

  it("counts her figures from her own records", async () => {
    serve();
    render(<HomePage />);
    // Active counts anything still granted - Retail Footfall is partial.
    const active = await screen.findByRole("link", { name: /active consents\s*2/i });
    expect(active).toHaveTextContent("2");
    expect(active).toHaveTextContent("across 2 projects");
    expect(active).toHaveAttribute("href", "/my-consents");
    const withdrawn = screen.getByRole("link", { name: /^withdrawn\s*1\s*on/i });
    expect(withdrawn).toHaveTextContent("1");
    expect(withdrawn).toHaveTextContent("on 12 Sept");
    const open = await screen.findByRole("link", { name: /open requests.*1/i });
    expect(open).toHaveTextContent("due 08 Jan");
    expect(open).toHaveAttribute("href", "/my-requests");
    expect(await screen.findByRole("link", { name: /updates.*1/i })).toHaveAttribute(
      "href",
      "/notifications",
    );
  });

  it("lists her consents and requests, each opening its own record", async () => {
    serve();
    render(<HomePage />);
    const consents = screen.getByRole("region", { name: "My consents" });
    const row = await within(consents).findByRole("link", { name: /Fingerprint QA/ });
    expect(row).toHaveAttribute(
      "href",
      "/my-consents?consent=44444444-4444-4444-8444-444444444444",
    );
    expect(row).toHaveTextContent("Withdrawn");
    const requests = screen.getByRole("region", { name: "My requests" });
    const req = await within(requests).findByRole("link", { name: /RR-2026-018527/ });
    expect(req).toHaveAttribute("href", `/my-requests?request=${OPEN.request_uuid}`);
    expect(req).toHaveTextContent("Due 08 Jan");
  });

  it("says a quiet day is quiet", async () => {
    serve();
    render(<HomePage />);
    expect(await screen.findByText("Nothing needs you right now.")).toBeInTheDocument();
  });

  it("raises a late request, a response to download and a nomination naming her", async () => {
    const ready = makeMyRequest({
      request_uuid: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
      status: "closed",
      outcome: "complete",
      download_available: true,
      download_expires_at: new Date(Date.now() + 2 * 86_400_000).toISOString(),
    });
    serve({
      requests: [OPEN, LATE, ready],
      naming: [
        {
          nomination_uuid: "c",
          principal_name: "Ravi",
          status: "pending",
          contact: "r***@x",
        },
      ],
    });
    render(<HomePage />);
    const box = screen.getByRole("region", { name: "Needs attention" });
    const late = await within(box).findByRole("link", { name: /past its deadline/i });
    expect(late).toHaveAttribute("href", `/my-requests?request=${LATE.request_uuid}`);
    expect(late).toHaveTextContent("Late");
    const download = within(box).getByRole("link", { name: /ready to download/i });
    expect(download).toHaveTextContent("Due soon");
    expect(
      await within(box).findByRole("link", { name: /named you to act for them/i }),
    ).toHaveAttribute("href", "/my-nominations");
  });
});
