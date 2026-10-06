/**
 * The breach page as one workspace, in tabs like the project page.
 *
 * What is pinned: closing it sits above the tabs, beside the facts it was
 * logged with (after the tabs on a phone, by CSS - jsdom renders both); the duties open first; a late duty is flagged on its tab from
 * whichever tab is open; and the bell's `#tickets` - written before the tabs -
 * still opens the Tickets card, as `#notices` opens People & notices.
 */
import { HttpResponse, http } from "msw";
import { afterEach, describe, expect, it, vi } from "vitest";

import BreachPage from "@/app/(app)/breaches/[uuid]/page";
import { makeMe } from "@/test/fixtures";
import { act, render, screen, within } from "@/test/render";
import { API, server } from "@/test/server";
import type { Breach, BreachDuty } from "@/types";

const UUID = "66666666-6666-4666-8666-666666666666";

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
  useAuth: () => ({ me: makeMe({ role: "dpo", nav: ["dashboard", "breaches", "audit"] }) }),
  useToast: () => ({ success: vi.fn(), error: vi.fn(), warning: vi.fn() }),
}));

const duty = (over: Partial<BreachDuty> = {}): BreachDuty => ({
  obligation_uuid: "77777777-7777-4777-8777-777777777777",
  duty: "org_board",
  label: "Organisation's board",
  basis: "Internal policy: thirty minutes from first noticed",
  created_at: "2026-10-06T09:00:00Z",
  state: "outstanding",
  due_at: "2026-10-06T09:30:00Z",
  anchored_at: "2026-10-06T09:00:00Z",
  completed_at: null,
  reference: null,
  reported_to: null,
  extended_until: null,
  extension_requested_at: null,
  clock: {
    without_delay: false,
    seconds_remaining: 600,
    overdue: false,
    seconds_elapsed: 1200,
    target_at: null,
    past_target: false,
  },
  events: [],
  ...over,
});

const breach = (over: Partial<Breach> = {}): Breach => ({
  breach_uuid: UUID,
  reference: "INC-2026-0042",
  incident_reference: "INC-2026-0042",
  breach_reference: null,
  title: "A laptop left on a train",
  status: "open",
  detected_at: "2026-10-06T09:00:00Z",
  location: { kind: "other", processor_uuid: null, processor_name: null, source_uuid: null, source_name: null, detail: null },
  determination: "pending",
  breach_recorded_at: null,
  breach_recorded_by_name: null,
  became_aware_at: null,
  began_at: null,
  began_at_recorded: null,
  recorded_at: "2026-10-06T09:05:00Z",
  recorded_by_name: "Priya Menon",
  determinations: [],
  assessment: null,
  assessment_revisions: 0,
  obligations: [duty()],
  attachments: [],
  status_history: [
    { from_status: null, to_status: "open", reason: null, changed_at: "2026-10-06T09:05:00Z", changed_by_name: "Priya Menon" },
  ],
  transitions: [
    { to: "closed", allowed: false, blocked_by: "validation", blockers: ["It has not been validated"], reason_required: false },
  ],
  without_delay_target_hours: null,
  ...over,
});

function serve(b: Breach) {
  server.use(
    http.get(`${API}/breaches/${UUID}`, () => HttpResponse.json(b)),
    http.get(`${API}/breaches/${UUID}/tickets`, () => HttpResponse.json([])),
    http.get(`${API}/breaches/${UUID}/affected`, () =>
      HttpResponse.json({ total: 0, revisions: [], people: [], next_cursor: null, platform_tables: [] }),
    ),
    http.get(`${API}/breaches/${UUID}/notices`, () =>
      HttpResponse.json({
        versions: [],
        account: [],
        failures: [],
        listed: 0,
        unnotified: 0,
        contents: [],
        duty: "",
        send_blocked_by: "Record the breach before anyone is notified",
      }),
    ),
    http.get(`${API}/users`, () => HttpResponse.json({ items: [], total: 0, page: 1, page_size: 25 })),
  );
}

afterEach(() => {
  window.history.replaceState(null, "", "/");
});

describe("the breach page", () => {
  it("puts closing and the facts above the tabs, and opens on the duties", async () => {
    serve(breach());
    render(<BreachPage />);

    expect(await screen.findByRole("button", { name: "Close the breach" })).toBeDisabled();
    expect(screen.getByText("It has not been validated")).toBeInTheDocument();
    expect(screen.getAllByText("First noticed").length).toBeGreaterThan(0);

    const tabs = screen.getByRole("tablist", { name: "Breach sections" });
    expect(within(tabs).getAllByRole("tab").map((t) => t.textContent?.replace(/\d+/g, "").trim())).toEqual([
      "Duties",
      "Validation",
      "People & notices",
      "Tickets",
      "Assessment",
      "Attachments",
      "Activity",
    ]);
    expect(within(tabs).getByRole("tab", { name: /Duties/ })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("columnheader", { name: "Due" })).toBeVisible();
    // Not validated yet: the way to the step that starts the clocks.
    expect(screen.getByRole("link", { name: "Record the validation" })).toHaveAttribute("href", "#validation");
  });

  it("flags a late duty on its tab, whichever tab is open", async () => {
    serve(breach({ obligations: [duty({ clock: { ...duty().clock, overdue: true, seconds_remaining: -60 } })] }));
    window.history.replaceState(null, "", "/#assessment");
    render(<BreachPage />);

    const tab = await screen.findByRole("tab", { name: /Duties/ });
    expect(tab).toHaveTextContent("1 late");
    expect(screen.getByRole("tab", { name: /Assessment/ })).toHaveAttribute("aria-selected", "true");
  });

  it("opens the tab holding the card an older address names", async () => {
    serve(breach());
    window.history.replaceState(null, "", "/#tickets");
    const { user } = render(<BreachPage />);

    expect(await screen.findByRole("tab", { name: /Tickets/ })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText("Tickets wait for the breach to be recorded")).toBeVisible();

    await act(async () => {
      window.history.replaceState(null, "", "/#notices");
      window.dispatchEvent(new HashChangeEvent("hashchange"));
    });
    expect(screen.getByRole("tab", { name: /People & notices/ })).toHaveAttribute("aria-selected", "true");

    await user.click(screen.getByRole("tab", { name: /Activity/ }));
    expect(window.location.hash).toBe("#activity");
    expect(screen.getByText("Logged as")).toBeVisible();
  });
});
