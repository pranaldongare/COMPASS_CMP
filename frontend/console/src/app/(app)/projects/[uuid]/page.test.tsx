/**
 * The project page as one workspace (UX review 2026-10-05).
 *
 * What is pinned here is the hierarchy, not the cards: one next move at the
 * top, each action on the card it changes and nowhere else, and the old
 * `#sites` / `#notices` addresses still landing on the card they name now that
 * the cards sit in tabs. The dashboard links rows to `#sites`; a notice links
 * back to `#notices`. Both were written before the tabs existed.
 */

import { HttpResponse, http } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ProjectDetailPage from "@/app/(app)/projects/[uuid]/page";
import { makeMe, makeProject } from "@/test/fixtures";
import { act, render, screen, within } from "@/test/render";
import { API, server } from "@/test/server";

const PROJECT = "22222222-2222-4222-8222-222222222222";

const dpo = () =>
  makeMe({
    role: "dpo",
    writes: ["project", "notice", "site", "link", "export"],
    nav: ["dashboard", "projects", "collections", "exports", "links", "audit"],
  });
let me = dpo();

vi.mock("next/navigation", () => ({
  useParams: () => ({ uuid: PROJECT }),
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
  useAuth: () => ({ me }),
  useToast: () => ({ success: vi.fn(), error: vi.fn(), warning: vi.fn() }),
}));

function serveProject(status = "approved") {
  server.use(
    http.get(`${API}/projects/${PROJECT}`, () =>
      HttpResponse.json(makeProject({ project_uuid: PROJECT, project_status: status as never })),
    ),
    http.get(`${API}/projects/${PROJECT}/summary`, () =>
      HttpResponse.json({
        project_uuid: PROJECT,
        project_name: "Retail footfall study",
        project_status: status,
        counts: {
          notices: 1,
          sites: 1,
          approvals: 1,
          purposes: 2,
          active_links: 0,
          exports: 0,
          collections: 0,
        },
        consents: { total: 0, consented: 0, partial: 0, declined: 0, withdrawn: 0 },
        readiness: { notice_published: true, rule3_complete: true, approvals_with_proof: 1 },
      }),
    ),
    http.get(`${API}/projects/${PROJECT}/history`, () => HttpResponse.json([])),
    http.get(`${API}/projects/${PROJECT}/transitions`, () =>
      HttpResponse.json({
        current: status,
        available: [{ to: "closed", allowed: true, reason_required: true }],
      }),
    ),
    http.get(`${API}/projects/${PROJECT}/notices`, () => HttpResponse.json([])),
    http.get(`${API}/projects/${PROJECT}/sites`, () =>
      HttpResponse.json([
        {
          site_uuid: "33333333-3333-4333-8333-333333333333",
          site_label: "Pune campus",
          location: "Pune",
          status: "active",
          active_links: 0,
          source_uuid: null,
        },
      ]),
    ),
    http.get(`${API}/projects/${PROJECT}/links`, () => HttpResponse.json([])),
    http.get(`${API}/projects/${PROJECT}/approvals`, () => HttpResponse.json([])),
    http.get(`${API}/projects/${PROJECT}/processors`, () => HttpResponse.json([])),
    http.get(`${API}/projects/${PROJECT}/collections`, () =>
      HttpResponse.json({ items: [], next_cursor: null, total: 0 }),
    ),
    http.get(`${API}/projects/${PROJECT}/exports`, () => HttpResponse.json([])),
  );
}

beforeEach(() => {
  me = dpo();
  window.history.replaceState(null, "", `/projects/${PROJECT}`);
});

