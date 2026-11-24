/**
 * A figure's own page (2026-11-24): what a tile opens.
 */
import { HttpResponse, http } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import FigurePage from "@/app/(app)/analytics/figure/[key]/page";
import { makeMe } from "@/test/fixtures";
import { render, screen, within } from "@/test/render";
import { API, server } from "@/test/server";
import type { Catalogue, Figure, Figures, Me } from "@/types";

const route = { key: "rights.on_time_rate" };
vi.mock("next/navigation", () => ({
  useParams: () => route,
  useSearchParams: () => new URLSearchParams(window.location.search),
  usePathname: () => window.location.pathname,
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
}));

let me: Me | null = null;
vi.mock("@/providers", () => ({
  useAuth: () => ({ me }),
  useOptionalAuth: () => ({ me }),
  useToast: () => ({ success: vi.fn(), error: vi.fn(), warning: vi.fn() }),
}));

const RATE = {
  key: "rights.on_time_rate",
  title: "Closed on time",
  definition: "Of the requests closed in the period, the share closed by the date due.",
  unit: "percent",
  section: "management",
  group: "Rights requests",
  kind: "ratio",
  dims: ["office", "type"],
  people: false,
  numerator: "rights.closed_on_time",
  denominator: "rights.closed",
  higher_is_better: true,
};

const CATALOGUE: Catalogue = {
  role: "management",
  office: null,
  may_choose_office: true,
  sections: ["management", "reports"],
  metrics: [RATE],
  dimensions: [
    { key: "office", label: "Office" },
    { key: "type", label: "Request type" },
  ],
  periods: [
    { key: "this_quarter", label: "This quarter" },
    { key: "this_month", label: "This month" },
  ],
  cadences: [],
  reports: [],
  audit_reports: [],
};

function fig(over: Partial<Figure>): Figure {
  return {
    ...RATE,
    value: 92.4,
    suppressed: false,
    previous: 94.1,
    previous_suppressed: false,
    change: -1.7,
    target: 95,
    amber: 90,
    higher_is_better: true,
    status: "amber",
    series: [
      { bucket: "2026-10-01", value: 92.9, suppressed: false },
      { bucket: "2026-11-01", value: 92.4, suppressed: false },
    ],
    breakdown: [],
    ...over,
  };
}

function count(
  key: string,
  title: string,
  value: number,
  parts: Figure["breakdown"] = [],
): Figure {
  return fig({
    key,
    title,
    unit: "count",
    kind: "count",
    value,
    numerator: null,
    denominator: null,
    target: null,
    amber: null,
    status: null,
    breakdown: parts,
  });
}

function answer(dim: string | null): Figures {
  const period = {
    preset: "this_quarter",
    start: "2026-10-01T00:00:00+05:30",
    end: "2027-01-01T00:00:00+05:30",
    label: "Q3 FY 2026-27",
    start_date: "2026-10-01",
    end_date: "2026-12-31",
  };
  const split = dim === "office";
  return {
    period,
    previous: { ...period, label: "Q2 FY 2026-27" },
    office: null,
    dim,
    grain: "month",
    threshold: 5,
    metrics: [
      fig({
        breakdown: split
          ? [
              { key: "rnd", label: "DPO office", value: 91.8, suppressed: false },
              { key: "hr", label: "Legal office", value: null, suppressed: true },
            ]
          : [],
      }),
      count(
        "rights.closed_on_time",
        "Requests closed on time",
        292,
        split ? [{ key: "rnd", label: "DPO office", value: 280, suppressed: false }] : [],
      ),
      count(
        "rights.closed",
        "Requests closed",
        316,
        split ? [{ key: "rnd", label: "DPO office", value: 305, suppressed: false }] : [],
      ),
    ],
  };
}

beforeEach(() => {
  route.key = "rights.on_time_rate";
  window.history.replaceState(
    null,
    "",
    "/analytics/figure/rights.on_time_rate?period=this_quarter&from=management",
  );
  me = makeMe({ role: "management", nav: ["analytics", "tickets"], writes: [] });
  server.use(
    http.get(`${API}/analytics/catalogue`, () => HttpResponse.json(CATALOGUE)),
    http.get(`${API}/analytics/figures`, ({ request }) =>
      HttpResponse.json(answer(new URL(request.url).searchParams.get("dim"))),
    ),
  );
});

describe("a figure's page", () => {
  it("leads with the value, its status, the two counts and the target", async () => {
    render(<FigurePage />);
    expect(await screen.findByText("92.4%")).toBeInTheDocument();
    expect(screen.getByText("Requests closed on time")).toBeInTheDocument();
    expect(screen.getByText("292")).toBeInTheDocument();
    expect(screen.getByText("316")).toBeInTheDocument();
    expect(screen.getAllByText("Watch").length).toBeGreaterThan(0);
    expect(screen.getByText(/−1\.7 points worse than Q2 FY 2026-27/)).toBeInTheDocument();
    // Back to the tab it came from, with the same period.
    expect(screen.getByRole("link", { name: /Back to the overview/ })).toHaveAttribute(
      "href",
      "/analytics?period=this_quarter&tab=management",
    );
  });

  it("splits by office for management, a withheld part as fewer than the threshold", async () => {
    render(<FigurePage />);
    const split = await screen.findByRole("group", { name: "Break down by" });
    expect(within(split).getByRole("button", { name: "Office" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    const list = await screen.findByRole("list", { name: /Closed on time by office/ });
    expect(within(list).getByText("DPO office")).toBeInTheDocument();
    expect(within(list).getByText("280 of 305")).toBeInTheDocument();
    expect(within(list).getByText("< 5")).toBeInTheDocument();
  });

  it("offers no register to a role the server did not give one", async () => {
    render(<FigurePage />);
    await screen.findByText("92.4%");
    expect(
      screen.queryByRole("link", { name: /Open Rights requests/ }),
    ).not.toBeInTheDocument();
  });

  it("offers the register to an officer who has it", async () => {
    me = makeMe({ role: "dpo", nav: ["analytics", "requests"], writes: [] });
    render(<FigurePage />);
    expect(
      await screen.findByRole("link", { name: /Open Rights requests/ }),
    ).toHaveAttribute("href", "/requests");
  });

  it("says plainly when the figure is not the reader's", async () => {
    route.key = "breach.incidents";
    render(<FigurePage />);
    expect(
      await screen.findByText("This figure is not one your role reads"),
    ).toBeInTheDocument();
  });
});
