/**
 * Finding a breach's people in the words of the work (2026-11-06): a project
 * or activity, a vendor, a data source, an Excel list or one person, never a
 * database table. Whoever was found is read before anyone is added, and anyone
 * wrong can be unticked.
 */
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";

import { AffectedCard } from "@/features/breach/components/affected-card";
import { makeMe } from "@/test/fixtures";
import { render, screen, waitFor, within } from "@/test/render";
import { API, errorResponse, server } from "@/test/server";
import type { Breach, BreachAffected, BreachCandidate, BreachPreview } from "@/types";

const toast = vi.hoisted(() => ({ success: vi.fn(), error: vi.fn() }));
const nav = vi.hoisted(() => ({ current: ["breaches", "processors", "sources"] }));

vi.mock("@/providers", () => ({
  useAuth: () => ({ me: makeMe({ role: "dpo", nav: nav.current as never }) }),
  useToast: () => toast,
}));

const UUID = "44444444-4444-4444-8444-444444444444";
const PROJECT = "66666666-6666-4666-8666-666666666666";
const VENDOR = "77777777-7777-4777-8777-777777777777";
const ASHA = "11111111-1111-4111-8111-111111111111";
const RAVI = "22222222-2222-4222-8222-222222222222";
const MEERA = "33333333-3333-4333-8333-333333333333";

const breach = (over: Partial<Breach> = {}) =>
  ({
    breach_uuid: UUID,
    status: "open",
    location: { kind: "platform", processor_uuid: null, source_uuid: null },
    ...over,
  }) as Breach;

const EMPTY: BreachAffected = { total: 0, revisions: [], people: [], next_cursor: null };

const candidate = (person_uuid: string, full_name: string, already_listed = false): BreachCandidate => ({
  person_uuid,
  full_name,
  role: "data_subject",
  has_email: true,
  has_mobile: false,
  found_by: "project",
  evidence: { projects: [], exports: [], assets: [], tables: [] },
  already_listed,
});

function serve({
  affected = EMPTY,
  contacts = 0,
  projects = [] as unknown[],
}: { affected?: BreachAffected; contacts?: number; projects?: unknown[] } = {}) {
  server.use(
    http.get(`${API}/breaches/${UUID}/affected`, () => HttpResponse.json(affected)),
    http.get(`${API}/breaches/${UUID}/affected/contacts`, () =>
      HttpResponse.json({ total: contacts, contacts: [], next_cursor: null, uploads: [] }),
    ),
    http.get(`${API}/breaches/${UUID}/affected/options`, () => HttpResponse.json({ projects })),
  );
}

/** A preview to answer with, and what was sent to preview and to confirm. */
function look(preview: BreachPreview) {
  const sent: { preview?: unknown; confirm?: Record<string, unknown> } = {};
  server.use(
    http.post(`${API}/breaches/${UUID}/affected/preview`, async ({ request }) => {
      sent.preview = await request.json();
      return HttpResponse.json(preview);
    }),
    http.post(`${API}/breaches/${UUID}/affected`, async ({ request }) => {
      sent.confirm = (await request.json()) as Record<string, unknown>;
      return HttpResponse.json(
        {
          ...EMPTY,
          revisions: [
            {
              revision_uuid: ASHA,
              revision: 1,
              scopes: [],
              derived: preview.derived,
              added_by_hand: 0,
              excluded: 0,
              newly_listed: 2,
              note: null,
              confirmed_at: "2026-11-06T10:00:00Z",
              confirmed_by_name: "Priya Menon",
            },
          ],
        },
        { status: 201 },
      );
    }),
  );
  return sent;
}

const GAIT = { project_uuid: PROJECT, project_name: "Gait Study", is_activity: false, people: 3 };

async function open(user: ReturnType<typeof render>["user"]) {
  await user.click(await screen.findByRole("button", { name: "Add people" }));
  return screen.findByRole("dialog");
}