describe("the project workspace", () => {
  it("opens on the overview with one next move at the top", async () => {
    serveProject();
    render(<ProjectDetailPage />);

    expect(await screen.findByText("What happens next")).toBeInTheDocument();
    expect(screen.getAllByText("What happens next")).toHaveLength(1);
    expect(screen.queryByText("Next steps")).not.toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Overview" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });

  it("keeps card actions off the header", async () => {
    serveProject();
    render(<ProjectDetailPage />);
    await screen.findByText("What happens next");

    // The header holds the project's own controls; adding a site or a notice
    // belongs to the card it changes.
    const header = screen.getByTestId("page-actions");
    expect(within(header).getByRole("link", { name: /audit trail/i })).toBeInTheDocument();
    for (const name of [/add site/i, /upload a notice/i, /upload approval/i, /generate export/i])
      expect(within(header).queryByRole("button", { name })).toBeNull();
  });

  it("lands an old #sites address on the sites card, in the consent tab", async () => {
    window.history.replaceState(null, "", `/projects/${PROJECT}#sites`);
    serveProject();
    render(<ProjectDetailPage />);

    expect(await screen.findByText("Pune campus")).toBeVisible();
    expect(screen.getByRole("tab", { name: /Consent/ })).toHaveAttribute("aria-selected", "true");
    // Added on the card, once: the sites card has a site, so no empty state
    // repeats the control.
    expect(screen.getAllByRole("button", { name: /add site/i })).toHaveLength(1);
  });

  it("opens the records a glance figure counts", async () => {
    serveProject();
    const { user } = render(<ProjectDetailPage />);

    const sites = await screen.findByRole("link", { name: /^Sites\s*1$/ });
    expect(sites).toHaveAttribute("href", "#sites");

    await user.click(screen.getByRole("link", { name: /^Notices\s*1$/ }));
    await act(async () => {});
    expect(screen.getByRole("tab", { name: "Setup" })).toHaveAttribute("aria-selected", "true");
  });

  it("leaves a figure this role cannot open as a number", async () => {
    me = makeMe({ role: "rnd_user", writes: ["project"], nav: ["dashboard", "projects"] });
    serveProject();
    render(<ProjectDetailPage />);

    await screen.findByRole("link", { name: /^Sites\s*1$/ });
    expect(screen.queryByRole("link", { name: /^Exports\s*0$/ })).toBeNull();
    expect(screen.getByText("Exports")).toBeInTheDocument();
  });

  it("names a tab in the address and adopts it on arrival", async () => {
    window.history.replaceState(null, "", `/projects/${PROJECT}#exchanges`);
    serveProject();
    render(<ProjectDetailPage />);

    expect(await screen.findByText("No collections yet")).toBeVisible();
    expect(screen.getByText("No exports yet")).toBeVisible();
    expect(screen.getByRole("button", { name: /generate export/i })).toBeVisible();
  });

  it("lists the project's consents, opened from a glance figure narrowed to it", async () => {
    me = makeMe({ ...dpo(), nav: [...dpo().nav, "consents"] });
    serveProject();
    const asked: URLSearchParams[] = [];
    server.use(
      http.get(`${API}/projects/${PROJECT}/summary`, () =>
        HttpResponse.json({
          project_uuid: PROJECT,
          project_name: "Retail footfall study",
          project_status: "approved",
          counts: { notices: 1, sites: 1, approvals: 1, purposes: 2, active_links: 0, exports: 0, collections: 0 },
          consents: { total: 3, consented: 2, partial: 1, declined: 0, withdrawn: 0 },
          readiness: { notice_published: true, rule3_complete: true, approvals_with_proof: 1 },
        }),
      ),
      http.get(`${API}/projects/${PROJECT}/consents`, ({ request }) => {
        asked.push(new URL(request.url).searchParams);
        return HttpResponse.json({
          items: [
            {
              consent_uuid: "44444444-4444-4444-8444-444444444444",
              subject_uuid: "55555555-5555-4555-8555-555555555555",
              subject_name: "Asha Rao",
              subject_email: "asha@example.com",
              subject_mobile: null,
              site_uuid: "33333333-3333-4333-8333-333333333333",
              site_label: "Pune campus",
              served_at: "2026-10-01T10:00:00Z",
              affirmative_action_at: "2026-10-01T10:01:00Z",
              action_type: "click",
              is_withdrawal: false,
              consent_status: "partial",
              granted_count: 1,
              refused_count: 1,
            },
          ],
          next_cursor: null,
          total: 1,
        });
      }),
    );
    const { user } = render(<ProjectDetailPage />);

    const partial = await screen.findByRole("link", { name: /^Partial\s*1$/ });
    expect(partial).toHaveAttribute("href", "#consents");
    await user.click(partial);
    await act(async () => {});

    expect(screen.getByRole("tab", { name: /Consent/ })).toHaveAttribute("aria-selected", "true");
    const row = await screen.findByRole("link", { name: "Asha Rao" });
    expect(row).toHaveAttribute("href", "/consents/44444444-4444-4444-8444-444444444444");
    expect(screen.getByText("1 of 2")).toBeInTheDocument();
    expect(screen.getByLabelText("Status")).toHaveValue("partial");
    await vi.waitFor(() => expect(asked.at(-1)!.get("status")).toBe("partial"));
    expect(screen.getByRole("link", { name: /Open in Consents/ })).toHaveAttribute(
      "href",
      `/consents?project=${PROJECT}`,
    );
  });

  it("shows no consent list to a role that does not read consents", async () => {
    me = makeMe({ role: "rnd_user", writes: ["project"], nav: ["dashboard", "projects"] });
    window.history.replaceState(null, "", `/projects/${PROJECT}#consent`);
    serveProject();
    render(<ProjectDetailPage />);

    expect(await screen.findByText("Pune campus")).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Consents" })).toBeNull();
    expect(screen.queryByRole("link", { name: /^Total\s*0$/ })).toBeNull();
  });
});
