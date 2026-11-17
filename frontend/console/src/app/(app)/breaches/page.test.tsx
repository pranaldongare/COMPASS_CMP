/**
 * The register found by search and narrowed by the office's questions
 * (2026-10-06): a reference or a title, what is late or due today, what
 * moved recently, where a ticket waits. The filters are the address's, so a
 * filtered register can be shared; every clock and count is the server's.
 */
import { HttpResponse, http } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import BreachesPage from "@/app/(app)/breaches/page";
import { render, screen, within } from "@/test/render";
import { API, server } from "@/test/server";
import type { BreachDuty, BreachSummary } from "@/types";

vi.mock("next/navigation", () => ({
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
  useToast: () => ({ success: vi.fn(), error: vi.fn(), warning: vi.fn() }),
}));

const ago = (hours: number) => new Date(Date.now() - hours * 3_600_000).toISOString();

const duty = (overdue: boolean, secondsLeft: number | null): BreachDuty => ({
  obligation_uuid: crypto.randomUUID(),
  duty: "cert_in",
  label: "Report to CERT-In",
  basis: "CERT-In Directions",
  created_at: ago(5),
  state: "outstanding",
  due_at: ago(1),
  anchored_at: ago(5),
  completed_at: null,
  reference: null,
  reported_to: null,
  extended_until: null,
  extension_requested_at: null,
  clock: {
    without_delay: false,
    seconds_remaining: secondsLeft,
    overdue,
    seconds_elapsed: 3600,
    target_at: null,
    past_target: false,
  },
  events: [],
});

const breach = (over: Partial<BreachSummary>): BreachSummary => ({
  breach_uuid: crypto.randomUUID(),
  reference: "INC-2026-0001",
  incident_reference: "INC-2026-0001",
  breach_reference: null,
  title: "Untitled",
  status: "open",
  detected_at: ago(10),
  location: { kind: "platform", processor_uuid: null, processor_name: null, source_uuid: null, source_name: null, detail: null },
  determination: "pending",
  obligations: [],
  last_activity_at: ago(24 * 40),
  tickets_open: 0,
  tickets_overdue: 0,
  recorded_at: "2026-10-01T09:00:00Z",
  ...over,
});

const LAPTOP = breach({
  reference: "BR-2026-0007",
  incident_reference: "INC-2026-0007",
  breach_reference: "BR-2026-0007",
  title: "Laptop left on a train",
  determination: "yes",
  obligations: [duty(true, -600)],
  last_activity_at: ago(2),
  tickets_open: 2,
  tickets_overdue: 1,
});
const SHARE = breach({
  reference: "INC-2026-0008",
  incident_reference: "INC-2026-0008",
  title: "Share link posted in a chat",
  obligations: [duty(false, 3 * 3600)],
  last_activity_at: ago(30),
});
const OLD = breach({ reference: "INC-2026-0009", incident_reference: "INC-2026-0009", title: "Printer queue" });

beforeEach(() => {
  window.history.replaceState(null, "", "/breaches");
  server.use(
    http.get(`${API}/breaches`, () => HttpResponse.json([LAPTOP, SHARE, OLD])),
    http.get(`${API}/breaches/intake`, () => HttpResponse.json({ items: [], total: 0, limit: 50, offset: 0 })),
  );
});

const shown = () =>
  screen
    .getAllByRole("row")
    .slice(1)
    .map((r) => within(r).getAllByRole("link")[0].textContent);

