/**
 * Analytics (ADR 0045): the tabs are the catalogue's, the office is
 * management's to choose, a withheld figure reads "< N" and never 0, a
 * status reads in words, and reports, schedules and targets send what the
 * API takes.
 */
import { HttpResponse, http } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AnalyticsPage from "@/app/(app)/analytics/page";
import { makeMe } from "@/test/fixtures";
import { render, screen, waitFor, within } from "@/test/render";
import { API, server } from "@/test/server";
import type {
  AnalyticsSettings,
  Catalogue,
  Figure,
  Figures,
  Me,
  Report,
  ReportSchedule,
} from "@/types";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(window.location.search),
  usePathname: () => window.location.pathname,
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
}));

let me: Me | null = null;
vi.mock("@/providers", () => ({
  useAuth: () => ({ me }),
  useToast: () => ({ success: vi.fn(), error: vi.fn(), warning: vi.fn() }),
}));

const PERIODS = [
  { key: "this_month", label: "This month" },
  { key: "last_month", label: "Last month" },
  { key: "this_fy", label: "This financial year" },
  { key: "custom", label: "Custom dates" },
];

const REPORT_KINDS: Catalogue["reports"] = [
  {
    key: "management_scorecard",
    title: "Management scorecard",
    description: "Every scorecard figure.",
    formats: ["pdf", "xlsx"],
    schedulable: true,
    recipient_roles: ["dpo", "legal", "management"],
  },
  {
    key: "audit",
    title: "Audit report",
    description: "One of the ready-made audit reports.",
    formats: ["csv", "xlsx", "pdf"],
    schedulable: true,
    recipient_roles: ["admin", "dpo", "legal"],
  },
  {
    key: "case_evidence",
    title: "Evidence pack",
    description: "The full trail of one case.",
    formats: ["pdf"],
    schedulable: false,
    recipient_roles: ["admin", "dpo", "legal"],
  },
];

function catalogue(
  role: string,
  sections: string[],
  over: Partial<Catalogue> = {},
): Catalogue {
  return {
    role,
    office: null,
    may_choose_office: role === "management",
    sections,
    metrics: [
      {
        key: "rights_on_time",
        title: "Requests answered on time",
        definition: "Rights requests closed within their deadline, of all closed.",
        unit: "percent",
        section: sections[0],
        group: "Rights requests",
        kind: "ratio",
        dims: ["type", "office"],
        people: true,
        numerator: "rights.closed_on_time",
        denominator: "rights.closed",
        higher_is_better: true,
      },
    ],
    dimensions: [
      { key: "office", label: "Office" },
      { key: "type", label: "Request type" },
    ],
    periods: PERIODS,
    cadences: [
      { key: "weekly", label: "Every Monday, for the week before" },
      { key: "monthly", label: "On the 1st, for the month before" },
    ],
    reports: REPORT_KINDS,
    audit_reports: [],
    ...over,
  };
}

function figure(over: Partial<Figure> = {}): Figure {
  return {
    key: "rights_on_time",
    title: "Requests answered on time",
    definition: "Rights requests closed within their deadline, of all closed.",
    unit: "percent",
    section: "management",
    group: "Rights requests",
    kind: "ratio",
    dims: ["type", "office"],
    numerator: null,
    denominator: null,
    value: 92.5,
    suppressed: false,
    previous: 88,
    previous_suppressed: false,
    change: 4.5,
    target: 95,
    amber: 85,
    higher_is_better: true,
    status: "amber",
    series: [
      { bucket: "2026-11-01", value: 90, suppressed: false },
      { bucket: "2026-11-02", value: 95, suppressed: false },
    ],
    breakdown: [],
    ...over,
  };
}

function figures(metrics: Figure[]): Figures {
  const period = {
    preset: "this_month",
    start: "2026-11-01T00:00:00+05:30",
    end: "2026-12-01T00:00:00+05:30",
    label: "November 2026",
    start_date: "2026-11-01",
    end_date: "2026-11-30",
  };
  return {
    period,
    previous: { ...period, preset: "last_month", label: "October 2026" },
    office: null,
    dim: null,
    grain: "day",
    threshold: 5,
    metrics,
  };
}

function report(over: Partial<Report> = {}): Report {
  return {
    report_uuid: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    kind: "management_scorecard",
    title: "Management scorecard, October 2026",
    params: {},
    office: null,
    format: "pdf",
    status: "ready",
    file_sha256: "ab",
    file_bytes: 20480,
    error: null,
    requested_by_name: "Meera Nair",
    requested_role: "management",
    schedule_uuid: null,
    created_at: "2026-11-02T09:00:00Z",
    ready_at: "2026-11-02T09:00:05Z",
    ...over,
  };
}

