/**
 * A DCO's or an RCO's own processors (2026-10-09, 0050). The administrator
 * sets them on the account; Data Sources then shows the collector those
 * processors' sources, says which they are, and offers no way to register a
 * source when none is assigned.
 */
import { HttpResponse, http } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import SourcesPage from "@/app/(app)/sources/page";
import UserDetailPage from "@/app/(app)/users/[uuid]/page";
import { makeMe } from "@/test/fixtures";
import { render, screen, within } from "@/test/render";
import { API, server } from "@/test/server";

const role = vi.hoisted(() => ({ current: "dco" }));
const UUID = "12121212-1212-4212-8212-121212121212";
const MINE = "34343434-3434-4434-8434-343434343434";
const OTHER = "56565656-5656-4656-8656-565656565656";

vi.mock("next/navigation", () => ({
  useParams: () => ({ uuid: UUID }),
  useSearchParams: () => new URLSearchParams(window.location.search),
  usePathname: () => window.location.pathname,
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
}));
vi.mock("@/providers", () => ({
  useAuth: () => ({ me: makeMe({ role: role.current as never }) }),
  useToast: () => ({ success: vi.fn(), error: vi.fn() }),
}));

const processor = (uuid: string, legal_name: string) => ({
  processor_uuid: uuid,
  legal_name,
  type: "lab",
  contract_ref: "C-1",
  security_confirmed_at: "2026-09-01",
  status: "active",
  is_in_house: false,
  location_country: "IN",
  created_at: "2026-09-01T10:00:00Z",
});

function serveProcessors(mine: ReturnType<typeof processor>[]) {
  const asked: URLSearchParams[] = [];
  server.use(
    http.get(`${API}/processors`, ({ request }) => {
      const params = new URL(request.url).searchParams;
      asked.push(params);
      const items = params.get("mine") ? mine : [processor(MINE, "Acme Labs"), processor(OTHER, "Other Ltd")];
      return HttpResponse.json({ items, next_cursor: null, total: items.length });
    }),
    http.get(`${API}/sources`, () => HttpResponse.json({ items: [], next_cursor: null, total: 0 })),
  );
  return asked;
}

beforeEach(() => {
  role.current = "dco";
  window.history.replaceState(null, "", "/sources");
});

describe("Data sources, for a collection owner", () => {
  it("says whose sources these are and offers only those processors", async () => {
    serveProcessors([processor(MINE, "Acme Labs")]);
    render(<SourcesPage />);

    expect(
      await screen.findByText(/The data sources of the processors you collect for: Acme Labs/),
    ).toBeInTheDocument();
    const filter = screen.getByLabelText("Processor");
    await vi.waitFor(() =>
      expect(within(filter).getAllByRole("option").map((o) => o.textContent)).toEqual([
        "All processors",
        "Acme Labs",
      ]),
    );
    expect(screen.queryByText("No processor named")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /register source/i })).toBeInTheDocument();
  });

  it("with no processor, says so and offers no registering", async () => {
    serveProcessors([]);
    render(<SourcesPage />);

    expect(await screen.findByText("You collect for no processor yet")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /register source/i })).not.toBeInTheDocument();
  });
});

describe("Collects for, on the account", () => {
  it("lets the administrator set a DCO's processors", async () => {
    role.current = "admin";
    serveProcessors([]);
    const saved: unknown[] = [];
    server.use(
      http.get(`${API}/users/${UUID}`, () =>
        HttpResponse.json({
          uuid: UUID,
          username: null,
          full_name: "Asha Rao",
          email: "asha@example.org",
          mobile: null,
          organization_id: null,
          role: "dco",
          person_type: "employee",
          status: "active",
          created_at: "2026-09-01T10:00:00Z",
          updated_at: "2026-09-02T10:00:00Z",
          processors: [{ processor_uuid: MINE, legal_name: "Acme Labs", is_in_house: false, status: "active" }],
        }),
      ),
      http.get(`${API}/users/${UUID}/person-type-history`, () => HttpResponse.json([])),
      http.put(`${API}/users/${UUID}/processors`, async ({ request }) => {
        saved.push(await request.json());
        return HttpResponse.json([]);
      }),
    );
    const { user } = render(<UserDetailPage />);

    expect(await screen.findByRole("link", { name: "Acme Labs" })).toHaveAttribute("href", `/processors/${MINE}`);
    await user.click(screen.getByRole("button", { name: "Change processors" }));
    await user.click(await screen.findByRole("button", { name: "Other Ltd" }));
    await user.click(screen.getByRole("button", { name: "Save processors" }));

    await vi.waitFor(() => expect(saved).toEqual([{ processor_uuids: [MINE, OTHER] }]));
  });

  it("shows no Change button to the DPO", async () => {
    role.current = "dpo";
    server.use(
      http.get(`${API}/users/${UUID}`, () =>
        HttpResponse.json({
          uuid: UUID,
          username: null,
          full_name: "Ravi Kumar",
          email: "ravi@example.org",
          mobile: null,
          organization_id: null,
          role: "rco",
          person_type: "employee",
          status: "active",
          created_at: "2026-09-01T10:00:00Z",
          updated_at: "2026-09-02T10:00:00Z",
          processors: [],
        }),
      ),
      http.get(`${API}/users/${UUID}/person-type-history`, () => HttpResponse.json([])),
    );
    render(<UserDetailPage />);
    expect(await screen.findByText(/No processor yet/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Change processors" })).not.toBeInTheDocument();
  });
});