describe("the register", () => {
  it("is found by a reference it was logged as, or by words of its title", async () => {
    const { user } = render(<BreachesPage />);
    expect(await screen.findByText("Laptop left on a train")).toBeInTheDocument();

    await user.type(screen.getByRole("searchbox", { name: "Search" }), "INC-2026-0007{Enter}");
    expect(shown()).toEqual(["BR-2026-0007"]);
    expect(new URLSearchParams(window.location.search).get("q")).toBe("INC-2026-0007");

    await user.clear(screen.getByRole("searchbox", { name: "Search" }));
    await user.type(screen.getByRole("searchbox", { name: "Search" }), "chat share{Enter}");
    expect(shown()).toEqual(["INC-2026-0008"]);
    expect(screen.getByText("1 of 3 shown")).toBeInTheDocument();
  });

  it("narrows to what is late, due today, recent, or waiting on a ticket", async () => {
    const { user } = render(<BreachesPage />);
    await screen.findByText("Printer queue");

    await user.selectOptions(screen.getByLabelText("Duties"), "overdue");
    expect(shown()).toEqual(["BR-2026-0007"]);
    await user.selectOptions(screen.getByLabelText("Duties"), "due_24h");
    expect(shown()).toEqual(["INC-2026-0008"]);
    await user.selectOptions(screen.getByLabelText("Duties"), "");

    await user.selectOptions(screen.getByLabelText("Recent activity"), "24h");
    expect(shown()).toEqual(["BR-2026-0007"]);
    await user.selectOptions(screen.getByLabelText("Recent activity"), "7d");
    expect(shown()).toEqual(["BR-2026-0007", "INC-2026-0008"]);

    await user.selectOptions(screen.getByLabelText("Tickets"), "overdue");
    expect(shown()).toEqual(["BR-2026-0007"]);
    expect(screen.getByText("1 past their resolve-by date")).toBeInTheDocument();

    await user.click(screen.getAllByRole("button", { name: "Clear filters" })[0]);
    expect(shown()).toHaveLength(3);
    expect(window.location.search).toBe("");
  });

  it("sorts by the most recent activity, or by what is due soonest", async () => {
    window.history.replaceState(null, "", "/breaches?sort=activity");
    const { user } = render(<BreachesPage />);
    await screen.findByText("Printer queue");
    expect(shown()).toEqual(["BR-2026-0007", "INC-2026-0008", "INC-2026-0009"]);

    await user.selectOptions(screen.getByLabelText("Sort"), "due");
    expect(shown()).toEqual(["BR-2026-0007", "INC-2026-0008", "INC-2026-0009"]);
    await user.selectOptions(screen.getByLabelText("Validation"), "pending");
    expect(shown()).toEqual(["INC-2026-0008", "INC-2026-0009"]);
  });

  it("says when nothing matches, and offers to clear", async () => {
    window.history.replaceState(null, "", "/breaches?q=nothing-like-this");
    render(<BreachesPage />);
    expect(await screen.findByText("Nothing matches")).toBeInTheDocument();
  });

  it("shows a report from the public link above the filters, apart from the register", async () => {
    server.use(
      http.get(`${API}/breaches/intake`, () =>
        HttpResponse.json({
          items: [
            {
              report_uuid: "99999999-9999-4999-8999-999999999999",
              reference: "INC-2026-0010",
              reporter_name: "Asha Rao",
              reporter_email: "asha@example.org",
              title: "A file on a public share",
              noticed_at: null,
              received_at: ago(1),
              cyber_attack: null,
            },
          ],
          total: 1,
          limit: 50,
          offset: 0,
        }),
      ),
    );
    render(<BreachesPage />);

    const intake = await screen.findByTestId("incident-intake");
    expect(within(intake).getByText("A file on a public share")).toBeInTheDocument();
    expect(intake.compareDocumentPosition(screen.getByRole("searchbox", { name: "Search" }))).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING,
    );
    await screen.findByText("Printer queue");
    expect(shown()).not.toContain("INC-2026-0010");
  });

  describe("what is new (2026-11-17)", () => {
    const FRESH = breach({
      reference: "INC-2026-0010",
      incident_reference: "INC-2026-0010",
      title: "Survey answers seen by another team",
      recorded_at: ago(2),
    });
    // Logged long ago, reassigned here an hour ago: new to this office.
    const MOVED = breach({
      reference: "INC-2026-0011",
      incident_reference: "INC-2026-0011",
      title: "Shared drive open to all staff",
      transferred_at: ago(1),
    });
    // Logged today but validated already: somebody has acted on it.
    const SEEN = breach({
      reference: "INC-2026-0012",
      incident_reference: "INC-2026-0012",
      title: "Badge list in a bin",
      recorded_at: ago(1),
      determination: "no",
    });

    it("counts what waits, what is new and what is late, and marks the new rows", async () => {
      server.use(
        http.get(`${API}/breaches`, () => HttpResponse.json([LAPTOP, FRESH, MOVED, SEEN, OLD])),
        http.get(`${API}/breaches/intake`, () =>
          HttpResponse.json({
            items: [
              {
                report_uuid: crypto.randomUUID(),
                reference: "INC-2026-0147",
                reporter_name: "Asha Rao",
                reporter_email: "asha@example.org",
                title: "Customer list emailed to the wrong vendor",
                noticed_at: null,
                received_at: ago(1),
                cyber_attack: null,
                escalated_at: ago(0.2),
              },
            ],
            total: 2,
            limit: 50,
            offset: 0,
          }),
        ),
      );
      render(<BreachesPage />);
      const tiles = within(await screen.findByRole("region", { name: "Needs attention" }));
      const tile = (label: string) => tiles.getByText(label).closest("a")!;
      await vi.waitFor(() => expect(tile("New reports waiting")).toHaveTextContent("2"));
      expect(tile("New reports waiting")).toHaveTextContent("1 escalated to management");
      await vi.waitFor(() => expect(tile("New in your register")).toHaveTextContent("2"));
      expect(tile("Breaches with a duty overdue")).toHaveTextContent("1");
      expect(tile("New in your register")).toHaveAttribute("href", "/breaches?new=1");

      const row = (ref: string) => screen.getByRole("link", { name: ref }).closest("tr")!;
      expect(row("INC-2026-0010")).toHaveAttribute("data-new", "true");
      expect(row("INC-2026-0011")).toHaveAttribute("data-new", "true");
      expect(within(row("INC-2026-0011")).getByText(/Reassigned to your office/)).toBeInTheDocument();
      expect(row("INC-2026-0012")).not.toHaveAttribute("data-new");
      expect(row("INC-2026-0009")).not.toHaveAttribute("data-new");
      expect(row("BR-2026-0007")).not.toHaveAttribute("data-new");
    });

    it("narrows to the new ones from the address", async () => {
      window.history.replaceState(null, "", "/breaches?new=1");
      server.use(http.get(`${API}/breaches`, () => HttpResponse.json([LAPTOP, FRESH, MOVED, SEEN, OLD])));
      render(<BreachesPage />);
      await screen.findByRole("link", { name: "INC-2026-0010" });
      expect(shown().sort()).toEqual(["INC-2026-0010", "INC-2026-0011"]);
      expect(screen.getByText("2 of 5 shown")).toBeInTheDocument();
    });
  });
});
