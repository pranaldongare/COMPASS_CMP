/**
 * Reports from the public link (0058, ADR 0037): nothing while nothing waits;
 * either office can read one; claiming logs it and goes to it; dismissing keeps
 * it, and asks why first, and what was dismissed can be read from the register
 * whether or not anything waits. A report taken up while it is open here goes,
 * and says so. What a stranger says about a cyber attack is shown as their
 * word, not as the register's "reportable".
 *
 * The list is a page of short rows and the total. A report's full text is read
 * when somebody presses Open report, and a report can be claimed or dismissed from
 * its row whether or not the rest of it could be read.
 */
import { HttpResponse, http } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import BreachesPage from "@/app/(app)/breaches/page";
import { DismissedReportsButton, IntakeCard } from "@/features/breach/components/intake-card";
import { keys } from "@/lib/query";
import { act, render, screen, within } from "@/test/render";
import { API, server } from "@/test/server";
import type { DismissedReport, IncidentReport, IncidentReportPage, IncidentReportRow } from "@/types";

/** A claim cannot be given back, so it is asked about first (2026-11-12): the
 *  pop-up says the other office stops seeing the report. This says yes. */
async function yesClaim(user: ReturnType<typeof render>["user"]) {
  const question = await screen.findByRole("dialog", { name: "Claim this report for your office?" });
  expect(within(question).getByText(/the other office no longer sees it\. A claim cannot be undone\./)).toBeInTheDocument();
  await user.click(within(question).getByRole("button", { name: "Claim for this office" }));
}

const push = vi.hoisted(() => vi.fn());
const toast = vi.hoisted(() => ({ success: vi.fn(), error: vi.fn(), warning: vi.fn() }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace: vi.fn(), back: vi.fn(), refresh: vi.fn() }),
  useSearchParams: () => new URLSearchParams(window.location.search),
  usePathname: () => window.location.pathname,
}));
vi.mock("@/providers", () => ({ useToast: () => toast }));

const REPORT = "99999999-9999-4999-8999-999999999999";
const BREACH = "66666666-6666-4666-8666-666666666666";

const report = (over: Partial<IncidentReport> = {}): IncidentReport => ({
  report_uuid: REPORT,
  reference: "INC-2026-0042",
  reporter_name: "Asha Rao",
  reporter_email: "asha@example.org",
  title: "A file on a public share",
  noticed_at: null,
  received_at: "2026-11-06T09:00:00Z",
  cyber_attack: "yes",
  logged: { incident_details: "The participant list was open to anyone with the link" },
  ...over,
});

const short = ({ logged: _, ...row }: IncidentReport): IncidentReportRow => row;

const page = (rows: IncidentReport[], over: Partial<IncidentReportPage> = {}): IncidentReportPage => ({
  items: rows.map(short),
  total: rows.length,
  limit: 50,
  offset: 0,
  ...over,
});

const GONE = { error: { code: "already_claimed", message: "The other office has already claimed it" } };
const DOWN = { error: { code: "unavailable", message: "Down for a moment" } };

/** The intake as it stands: the list, and each report in full until it is taken up. */
function serve(rows: IncidentReport[]) {
  const world = { rows };
  server.use(
    http.get(`${API}/breaches/intake`, () => HttpResponse.json(page(world.rows))),
    http.get(`${API}/breaches/intake/:uuid`, ({ params }) => {
      const found = world.rows.find((r) => r.report_uuid === params.uuid);
      return found ? HttpResponse.json(found) : HttpResponse.json(GONE, { status: 409 });
    }),
  );
  return world;
}

async function openIt(user: ReturnType<typeof render>["user"]) {
  await user.click(await screen.findByRole("button", { name: "Open report" }));
  return screen.findByRole("dialog");
}

