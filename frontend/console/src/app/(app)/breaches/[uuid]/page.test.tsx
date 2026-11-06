/**
 * The breach page as one workspace, in tabs like the project page.
 *
 * What is pinned: closing it sits above the tabs, beside the facts it was
 * logged with (after the tabs on a phone, by CSS - jsdom renders both); the duties open first; a late duty is flagged on its tab from
 * whichever tab is open; and the bell's `#tickets` - written before the tabs -
 * still opens the Tickets card, as `#notices` opens People & notices. Every
 * duty but telling the people leads to its report (0059), and who reported an
 * incident through the public link is in its details (0058). A failed background
 * read leaves the page standing, and a ticket's changes are found from Activity
 * by the ticket's own trail.
 */
import { HttpResponse, http } from "msw";
import { afterEach, describe, expect, it, vi } from "vitest";

import BreachPage from "@/app/(app)/breaches/[uuid]/page";
import { keys } from "@/lib/query";
import { makeMe } from "@/test/fixtures";
import { act, render, screen, within } from "@/test/render";
import { API, server } from "@/test/server";
import type { Breach, BreachDuty, BreachTicket } from "@/types";

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
  duty: "cert_in",
  label: "Report to CERT-In",
  basis: "CERT-In Directions 2022 (IT Act s.70B): within 6 hours of noticing",
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
  logged: {},
  cyber_attack: null,
  reported: null,
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

const ORG_BOARD = duty({
  duty: "org_board",
  label: "Organisation's board",
  basis: "Internal policy: within 30 minutes of a validation of yes",
});

const NO_REPORTS = {
  kinds: [
    {
      kind: "org_board",
      title: "Report to the organisation's board",
      basis: "Internal policy",
      duty: "org_board",
      duty_state: "outstanding",
      blocked_by: null,
      goes_to_regulator: false,
      versions: [],
    },
  ],
  board_recipients: 1,
  proofs: [],
};