describe("AffectedCard", () => {
  it("lists the people in plain words, tables never named", async () => {
    const at = "2026-11-02T10:00:00Z";
    const row = (revision: number, uuid: string, scopes: Record<string, unknown>[], over = {}) => ({
      revision_uuid: uuid,
      revision,
      scopes,
      derived: 3,
      added_by_hand: 0,
      excluded: 0,
      newly_listed: 3,
      note: null,
      confirmed_at: at,
      confirmed_by_name: "Priya Menon",
      ...over,
    });
    serve({
      contacts: 2,
      affected: {
        ...EMPTY,
        total: 3,
        people: [
          {
            ...candidate(ASHA, "Asha Rao"),
            affected_uuid: ASHA,
            revision: 1,
            found_by: "platform",
          },
          {
            ...candidate(RAVI, "Ravi Kumar"),
            affected_uuid: RAVI,
            revision: 2,
            found_by: "processor",
            has_mobile: true,
          },
        ],
        revisions: [
          row(1, ASHA, [{ kind: "platform", tables: ["auth_user", "consent_artefact"] }]),
          row(2, RAVI, [{ kind: "processor", processor_name: "Acme Labs" }], { excluded: 1 }),
          row(3, MEERA, [{ kind: "project", project_name: "Gait Study", since: at, until: at }]),
          row(4, PROJECT, [{ kind: "upload", file: "contacts" }], { newly_listed: 1 }),
          row(5, VENDOR, [], { newly_listed: 1, note: "Named by the vendor" }),
        ],
      },
    });
    render(<AffectedCard breach={breach()} />);

    expect(await screen.findByText("5 people")).toBeInTheDocument();
    expect(screen.getByText("Affected people")).toBeInTheDocument();
    const table = screen.getByRole("table");
    for (const heading of ["Person", "How found", "Reachable by", "Added"]) {
      expect(within(table).getByRole("columnheader", { name: heading })).toBeInTheDocument();
    }
    expect(within(table).getByText("From the platform's records")).toBeInTheDocument();
    expect(within(table).getByText("Sent to a vendor")).toBeInTheDocument();
    expect(within(table).getByText("email, SMS, their account")).toBeInTheDocument();
    expect(within(table).getAllByText("02 Nov 2026").length).toBeGreaterThan(0);

    expect(screen.getByText(/From the platform's records\. 3 people added\./)).toBeInTheDocument();
    expect(screen.getByText(/Sent to Acme Labs\. 3 people added, 1 left out\./)).toBeInTheDocument();
    expect(screen.getByText(/From Gait Study, consent given 02 Nov 2026 to 02 Nov 2026\./)).toBeInTheDocument();
    expect(screen.getByText(/From a list of people\. 1 person on the platform added\./)).toBeInTheDocument();
    expect(screen.getByText(/1 person added by hand\./)).toBeInTheDocument();
    expect(screen.getByText("Named by the vendor")).toBeInTheDocument();

    const words = document.body.textContent ?? "";
    expect(words).not.toMatch(/auth_user|consent_artefact|touched|revision|derive/i);
  });

  it("does not call a list of people with no account an empty list", async () => {
    serve({ contacts: 2 });
    render(<AffectedCard breach={breach()} />);
    expect(await screen.findByText("2 people")).toBeInTheDocument();
    expect(screen.queryByText("Nobody is listed yet.")).not.toBeInTheDocument();
  });

  it("offers nothing to add once the breach is closed", async () => {
    serve();
    render(<AffectedCard breach={breach({ status: "closed" })} />);
    expect(await screen.findByText("Nobody is listed yet.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Add people" })).not.toBeInTheDocument();
  });

  it("asks how, with the five ways, and leaves out sources for a role without them", async () => {
    serve();
    const first = render(<AffectedCard breach={breach()} />);
    const dialog = await open(first.user);
    expect(within(dialog).getByText("How do you want to add people?")).toBeInTheDocument();
    expect(
      within(dialog)
        .getAllByRole("button")
        .map((b) => b.textContent),
    ).toEqual(
      expect.arrayContaining([
        "From a project or activityEveryone who gave consent in it, including those who later withdrew. Optional: only between two dates.",
        "From a vendorEveryone whose data we sent to them.",
        "From a data sourceEveryone recorded in its files.",
        "Upload an Excel listName, Mail ID, Mobile number.",
        "Add one person",
      ]),
    );
    first.unmount();

    nav.current = ["breaches", "processors"];
    const second = render(<AffectedCard breach={breach()} />);
    const legal = await open(second.user);
    expect(within(legal).queryByRole("button", { name: /From a data source/ })).not.toBeInTheDocument();
    expect(within(legal).getByRole("button", { name: /From a vendor/ })).toBeInTheDocument();
    nav.current = ["breaches", "processors", "sources"];
  });

  it("finds a project's people, in whole days, and adds them less anyone unticked", async () => {
    serve({
      projects: [
        GAIT,
        { project_uuid: VENDOR, project_name: "Annual wellness", is_activity: true, people: 1 },
      ],
    });
    const sent = look({
      scopes: [{ kind: "project", project_uuid: PROJECT, project_name: "Gait Study" }],
      derived: 250,
      already_listed: 1,
      would_add: 249,
      people: [candidate(ASHA, "Asha Rao"), candidate(RAVI, "Ravi Kumar"), candidate(MEERA, "Meera Nair", true)],
    });
    const { user } = render(<AffectedCard breach={breach()} />);
    const dialog = await open(user);
    await user.click(within(dialog).getByRole("button", { name: /From a project or activity/ }));

    const choice = await within(dialog).findByLabelText(/^Project or activity/);
    expect(within(choice).getByRole("option", { name: "Gait Study · Project · 3 people" })).toBeInTheDocument();
    expect(within(choice).getByRole("option", { name: "Annual wellness · Activity · 1 person" })).toBeInTheDocument();
    const find = within(dialog).getByRole("button", { name: "Find the people" });
    expect(find).toBeDisabled();

    await user.selectOptions(choice, PROJECT);
    const from = within(dialog).getByLabelText("Consent given from");
    const until = within(dialog).getByLabelText("Consent given until");
    await user.type(until, "2026-10-01");
    await user.type(from, "2026-10-03");
    expect(within(dialog).getByText("This is before the first date")).toBeInTheDocument();
    expect(find).toBeDisabled();
    await user.clear(from);
    await user.type(from, "2026-09-28");
    await user.click(find);

    expect(await within(dialog).findByText("250 people found")).toBeInTheDocument();
    expect(within(dialog).getByText(/From Gait Study\. 1 already listed\./)).toBeInTheDocument();
    expect(within(dialog).getByText(/The first 3 of 250 are shown/)).toBeInTheDocument();
    expect(sent.preview).toEqual({
      scopes: [
        {
          kind: "project",
          project_uuid: PROJECT,
          since: new Date("2026-09-28T00:00").toISOString(),
          until: new Date("2026-10-01T23:59:59.999").toISOString(),
        },
      ],
    });

    const listed = within(dialog).getByRole("checkbox", { name: /Meera Nair/ });
    expect(listed).toBeChecked();
    expect(listed).toBeDisabled();
    await user.click(within(dialog).getByRole("checkbox", { name: "Ravi Kumar" }));
    await user.type(within(dialog).getByLabelText(/^Note/), "The October cohort");
    await user.click(within(dialog).getByRole("button", { name: "Add 248 people" }));

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(sent.confirm).toMatchObject({ exclude: [RAVI], add: [], note: "The October cohort" });
    expect((sent.confirm?.scopes as Record<string, unknown>[])[0]).toMatchObject({
      kind: "project",
      project_uuid: PROJECT,
    });
    expect(toast.success).toHaveBeenCalledWith(
      "2 people added to the list",
      "Next: draft and approve the notice below, then send it.",
    );
  });

  it("says so when no project has people, and points to the Excel list", async () => {
    serve({ projects: [] });
    const { user } = render(<AffectedCard breach={breach()} />);
    const dialog = await open(user);
    await user.click(within(dialog).getByRole("button", { name: /From a project or activity/ }));

    expect(await within(dialog).findByText("No project or activity has people in it yet")).toBeInTheDocument();
    await user.click(within(dialog).getByRole("button", { name: "Upload an Excel list" }));
    expect(await within(dialog).findByRole("button", { name: "Download the template" })).toBeInTheDocument();
  });

  it("starts from the vendor the incident happened at, and says when nobody is found", async () => {
    serve();
    server.use(
      http.get(`${API}/processors`, () =>
        HttpResponse.json({
          items: [{ processor_uuid: VENDOR, legal_name: "Acme Labs", contract_ref: "CTR-1" }],
          next_cursor: null,
          total: 1,
        }),
      ),
    );
    const sent = look({
      scopes: [{ kind: "processor", processor_uuid: VENDOR, processor_name: "Acme Labs" }],
      derived: 0,
      already_listed: 0,
      would_add: 0,
      people: [],
    });
    const { user } = render(
      <AffectedCard
        breach={breach({
          location: {
            kind: "processor",
            processor_uuid: VENDOR,
            processor_name: "Acme Labs",
            source_uuid: null,
            source_name: null,
            detail: null,
          },
        })}
      />,
    );
    const dialog = await open(user);
    await user.click(within(dialog).getByRole("button", { name: /From a vendor/ }));
    await user.click(within(dialog).getByRole("button", { name: "Find the people" }));

    expect(await within(dialog).findByText("0 people found")).toBeInTheDocument();
    expect(sent.preview).toEqual({ scopes: [{ kind: "processor", processor_uuid: VENDOR }] });
    expect(within(dialog).getByText(/Nobody is recorded here/)).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Add 0 people" })).toBeDisabled();

    await user.click(within(dialog).getByRole("button", { name: "Back" }));
    expect(within(dialog).getByRole("button", { name: "Find the people" })).toBeInTheDocument();
  });

  it("adds one person by search, with nothing looked up", async () => {
    serve();
    const sent = look({ scopes: [], derived: 0, already_listed: 0, would_add: 0, people: [] });
    server.use(
      http.get(`${API}/audit/lookup`, ({ request }) =>
        HttpResponse.json(
          new URL(request.url).searchParams.get("kind") === "data_subject"
            ? [
                {
                  kind: "data_subject",
                  entity_type: "user",
                  filter: "subject",
                  uuid: ASHA,
                  label: "Asha Rao",
                  hint: null,
                },
              ]
            : [],
        ),
      ),
    );
    const { user } = render(<AffectedCard breach={breach()} />);
    const dialog = await open(user);
    await user.click(within(dialog).getByRole("button", { name: "Add one person" }));

    const add = within(dialog).getByRole("button", { name: "Add this person" });
    expect(add).toBeDisabled();
    await user.type(within(dialog).getByLabelText(/^Find the person/), "asha");
    await user.click(within(dialog).getByRole("button", { name: "Find" }));
    await user.click(await within(dialog).findByRole("button", { name: "Add" }));
    await user.click(add);

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(sent.confirm).toEqual({ scopes: [], exclude: [], add: [ASHA], note: null });
  });

  it("says when a search finds nobody", async () => {
    serve();
    server.use(http.get(`${API}/audit/lookup`, () => HttpResponse.json([])));
    const { user } = render(<AffectedCard breach={breach()} />);
    const dialog = await open(user);
    await user.click(within(dialog).getByRole("button", { name: "Add one person" }));
    await user.type(within(dialog).getByLabelText(/^Find the person/), "nobody");
    await user.click(within(dialog).getByRole("button", { name: "Find" }));
    expect(await within(dialog).findByText(/Nobody found/)).toBeInTheDocument();
  });

  it("takes an Excel list as a step, with a way back", async () => {
    serve();
    const { user } = render(<AffectedCard breach={breach()} />);
    const dialog = await open(user);
    await user.click(within(dialog).getByRole("button", { name: /Upload an Excel list/ }));
    expect(within(dialog).getByRole("button", { name: "Download the template" })).toBeInTheDocument();

    await user.click(within(dialog).getByRole("button", { name: "Back" }));
    expect(within(dialog).getByText("How do you want to add people?")).toBeInTheDocument();
  });

  describe("Show more", () => {
    const person = (n: number) => ({
      affected_uuid: `55555555-5555-4555-8555-55555555555${n}`,
      full_name: `Person ${n}`,
      found_by: "project",
      has_email: true,
      has_mobile: false,
      revision: 1,
    });
    const page = (n: number, next_cursor: string | null) =>
      ({ total: 2, revisions: [], people: [person(n)], next_cursor }) as unknown as BreachAffected;

    function servePages(next: () => Response | Promise<Response>) {
      serve();
      server.use(
        http.get(`${API}/breaches/${UUID}/affected`, ({ request }) =>
          new URL(request.url).searchParams.get("cursor") ? next() : HttpResponse.json(page(1, "page-2")),
        ),
      );
    }

    it("says when the next page cannot be had, and lets it be asked for again", async () => {
      servePages(() => errorResponse("server_error", "Something failed", 500));
      const { user } = render(<AffectedCard breach={breach()} />);

      await user.click(await screen.findByRole("button", { name: "Show more" }));
      await waitFor(() =>
        expect(toast.error).toHaveBeenCalledWith("Could not load more", expect.any(String)),
      );
      expect(screen.getByRole("button", { name: "Show more" })).toBeEnabled();
    });

    it("asks once at a time, so a page is never listed twice", async () => {
      let asked = 0;
      let answer = () => {};
      servePages(async () => {
        asked += 1;
        await new Promise<void>((resolve) => {
          answer = resolve;
        });
        return HttpResponse.json(page(2, null));
      });
      const { user } = render(<AffectedCard breach={breach()} />);

      const more = await screen.findByRole("button", { name: "Show more" });
      await user.click(more);
      await waitFor(() => expect(more).toBeDisabled());
      await waitFor(() => expect(asked).toBe(1));
      answer();
      expect(await screen.findByText("Person 2")).toBeInTheDocument();
      expect(asked).toBe(1);
    });
  });
});
