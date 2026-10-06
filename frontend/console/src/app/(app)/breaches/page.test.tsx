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
  server.use(http.get(`${API}/breaches`, () => HttpResponse.json([LAPTOP, SHARE, OLD])));
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
    expect(screen.getByText("1 past their answer-by")).toBeInTheDocument();

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
});