const MANAGEMENT = catalogue("management", [
  "management",
  "analytics",
  "inventory",
  "reports",
]);
const ADMIN = catalogue("admin", ["audit", "health", "quality", "reports"]);
const RND = catalogue("rnd_user", ["mine", "reports"], { reports: [] });

function serve(cat: Catalogue, metrics: Figure[] = [figure()]) {
  server.use(
    http.get(`${API}/analytics/catalogue`, () => HttpResponse.json(cat)),
    http.get(`${API}/analytics/figures`, () => HttpResponse.json(figures(metrics))),
    http.get(`${API}/reports`, () => HttpResponse.json([])),
    http.get(`${API}/reports/schedules`, () => HttpResponse.json([])),
    http.get(`${API}/analytics/inventory`, () =>
      HttpResponse.json({ purposes: [], processors: [], sources: [] }),
    ),
    http.get(`${API}/analytics/audit-reports/:key`, () =>
      HttpResponse.json({
        key: "privileged",
        title: "Privileged actions",
        description: "Accounts made.",
        events: [],
        period: figures([]).period,
        items: [],
        next_cursor: null,
        total: 0,
        summary: { total: 0, by_event: [], by_actor_role: [] },
      }),
    ),
    http.get(`${API}/audit/vocabulary`, () =>
      HttpResponse.json({
        entity_types: [],
        event_groups: [],
        event_types: [],
        lookups: [],
      }),
    ),
  );
}

function tabNames(): string[] {
  return within(screen.getByRole("tablist", { name: "Analytics" }))
    .getAllByRole("tab")
    .map((t) => t.textContent ?? "");
}

beforeEach(() => {
  window.history.replaceState(null, "", "/analytics");
  me = makeMe({ role: "dpo", writes: ["report"] });
});

