/**
 * A record's page offers what its register's row menu offers (2026-11-11): a
 * purpose's Edit, Activate and Retire, a source's and a processor's Suspend,
 * and an account's role, MFA, invitation and access - each only to whoever may.
 * And a purpose or a source is created with no code: the platform gives it.
 */
import { HttpResponse, http } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import PurposeDetailPage from "@/app/(app)/purposes/[uuid]/page";
import SourceDetailPage from "@/app/(app)/sources/[uuid]/page";
import UserDetailPage from "@/app/(app)/users/[uuid]/page";
import { PurposeForm } from "@/features/registry/components/purpose-form";
import { makeMe } from "@/test/fixtures";
import { render, screen, waitFor, within } from "@/test/render";
import { API, server } from "@/test/server";

const who = vi.hoisted(() => ({ role: "dpo", writes: ["purpose"] as string[] }));
const UUID = "12121212-1212-4212-8212-121212121212";

vi.mock("next/navigation", () => ({
  useParams: () => ({ uuid: UUID }),
  useSearchParams: () => new URLSearchParams(window.location.search),
  usePathname: () => window.location.pathname,
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
}));
vi.mock("@/providers", () => ({
  useAuth: () => ({ me: makeMe({ role: who.role as never, writes: who.writes as never }) }),
  useToast: () => ({ success: vi.fn(), error: vi.fn() }),
}));

const purpose = (status: string) => ({
  purpose_uuid: UUID,
  purpose_code: "PUR-0007",
  version: 1,
  status,
  name: "Gait model training",
  description: "Training the gait model.",
  uses: "Model training.",
  lawful_basis: "consent_s6",
  s7_clause: null,
  data_categories: ["name"],
  retention_period: "365 days",
  retention_basis: "business_policy",
  erasure_trigger: "withdrawal",
  consent_validity_period: null,
  cross_border_permitted: false,
  permitted_for_minors: false,
  lapse_behaviour: "quarantine",
  created_at: "2026-11-01T10:00:00Z",
  updated_at: "2026-11-01T10:00:00Z",
});

function servePurpose(status: string, retirable = true) {
  const posted: string[] = [];
  server.use(
    http.get(`${API}/purposes/${UUID}`, () => HttpResponse.json(purpose(status))),
    http.get(`${API}/purposes/${UUID}/usage`, () =>
      HttpResponse.json({ items: [], total: 0, retirable }),
    ),
    http.get(`${API}/purposes/${UUID}/versions`, () => HttpResponse.json([purpose(status)])),
    http.post(`${API}/purposes/${UUID}/:act`, ({ params }) => {
      posted.push(String(params.act));
      return HttpResponse.json({ ok: true });
    }),
  );
  return posted;
}

beforeEach(() => {
  who.role = "dpo";
  who.writes = ["purpose"];
});

describe("A purpose's page", () => {
  it("offers a draft's Edit and Activate, and activates it", async () => {
    const posted = servePurpose("draft");
    const { user } = render(<PurposeDetailPage />);
    expect(await screen.findByRole("button", { name: "Edit" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Retire" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Activate" }));
    await waitFor(() => expect(posted).toEqual(["activate"]));
  });

  it("offers an active purpose's Retire, asks first, and not while a notice holds it", async () => {
    const posted = servePurpose("active");
    const { user, unmount } = render(<PurposeDetailPage />);
    await user.click(await screen.findByRole("button", { name: "Retire" }));
    const asking = await screen.findByRole("dialog");
    await user.click(within(asking).getByRole("button", { name: "Retire purpose" }));
    await waitFor(() => expect(posted).toEqual(["retire"]));
    unmount();

    servePurpose("active", false);
    render(<PurposeDetailPage />);
    expect(await screen.findByText(/cannot be retired/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Retire" })).not.toBeInTheDocument();
  });

  it("offers nothing to somebody who cannot write purposes", async () => {
    who.role = "rnd_user";
    who.writes = [];
    servePurpose("draft");
    render(<PurposeDetailPage />);
    expect((await screen.findAllByRole("heading", { name: "Gait model training" }))[0]).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Edit" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Activate" })).not.toBeInTheDocument();
  });

  it("is created with no code: the platform gives one", async () => {
    let body: Record<string, unknown> | undefined;
    server.use(
      http.get(`${API}/meta/data-categories`, () =>
        HttpResponse.json({ items: [{ value: "name", label: "Name", group: "identity" }] }),
      ),
      http.post(`${API}/purposes`, async ({ request }) => {
        body = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(purpose("draft"), { status: 201 });
      }),
    );
    const onDone = vi.fn();
    const { user } = render(<PurposeForm onDone={onDone} />);
    expect(screen.queryByLabelText(/^Code/)).not.toBeInTheDocument();
    await user.type(screen.getByLabelText(/^Name/), "Gait model training");
    await user.type(screen.getByLabelText(/^Description/), "Training the gait model.");
    await user.type(screen.getByLabelText(/^What this allows/), "Model training.");
    await user.click(await screen.findByRole("checkbox", { name: "Name" }));
    await user.click(screen.getByRole("button", { name: "Create purpose" }));
    await waitFor(() => expect(onDone).toHaveBeenCalled());
    expect(body).toBeDefined();
    expect(body).not.toHaveProperty("purpose_code");
  });
});