/** Reads that have just come back. */
async function polled(queryClient: ReturnType<typeof render>["queryClient"]) {
  await act(async () => {
    await queryClient.refetchQueries({ queryKey: keys.breach.intake() });
    // The query tells the screen on the next turn of the loop.
    await new Promise((resolve) => setTimeout(resolve, 10));
  });
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("IntakeCard", () => {
  it("shows nothing while nothing waits", async () => {
    let asked = false;
    server.use(
      http.get(`${API}/breaches/intake`, () => {
        asked = true;
        return HttpResponse.json(page([]));
      }),
    );
    const { container } = render(<IntakeCard />);

    await vi.waitFor(() => expect(asked).toBe(true));
    expect(screen.queryByTestId("incident-intake")).not.toBeInTheDocument();
    expect(container).toBeEmptyDOMElement();
  });

  it("lists what waits, and shows who reported it and what they said", async () => {
    serve([report()]);
    const { user } = render(<IntakeCard />);

    const card = await screen.findByTestId("incident-intake");
    expect(within(card).getByText("A file on a public share")).toBeInTheDocument();
    expect(within(card).getByText("INC-2026-0042")).toBeInTheDocument();

    const dialog = await openIt(user);
    expect(within(dialog).getByText("asha@example.org")).toBeInTheDocument();
    expect(within(dialog).getByText("Not said")).toBeInTheDocument();
    expect(await within(dialog).findByText("The participant list was open to anyone with the link")).toBeInTheDocument();
    // Their word, not the register's: it has started nothing.
    expect(within(dialog).getByText("They say it was")).toBeInTheDocument();
    expect(within(dialog).queryByText(/reportable to CERT-In/)).not.toBeInTheDocument();
  });

  it("does not read a report's full text until somebody presses Open report", async () => {
    let asked = 0;
    serve([report()]);
    server.use(
      http.get(`${API}/breaches/intake/${REPORT}`, () => {
        asked += 1;
        return HttpResponse.json(report());
      }),
    );
    const { user } = render(<IntakeCard />);

    await screen.findByTestId("incident-intake");
    expect(asked).toBe(0);

    const dialog = await openIt(user);
    expect(await within(dialog).findByText(/open to anyone with the link/)).toBeInTheDocument();
    expect(asked).toBe(1);
  });

  it("shows the row at once and says it is reading the rest, which can be claimed meanwhile", async () => {
    let claimed = false;
    serve([report()]);
    let release = () => {};
    const held = new Promise<void>((resolve) => {
      release = resolve;
    });
    server.use(
      http.get(`${API}/breaches/intake/${REPORT}`, async () => {
        await held;
        return HttpResponse.json(report());
      }),
      http.post(`${API}/breaches/intake/${REPORT}/claim`, () => {
        claimed = true;
        return HttpResponse.json({ breach_uuid: BREACH, reference: "INC-2026-0042" });
      }),
    );
    const { user } = render(<IntakeCard />);

    const dialog = await openIt(user);
    expect(within(dialog).getByText("A file on a public share")).toBeInTheDocument();
    expect(within(dialog).getByRole("status", { name: "Reading the report" })).toBeInTheDocument();

    await user.click(within(dialog).getByRole("button", { name: "Claim for this office" }));
    await yesClaim(user);
    await vi.waitFor(() => expect(claimed).toBe(true));
    release();
  });

  it("says when the rest cannot be read, reads it again on asking, and leaves Dismiss working", async () => {
    let sent: unknown = null;
    serve([report()]);
    server.use(
      http.get(`${API}/breaches/intake/${REPORT}`, () => HttpResponse.json(DOWN, { status: 503 })),
      http.post(`${API}/breaches/intake/${REPORT}/dismiss`, async ({ request }) => {
        sent = await request.json();
        return HttpResponse.json({ message: "Dismissed" });
      }),
    );
    const { user } = render(<IntakeCard />);

    const dialog = await openIt(user);
    expect(await within(dialog).findByText("The rest of this report could not be read")).toBeInTheDocument();
    expect(within(dialog).getByText(/Something went wrong at our end/)).toBeInTheDocument();
    // What the row knows is still there.
    expect(within(dialog).getByText("asha@example.org")).toBeInTheDocument();

    server.use(http.get(`${API}/breaches/intake/${REPORT}`, () => HttpResponse.json(report())));
    await user.click(within(dialog).getByRole("button", { name: "Retry" }));
    expect(await within(dialog).findByText(/open to anyone with the link/)).toBeInTheDocument();
    expect(within(dialog).queryByText("The rest of this report could not be read")).not.toBeInTheDocument();

    await user.click(within(dialog).getByRole("button", { name: "Dismiss" }));
    await user.type(within(dialog).getByLabelText(/reason for dismissal/i), "A drill");
    await user.click(within(dialog).getByRole("button", { name: "Dismiss the report" }));
    await vi.waitFor(() => expect(sent).toEqual({ reason: "A drill" }));
  });

  it("leaves what was read on the screen when a later read fails", async () => {
    serve([report()]);
    const { user, queryClient } = render(<IntakeCard />);

    const dialog = await openIt(user);
    await within(dialog).findByText(/open to anyone with the link/);

    server.use(http.get(`${API}/breaches/intake/${REPORT}`, () => HttpResponse.json(DOWN, { status: 503 })));
    await polled(queryClient);

    expect(queryClient.getQueryState(keys.breach.intakeReport(REPORT))?.status).toBe("error");
    expect(within(dialog).getByText(/open to anyone with the link/)).toBeInTheDocument();
    expect(within(dialog).queryByText("The rest of this report could not be read")).not.toBeInTheDocument();
    expect(toast.warning).not.toHaveBeenCalled();
  });

  it("claims it for this office and goes to the incident", async () => {
    let claimed = false;
    serve([report()]);
    server.use(
      http.post(`${API}/breaches/intake/${REPORT}/claim`, () => {
        claimed = true;
        return HttpResponse.json({ breach_uuid: BREACH, reference: "INC-2026-0042" });
      }),
    );
    const { user } = render(<IntakeCard />);

    const dialog = await openIt(user);
    await user.click(within(dialog).getByRole("button", { name: "Claim for this office" }));
    await yesClaim(user);

    await vi.waitFor(() => expect(push).toHaveBeenCalledWith(`/breaches/${BREACH}`));
    expect(claimed).toBe(true);
    expect(toast.success).toHaveBeenCalledWith("INC-2026-0042 is yours", expect.any(String));
  });

  it("says when the other office got there first", async () => {
    serve([report()]);
    server.use(
      http.post(`${API}/breaches/intake/${REPORT}/claim`, () => HttpResponse.json(GONE, { status: 409 })),
    );
    const { user } = render(<IntakeCard />);

    const dialog = await openIt(user);
    await user.click(within(dialog).getByRole("button", { name: "Claim for this office" }));
    await yesClaim(user);

    await vi.waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith("Not claimed", "The other office has already claimed it"),
    );
    expect(push).not.toHaveBeenCalled();
  });

  it("will not dismiss a report without a reason", async () => {
    let sent: unknown = null;
    serve([report()]);
    server.use(
      http.post(`${API}/breaches/intake/${REPORT}/dismiss`, async ({ request }) => {
        sent = await request.json();
        return HttpResponse.json({ message: "Dismissed" });
      }),
    );
    const { user } = render(<IntakeCard />);

    const dialog = await openIt(user);
    await user.click(within(dialog).getByRole("button", { name: "Dismiss" }));
    const go = within(dialog).getByRole("button", { name: "Dismiss the report" });
    expect(go).toBeDisabled();
    await user.type(within(dialog).getByLabelText(/reason for dismissal/i), "   ");
    expect(go).toBeDisabled();
    await user.type(within(dialog).getByLabelText(/reason for dismissal/i), "A test by the helpdesk");
    await user.click(go);

    await vi.waitFor(() => expect(sent).toEqual({ reason: "A test by the helpdesk" }));
    await vi.waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(toast.success).toHaveBeenCalledWith("Report dismissed", expect.any(String));
  });

  it("does not claim anybody else took a report this office claimed", async () => {
    const world = serve([report()]);
    server.use(
      http.post(`${API}/breaches/intake/${REPORT}/claim`, () => {
        world.rows = [];
        return HttpResponse.json({ breach_uuid: BREACH, reference: "INC-2026-0042" });
      }),
    );
    const { user, queryClient } = render(<IntakeCard />);

    const dialog = await openIt(user);
    await user.click(within(dialog).getByRole("button", { name: "Claim for this office" }));
    await yesClaim(user);
    await vi.waitFor(() => expect(push).toHaveBeenCalled());
    await polled(queryClient);

    expect(toast.warning).not.toHaveBeenCalled();
  });

  it("does not take its own claim for somebody else's, whichever comes back first", async () => {
    const world = serve([report()]);
    let release = () => {};
    const held = new Promise<void>((resolve) => {
      release = resolve;
    });
    server.use(
      http.post(`${API}/breaches/intake/${REPORT}/claim`, async () => {
        world.rows = [];
        await held;
        return HttpResponse.json({ breach_uuid: BREACH, reference: "INC-2026-0042" });
      }),
    );
    const { user, queryClient } = render(<IntakeCard />);

    const dialog = await openIt(user);
    await within(dialog).findByText(/open to anyone with the link/);
    await user.click(within(dialog).getByRole("button", { name: "Claim for this office" }));
    await yesClaim(user);
    await vi.waitFor(() => expect(world.rows).toEqual([]));
    await polled(queryClient);
    expect(toast.warning).not.toHaveBeenCalled();

    release();
    await vi.waitFor(() => expect(push).toHaveBeenCalled());
    expect(toast.warning).not.toHaveBeenCalled();
  });

  it("does not say it twice when a claim is refused because somebody got there first", async () => {
    const world = serve([report()]);
    server.use(
      http.post(`${API}/breaches/intake/${REPORT}/claim`, () => {
        world.rows = [];
        return HttpResponse.json(GONE, { status: 409 });
      }),
    );
    const { user, queryClient } = render(<IntakeCard />);

    const dialog = await openIt(user);
    await user.click(within(dialog).getByRole("button", { name: "Claim for this office" }));
    await yesClaim(user);
    await vi.waitFor(() => expect(toast.error).toHaveBeenCalled());
    await polled(queryClient);

    await vi.waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(toast.warning).not.toHaveBeenCalled();
  });

  it("clears an open report that an office took up, says so, and does not bring it back", async () => {
    const world = serve([report()]);
    const { user, queryClient } = render(<IntakeCard />);

    await openIt(user);
    world.rows = [];
    await polled(queryClient);

    await vi.waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(toast.warning).toHaveBeenCalledTimes(1);
    expect(toast.warning).toHaveBeenCalledWith("That report has been taken up", expect.any(String));

    // The next report to arrive is a row in the list, not a window on the screen.
    world.rows = [report({ report_uuid: crypto.randomUUID(), reference: "INC-2026-0043", title: "Another" })];
    await polled(queryClient);

    expect(await screen.findByText("Another")).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("says a report was taken up when it goes between the list and the press", async () => {
    serve([report()]);
    server.use(http.get(`${API}/breaches/intake/${REPORT}`, () => HttpResponse.json(GONE, { status: 409 })));
    const { user } = render(<IntakeCard />);

    await user.click(await screen.findByRole("button", { name: "Open report" }));

    await vi.waitFor(() => expect(toast.warning).toHaveBeenCalledTimes(1));
    await vi.waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });

  it("keeps a report open while it is still listed, among newer ones", async () => {
    const world = serve([report()]);
    const { user, queryClient } = render(<IntakeCard />);

    const dialog = await openIt(user);
    await user.click(within(dialog).getByRole("button", { name: "Dismiss" }));
    await user.type(within(dialog).getByLabelText(/reason for dismissal/i), "A reason");
    world.rows = [report(), report({ report_uuid: crypto.randomUUID(), reference: "INC-2026-0043" })];
    await polled(queryClient);

    expect(within(screen.getByRole("dialog")).getByLabelText(/reason for dismissal/i)).toHaveValue("A reason");
    expect(toast.warning).not.toHaveBeenCalled();
  });

  describe("past one page", () => {
    const rows = (from: number, count: number) =>
      Array.from({ length: count }, (_, i) =>
        report({
          report_uuid: crypto.randomUUID(),
          reference: `INC-2026-${String(from + i).padStart(4, "0")}`,
          title: `Report ${from + i}`,
        }),
      );
    const FIRST = rows(1, 50);
    const SECOND = rows(51, 50);
    const THIRD = rows(101, 20);

    /** The server's own paging, over however many reports wait. */
    function serveAll(all: IncidentReport[]) {
      const world = { all, seen: [] as string[] };
      server.use(
        http.get(`${API}/breaches/intake`, ({ request }) => {
          const url = new URL(request.url);
          world.seen.push(url.search);
          const limit = Number(url.searchParams.get("limit"));
          const offset = Number(url.searchParams.get("offset"));
          return HttpResponse.json(
            page(world.all.slice(offset, offset + limit), { total: world.all.length, limit, offset }),
          );
        }),
      );
      return world;
    }

    it("shows the total, not the page, and asks for one page at a time", async () => {
      const world = serveAll([...FIRST, ...SECOND, ...THIRD]);
      render(<IntakeCard />);

      expect(await screen.findByRole("heading", { name: /Reported through the public link \(120\)/ })).toBeInTheDocument();
      expect(screen.getAllByRole("button", { name: "Open report" })).toHaveLength(50);
      expect(screen.getByText("1 to 50 of 120")).toBeInTheDocument();
      expect(world.seen).toEqual(["?limit=50&offset=0"]);
    });

    it("steps through the pages and back", async () => {
      serveAll([...FIRST, ...SECOND, ...THIRD]);
      const { user } = render(<IntakeCard />);

      await screen.findByText("Report 1");
      expect(screen.getByRole("button", { name: "Previous" })).toBeDisabled();

      await user.click(screen.getByRole("button", { name: "Next" }));
      expect(await screen.findByText("Report 51")).toBeInTheDocument();
      expect(screen.queryByText("Report 1")).not.toBeInTheDocument();
      expect(screen.getByText("51 to 100 of 120")).toBeInTheDocument();

      await user.click(screen.getByRole("button", { name: "Next" }));
      expect(await screen.findByText("Report 101")).toBeInTheDocument();
      expect(screen.getByText("101 to 120 of 120")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();

      await user.click(screen.getByRole("button", { name: "Previous" }));
      expect(await screen.findByText("Report 51")).toBeInTheDocument();
    });

    it("offers no paging while everything fits on one page", async () => {
      serveAll(rows(1, 50));
      render(<IntakeCard />);

      await screen.findByText("Report 1");
      expect(screen.queryByRole("button", { name: "Next" })).not.toBeInTheDocument();
    });

    it("steps back when reports taken up leave the last page empty", async () => {
      const world = serveAll([...FIRST, ...SECOND, ...THIRD]);
      const { user, queryClient } = render(<IntakeCard />);

      await screen.findByText("Report 1");
      await user.click(screen.getByRole("button", { name: "Next" }));
      await screen.findByText("Report 51");
      await user.click(screen.getByRole("button", { name: "Next" }));
      await screen.findByText("Report 101");

      world.all = [...FIRST, ...SECOND];
      await polled(queryClient);

      expect(await screen.findByText("Report 51")).toBeInTheDocument();
      expect(screen.getByText("51 to 100 of 100")).toBeInTheDocument();
    });

    it("keeps a report open when it has only moved to another page", async () => {
      const world = serveAll([...FIRST, ...SECOND, ...THIRD]);
      const opened = SECOND[0];
      server.use(http.get(`${API}/breaches/intake/${opened.report_uuid}`, () => HttpResponse.json(opened)));
      const { user, queryClient } = render(<IntakeCard />);

      await screen.findByText("Report 1");
      await user.click(screen.getByRole("button", { name: "Next" }));
      const row = (await screen.findByText("Report 51")).closest("li") as HTMLElement;
      await user.click(within(row).getByRole("button", { name: "Open report" }));
      await screen.findByRole("dialog");

      // A report on the first page is taken up, so this one moves up onto it.
      world.all = [...FIRST.slice(1), ...SECOND, ...THIRD];
      await polled(queryClient);

      expect(screen.getByRole("dialog")).toBeInTheDocument();
      expect(toast.warning).not.toHaveBeenCalled();
    });
  });

  it("says when the list cannot be read", async () => {
    server.use(http.get(`${API}/breaches/intake`, () => HttpResponse.json(DOWN, { status: 503 })));
    render(<IntakeCard />);

    expect(await screen.findByText("Reports from the public link could not be read")).toBeInTheDocument();
    expect(screen.getByText(/Something went wrong at our end/)).toBeInTheDocument();
  });
});

describe("Dismissed reports", () => {
  const dismissed = (over: Partial<DismissedReport> = {}): DismissedReport => ({
    reference: "INC-2026-0041",
    reporter_name: "Asha Rao",
    reporter_email: "asha@example.org",
    title: "A test by the helpdesk",
    received_at: "2026-11-05T09:00:00Z",
    dismissed_at: "2026-11-05T12:00:00Z",
    dismissed_by_name: "Priya Menon",
    dismissal_reason: "It was a drill",
    reporter_erased_at: null,
    ...over,
  });

  it("is reachable from the register with nothing waiting, and shows who, when and why", async () => {
    serve([]);
    server.use(
      http.get(`${API}/breaches`, () => HttpResponse.json([])),
      http.get(`${API}/breaches/intake/dismissed`, () => HttpResponse.json([dismissed()])),
    );
    const { user } = render(<BreachesPage />);

    await user.click(await screen.findByRole("button", { name: "Dismissed reports" }));

    const dialog = await screen.findByRole("dialog");
    expect(await within(dialog).findByText("A test by the helpdesk")).toBeInTheDocument();
    expect(within(dialog).getByText("INC-2026-0041")).toBeInTheDocument();
    expect(within(dialog).getByText(/Asha Rao, asha@example\.org/)).toBeInTheDocument();
    expect(within(dialog).getByText(/^Dismissed .* by Priya Menon$/)).toBeInTheDocument();
    expect(within(dialog).getByText("“It was a drill”")).toBeInTheDocument();
  });

  it("says the reporter's name and email were erased at their request, and keeps the number, the reason and who dismissed it", async () => {
    server.use(
      http.get(`${API}/breaches/intake/dismissed`, () =>
        HttpResponse.json([
          dismissed({ reporter_name: null, reporter_email: null, reporter_erased_at: "2026-11-07T10:00:00Z" }),
        ]),
      ),
    );
    const { user } = render(<DismissedReportsButton />);

    await user.click(await screen.findByRole("button", { name: "Dismissed reports" }));

    const dialog = await screen.findByRole("dialog");
    expect(await within(dialog).findByText(/^Reporter's name and email erased .*, at their request$/)).toBeInTheDocument();
    expect(within(dialog).queryByText(/Reported by/)).not.toBeInTheDocument();
    // Never the request that erased them: both offices read this list.
    expect(within(dialog).queryByText(/RR-/)).not.toBeInTheDocument();
    expect(within(dialog).getByText("INC-2026-0041")).toBeInTheDocument();
    expect(within(dialog).getByText(/^Dismissed .* by Priya Menon$/)).toBeInTheDocument();
    expect(within(dialog).getByText("“It was a drill”")).toBeInTheDocument();
  });

  it("does not read them until they are asked for", async () => {
    let asked = false;
    server.use(
      http.get(`${API}/breaches/intake/dismissed`, () => {
        asked = true;
        return HttpResponse.json([]);
      }),
    );
    const { user } = render(<DismissedReportsButton />);

    const button = await screen.findByRole("button", { name: "Dismissed reports" });
    expect(asked).toBe(false);
    await user.click(button);

    expect(await screen.findByText("No report has been dismissed.")).toBeInTheDocument();
    expect(asked).toBe(true);
  });

  it("says when they cannot be read", async () => {
    server.use(
      http.get(`${API}/breaches/intake/dismissed`, () =>
        HttpResponse.json({ error: { code: "unavailable", message: "Down for a moment" } }, { status: 503 }),
      ),
    );
    const { user } = render(<DismissedReportsButton />);

    await user.click(await screen.findByRole("button", { name: "Dismissed reports" }));

    expect(await screen.findByText("Down for a moment")).toBeInTheDocument();
  });
});