describe("Analytics tabs", () => {
  it("gives management the scorecard, analytics, the record and reports, with an office", async () => {
    serve(MANAGEMENT);
    render(<AnalyticsPage />);
    await screen.findByRole("tablist", { name: "Analytics" });
    expect(tabNames()).toEqual([
      "Management",
      "Analytics",
      "Record of processing",
      "Reports",
    ]);
    const office = screen.getByLabelText("Office");
    expect(
      within(office)
        .getAllByRole("option")
        .map((o) => o.textContent),
    ).toEqual(["All offices", "R&D (DPO office)", "HR (Legal office)"]);
    // A breakdown is chosen on a figure's own page and on each chart
    // (2026-11-24), not in the toolbar.
    expect(screen.queryByLabelText("Breakdown")).not.toBeInTheDocument();
  });

  it("gives the administrator audit, health, quality, reports and settings, and no office", async () => {
    me = makeMe({ role: "admin", writes: ["analytics_setting", "report"] });
    serve(ADMIN);
    server.use(
      http.get(`${API}/analytics/catalogue`, () =>
        HttpResponse.json({
          ...ADMIN,
          audit_reports: [
            {
              key: "privileged",
              title: "Privileged actions",
              description: "Accounts made.",
            },
          ],
        }),
      ),
    );
    render(<AnalyticsPage />);
    await screen.findByRole("tablist", { name: "Analytics" });
    expect(tabNames()).toEqual([
      "Audit reports",
      "Health",
      "Data quality",
      "Reports",
      "Settings",
    ]);
    expect(screen.queryByLabelText("Office")).not.toBeInTheDocument();
  });

  it("gives an R&D user their own work and reports, without the office or its breakdown", async () => {
    me = makeMe({ role: "rnd_user", writes: ["report"] });
    serve(RND);
    render(<AnalyticsPage />);
    await screen.findByRole("tablist", { name: "Analytics" });
    expect(tabNames()).toEqual(["Your work", "Reports"]);
    expect(screen.queryByLabelText("Office")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Breakdown")).not.toBeInTheDocument();
  });
});

describe("figures", () => {
  it("shows a withheld figure as fewer than the threshold, never as nought", async () => {
    serve(MANAGEMENT, [
      figure({
        key: "erasures",
        title: "People erased",
        unit: "count",
        kind: "count",
        value: null,
        suppressed: true,
        previous: null,
        previous_suppressed: true,
        change: null,
        target: null,
        amber: null,
        status: null,
        series: [],
      }),
    ]);
    render(<AnalyticsPage />);
    const tile = (await screen.findByRole("heading", { name: "People erased" })).closest(
      "a",
    ) as HTMLElement;
    expect(within(tile).getAllByText("< 5").length).toBeGreaterThan(0);
    expect(within(tile).getByText("Too few to show")).toBeInTheDocument();
    expect(within(tile).queryByText("0")).not.toBeInTheDocument();
  });

  it("reads each status in words, with the target and the change", async () => {
    serve(MANAGEMENT, [
      figure(),
      figure({ key: "a", title: "Breaches reported in time", status: "green", value: 100 }),
      figure({ key: "b", title: "Erasures confirmed", status: "red", value: 40 }),
    ]);
    render(<AnalyticsPage />);
    const tile = (
      await screen.findByRole("heading", { name: "Requests answered on time" })
    ).closest("a") as HTMLElement;
    expect(within(tile).getByText("Watch")).toBeInTheDocument();
    expect(within(tile).getByText("92.5%")).toBeInTheDocument();
    expect(within(tile).getByText("+4.5 points")).toBeInTheDocument();
    expect(within(tile).getByText(/at least 95%/)).toBeInTheDocument();
    expect(screen.getAllByText("On target").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Off target").length).toBeGreaterThan(0);
  });

  it("opens a figure's own page from its tile, with the period it was read under", async () => {
    window.history.replaceState(null, "", "/analytics?period=this_quarter");
    serve(MANAGEMENT, [figure()]);
    render(<AnalyticsPage />);
    const tile = (
      await screen.findByRole("heading", { name: "Requests answered on time" })
    ).closest("a") as HTMLElement;
    const href = tile.getAttribute("href") ?? "";
    expect(href.startsWith("/analytics/figure/rights_on_time?")).toBe(true);
    expect(href).toContain("period=this_quarter");
    expect(href).toContain("from=management");
    // Named for what it opens, once: the figure, its value and its status.
    expect(tile).toHaveAccessibleName(/Requests answered on time, 92\.5%, Watch/);
  });

  it("puts the figures off target first, worst first, each a link to its page", async () => {
    serve(MANAGEMENT, [
      figure({ key: "a", title: "Watched figure", status: "amber" }),
      figure({ key: "b", title: "Missed figure", status: "red", value: 40 }),
      figure({ key: "c", title: "Fine figure", status: "green", value: 99 }),
    ]);
    render(<AnalyticsPage />);
    const strip = await screen.findByRole("region", { name: /Needs attention/ });
    const links = within(strip).getAllByRole("link");
    expect(links.map((l) => l.textContent)).toEqual([
      expect.stringContaining("Missed figure"),
      expect.stringContaining("Watched figure"),
    ]);
    expect(links[0].getAttribute("href")).toContain("/analytics/figure/b?");
  });

  it("asks for the office management chooses", async () => {
    serve(MANAGEMENT);
    const asked: URLSearchParams[] = [];
    server.use(
      http.get(`${API}/analytics/figures`, ({ request }) => {
        asked.push(new URL(request.url).searchParams);
        return HttpResponse.json(figures([figure()]));
      }),
    );
    const { user } = render(<AnalyticsPage />);
    await user.selectOptions(await screen.findByLabelText("Office"), "hr");
    await waitFor(() => expect(asked.at(-1)?.get("office")).toBe("hr"));
    expect(asked.at(-1)?.get("section")).toBe("management");
  });
});

describe("reports", () => {
  it("lists reports and deletes one only once confirmed", async () => {
    serve(MANAGEMENT);
    let deleted: string | null = null;
    server.use(
      http.get(`${API}/reports`, () =>
        HttpResponse.json([
          report(),
          report({
            report_uuid: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
            title: "Board pack, October 2026",
            status: "failed",
            error: "The record could not be read.",
            file_bytes: null,
          }),
        ]),
      ),
      http.delete(`${API}/reports/:uuid`, ({ params }) => {
        deleted = String(params.uuid);
        return HttpResponse.json({ ok: true, message: "Deleted" });
      }),
    );
    window.history.replaceState(null, "", "/analytics?tab=reports");
    const { user } = render(<AnalyticsPage />);

    const table = await screen.findByRole("table", { name: "Reports" });
    expect(
      within(table).getByText("Management scorecard, October 2026"),
    ).toBeInTheDocument();
    expect(within(table).getByText("Ready")).toBeInTheDocument();
    expect(within(table).getByText("Failed")).toBeInTheDocument();
    expect(within(table).getByText("The record could not be read.")).toBeInTheDocument();
    expect(within(table).getByText("20.0 KB")).toBeInTheDocument();
    expect(
      within(table).getByRole("button", {
        name: "Download Management scorecard, October 2026",
      }),
    ).toBeInTheDocument();

    await user.click(
      within(table).getByRole("button", {
        name: "Delete Management scorecard, October 2026",
      }),
    );
    const dialog = await screen.findByRole("dialog", { name: "Delete this report?" });
    expect(deleted).toBeNull();
    await user.click(within(dialog).getByRole("button", { name: "Delete report" }));
    await waitFor(() => expect(deleted).toBe("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"));
  });

  it("asks for a new report with what was chosen", async () => {
    serve(MANAGEMENT);
    let body: unknown = null;
    server.use(
      http.post(`${API}/reports`, async ({ request }) => {
        body = await request.json();
        return HttpResponse.json(report({ status: "queued", file_bytes: null }), {
          status: 202,
        });
      }),
    );
    window.history.replaceState(null, "", "/analytics?tab=reports");
    const { user } = render(<AnalyticsPage />);

    await user.click(await screen.findByRole("button", { name: "New report" }));
    const form = screen.getByRole("form", { name: "New report" });
    await user.selectOptions(within(form).getByLabelText("Format"), "xlsx");
    await user.selectOptions(within(form).getByLabelText("Period"), "this_fy");
    await user.selectOptions(within(form).getByLabelText("Office"), "rnd");
    await user.click(within(form).getByRole("button", { name: "Make report" }));

    await waitFor(() =>
      expect(body).toEqual({
        kind: "management_scorecard",
        format: "xlsx",
        period: "this_fy",
        office: "rnd",
      }),
    );
  });

  it("sets up a schedule, mailed to the roles chosen by their titles", async () => {
    serve(MANAGEMENT);
    let body: unknown = null;
    server.use(
      http.post(`${API}/reports/schedules`, async ({ request }) => {
        body = await request.json();
        const made: ReportSchedule = {
          schedule_uuid: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
          kind: "management_scorecard",
          title: "Management scorecard",
          params: {},
          format: "pdf",
          cadence: "weekly",
          recipient_roles: ["dpo"],
          office: null,
          active: true,
          created_by_name: "Meera Nair",
          created_role: "management",
          created_at: "2026-11-02T09:00:00Z",
          last_run_at: null,
          next_run_at: "2026-11-09T02:00:00Z",
        };
        return HttpResponse.json(made, { status: 201 });
      }),
    );
    window.history.replaceState(null, "", "/analytics?tab=reports");
    const { user } = render(<AnalyticsPage />);

    await user.click(await screen.findByRole("button", { name: "New schedule" }));
    const form = screen.getByRole("form", { name: "New schedule" });
    // Only the kinds that may be scheduled are offered.
    expect(
      within(form).queryByRole("option", { name: "Evidence pack" }),
    ).not.toBeInTheDocument();
    await user.selectOptions(within(form).getByLabelText("How often"), "weekly");
    await user.click(within(form).getByRole("checkbox", { name: "DPO" }));
    await user.click(within(form).getByRole("checkbox", { name: "Management" }));
    await user.click(within(form).getByRole("button", { name: "Set up schedule" }));

    await waitFor(() =>
      expect(body).toEqual({
        kind: "management_scorecard",
        format: "pdf",
        cadence: "weekly",
        recipient_roles: ["dpo", "management"],
      }),
    );
  });
});

describe("settings", () => {
  it("saves a target and its amber line", async () => {
    me = makeMe({ role: "admin", writes: ["analytics_setting", "report"] });
    serve(ADMIN);
    const settings: AnalyticsSettings = {
      small_number_threshold: 5,
      updated_at: null,
      updated_by_name: null,
      targets: [
        {
          key: "rights_on_time",
          title: "Requests answered on time",
          unit: "percent",
          section: "management",
          group: "Rights requests",
          higher_is_better: true,
          default_target: 95,
          default_amber: 85,
          target: 95,
          amber: 85,
          customised: false,
          updated_at: null,
          updated_by_name: null,
        },
      ],
    };
    let put: { key: string; body: unknown } | null = null;
    server.use(
      http.get(`${API}/analytics/settings`, () => HttpResponse.json(settings)),
      http.put(`${API}/analytics/targets/:key`, async ({ params, request }) => {
        put = { key: String(params.key), body: await request.json() };
        return HttpResponse.json(settings);
      }),
    );
    window.history.replaceState(null, "", "/analytics?tab=settings");
    const { user } = render(<AnalyticsPage />);

    expect(await screen.findByText(/1 withholds nothing/)).toBeInTheDocument();
    await user.click(
      await screen.findByRole("button", {
        name: "Edit the target of Requests answered on time",
      }),
    );
    const form = screen.getByRole("form", { name: "Target of Requests answered on time" });
    const target = within(form).getByLabelText(/^Target/);
    await user.clear(target);
    await user.type(target, "90");
    const amber = within(form).getByLabelText(/^Amber line/);
    await user.clear(amber);
    await user.type(amber, "80");
    await user.click(within(form).getByRole("button", { name: "Save" }));

    await waitFor(() =>
      expect(put).toEqual({ key: "rights_on_time", body: { target: 90, amber: 80 } }),
    );
  });
});