describe("A data source's page", () => {
  const source = {
    source_uuid: UUID,
    source_code: "SRC-0003",
    name: "Gait rig",
    source_role: "collection",
    exchange_mode: "file_import",
    id_scheme: null,
    is_authoritative_for: [],
    status: "active",
    created_at: "2026-09-01T10:00:00Z",
    processor_uuid: null,
    processor_name: null,
    is_in_house: false,
    has_owner: false,
    owner_user_uuid: null,
    owner_name: null,
    owner_role: null,
  };

  it("suspends the source, asking first, for the DPO and the administrator only", async () => {
    who.role = "admin";
    let suspended = false;
    server.use(
      http.get(`${API}/sources/${UUID}`, () => HttpResponse.json(source)),
      http.post(`${API}/sources/${UUID}/suspend`, () => {
        suspended = true;
        return HttpResponse.json({ ok: true });
      }),
    );
    const { user, unmount } = render(<SourceDetailPage />);
    await user.click(await screen.findByRole("button", { name: "Suspend" }));
    await user.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "Suspend source" }));
    await waitFor(() => expect(suspended).toBe(true));
    unmount();

    who.role = "dco";
    render(<SourceDetailPage />);
    expect((await screen.findAllByRole("heading", { name: "Gait rig" }))[0]).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Suspend" })).not.toBeInTheDocument();
  });
});

describe("An account's page", () => {
  const account = (over: Record<string, unknown> = {}) => ({
    uuid: UUID,
    username: null,
    full_name: "Ravi Kumar",
    email: "ravi@example.org",
    mobile: null,
    organization_id: null,
    role: "dco",
    person_type: "employee",
    status: "active",
    created_at: "2026-09-01T10:00:00Z",
    updated_at: "2026-09-02T10:00:00Z",
    ...over,
  });

  function serveAccount(over: Record<string, unknown> = {}) {
    server.use(
      http.get(`${API}/users/${UUID}`, () => HttpResponse.json(account(over))),
      http.get(`${API}/users/${UUID}/person-type-history`, () => HttpResponse.json([])),
    );
  }

  it("offers the register's actions to an administrator", async () => {
    who.role = "admin";
    serveAccount();
    const { user } = render(<UserDetailPage />);
    expect((await screen.findAllByRole("heading", { name: "Ravi Kumar" }))[0]).toBeInTheDocument();
    for (const name of ["Edit", "Change role", "Reset MFA", "End staff access"]) {
      expect(screen.getByRole("button", { name })).toBeInTheDocument();
    }
    expect(screen.queryByRole("button", { name: "Resend invitation" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Change role" }));
    expect(await screen.findByRole("dialog", { name: "Change role" })).toBeInTheDocument();
  });

  it("offers a pending account its invitation, and nothing to a reader", async () => {
    who.role = "admin";
    serveAccount({ status: "pending" });
    const { unmount } = render(<UserDetailPage />);
    expect(await screen.findByRole("button", { name: "Resend invitation" })).toBeInTheDocument();
    unmount();

    who.role = "dpo";
    serveAccount();
    render(<UserDetailPage />);
    expect((await screen.findAllByRole("heading", { name: "Ravi Kumar" }))[0]).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Change role" })).not.toBeInTheDocument();
  });
});