function serve(b: Breach) {
  server.use(
    http.get(`${API}/breaches/${UUID}`, () => HttpResponse.json(b)),
    http.get(`${API}/breaches/${UUID}/reports`, () => HttpResponse.json(NO_REPORTS)),
    http.get(`${API}/breaches/${UUID}/tickets`, () => HttpResponse.json([])),
    http.get(`${API}/breaches/${UUID}/affected`, () =>
      HttpResponse.json({ total: 0, revisions: [], people: [], next_cursor: null }),
    ),
    http.get(`${API}/breaches/${UUID}/notices`, () =>
      HttpResponse.json({
        versions: [],
        account: [],
        failures: [],
        listed: 0,
        contacts: 0,
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
      "Reports",
      "People & notices",
      "Tickets",
      "Assessment",
      "Attachments",
      "Activity",
    ]);
    expect(within(tabs).getByRole("tab", { name: /Duties/ })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("columnheader", { name: "Due" })).toBeVisible();
    // Not validated yet: the way to the step that starts the clocks.
    const validate = screen.getByRole("link", { name: "Record the validation" });
    expect(validate).toHaveAttribute("href", "#validation");
    expect(validate.parentElement).toHaveTextContent("gives 30 minutes to tell the organisation's board");
    expect(screen.queryByRole("link", { name: /Documents for the Board/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Brief for the organisation's board/ })).not.toBeInTheDocument();
  });

  it("leads a regulator's duty to its report, and counts what is still to send", async () => {
    serve(breach());
    const { user } = render(<BreachPage />);

    const link = await screen.findByRole("link", { name: "Open the report" });
    expect(link).toHaveAttribute("href", "#reports");
    expect(screen.getByRole("tab", { name: /Reports/ })).toHaveTextContent("1");

    await user.click(screen.getByRole("tab", { name: /Reports/ }));
    expect(await screen.findByText("Report to the organisation's board")).toBeVisible();
  });

  it("offers Notify Organization Board in the header and on the duty, while the duty stands", async () => {
    serve(breach({ determination: "yes", breach_reference: "BR-2026-0042", obligations: [ORG_BOARD] }));
    render(<BreachPage />);

    const buttons = await screen.findAllByRole("button", { name: "Notify Organization Board" });
    expect(buttons).toHaveLength(2);
    expect(screen.queryByRole("link", { name: "Open the report" })).not.toBeInTheDocument();
  });

  it("does not ask to tell the board before a yes, and says no clock is running", async () => {
    serve(breach({ obligations: [] }));
    window.history.replaceState(null, "", "/#validation");
    render(<BreachPage />);

    expect(await screen.findByText("Still validating. No clock is running yet.")).toBeVisible();
    expect(screen.queryByRole("button", { name: "Notify Organization Board" })).not.toBeInTheDocument();
  });

  it("says who reported it when it came through the public link", async () => {
    serve(
      breach({
        reported: {
          reporter_name: "Asha Rao",
          reporter_email: "asha@example.org",
          received_at: "2026-10-06T08:00:00Z",
          noticed_at: null,
          cyber_attack: "yes",
        },
      }),
    );
    render(<BreachPage />);

    expect((await screen.findAllByText("Asha Rao")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("asha@example.org").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Not said").length).toBeGreaterThan(0);
    expect(screen.getAllByText("They say it was").length).toBeGreaterThan(0);
    expect(screen.queryByText(/reportable to CERT-In$/)).not.toBeInTheDocument();
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

  it("keeps the page through a failed background read, so an open form is not lost", async () => {
    serve(breach());
    const { queryClient } = render(<BreachPage />);
    await screen.findByRole("button", { name: "Close the breach" });

    server.use(
      http.get(`${API}/breaches/${UUID}`, () =>
        HttpResponse.json({ error: { code: "unavailable", message: "Down for a moment" } }, { status: 503 }),
      ),
    );
    await act(async () => {
      await queryClient.refetchQueries({ queryKey: keys.breach.detail(UUID), exact: true });
      // The query tells the screen on the next turn of the loop.
      await new Promise((resolve) => setTimeout(resolve, 10));
    });

    expect(queryClient.getQueryState(keys.breach.detail(UUID))?.status).toBe("error");
    expect(screen.queryByText("Could not load this incident")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Close the breach" })).toBeInTheDocument();
  });

  it("says so when the incident cannot be read at all", async () => {
    server.use(
      http.get(`${API}/breaches/${UUID}`, () =>
        HttpResponse.json({ error: { code: "unavailable", message: "Down for a moment" } }, { status: 503 }),
      ),
      http.get(`${API}/breaches/${UUID}/tickets`, () => HttpResponse.json([])),
    );
    render(<BreachPage />);

    expect(await screen.findByText("Could not load this incident")).toBeInTheDocument();
  });

  it("says a ticket's changes are on its own trail, and goes there from Activity", async () => {
    const TICKET = "88888888-8888-4888-8888-888888888888";
    serve(breach());
    server.use(
      http.get(`${API}/breaches/${UUID}/tickets`, () =>
        HttpResponse.json([
          { ticket_uuid: TICKET, holder_name: "Arun Shetty", state: "issued", created_at: "2026-10-06T10:00:00Z" } as BreachTicket,
        ]),
      ),
    );
    window.history.replaceState(null, "", "/#activity");
    render(<BreachPage />);

    expect(await screen.findByText(/on that ticket's own trail/)).toBeVisible();
    const history = document.getElementById("history") as HTMLElement;
    const row = (await within(history).findByText("Arun Shetty")).closest("li") as HTMLElement;
    const link = within(row).getByRole("link", { name: "Audit trail" });
    const href = new URL(link.getAttribute("href") ?? "", "http://cmp.local");
    expect(href.pathname).toBe("/audit");
    expect(href.searchParams.get("entity_type")).toBe("breach_ticket");
    expect(href.searchParams.get("entity")).toBe(TICKET);
    // No name in an address.
    expect(href.searchParams.get("label")).not.toContain("Arun");
  });

  it("keeps the hidden Actions heading inside the duties table, or the page scrolls sideways on a phone", async () => {
    serve(breach());
    render(<BreachPage />);

    expect(await screen.findByRole("columnheader", { name: "Actions" })).toHaveClass("relative");
  });
});
