/**
 * Reading a register's record without editing it (2026-10-09): a data
 * source, a processor and an account each have a page; Edit is a button there
 * only for those who may. The source register filters by processor.
 */
import { HttpResponse, http } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ProcessorDetailPage from "@/app/(app)/processors/[uuid]/page";
import SourceDetailPage from "@/app/(app)/sources/[uuid]/page";
import SourcesPage from "@/app/(app)/sources/page";
import UserDetailPage from "@/app/(app)/users/[uuid]/page";
import { makeMe } from "@/test/fixtures";
import { render, screen } from "@/test/render";
import { API, server } from "@/test/server";

const role = vi.hoisted(() => ({ current: "admin" }));
const UUID = "12121212-1212-4212-8212-121212121212";
const PROC = "34343434-3434-4434-8434-343434343434";

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

const source = {
  source_uuid: UUID,
  source_code: "SRC-9",
  name: "Gait rig",
  source_role: "collection",
  exchange_mode: "file_import",
  id_scheme: null,
  is_authoritative_for: [],
  status: "active",
  created_at: "2026-09-01T10:00:00Z",
  processor_uuid: PROC,
  processor_name: "Acme Labs",
  is_in_house: false,
  has_owner: false,
  owner_user_uuid: null,
  owner_name: null,
  owner_role: null,
};

beforeEach(() => {
  role.current = "admin";
  window.history.replaceState(null, "", "/sources");
});

describe("Register records, to read", () => {
  it("shows a data source, its processor as a link, and Edit only to an editor", async () => {
    server.use(http.get(`${API}/sources/${UUID}`, () => HttpResponse.json(source)));
    const { unmount } = render(<SourceDetailPage />);
    expect(await screen.findByRole("heading", { name: "Gait rig" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Acme Labs" })).toHaveAttribute("href", `/processors/${PROC}`);
    expect(screen.getByRole("button", { name: /edit/i })).toBeInTheDocument();
    unmount();

    role.current = "dco";
    render(<SourceDetailPage />);
    expect(await screen.findByRole("heading", { name: "Gait rig" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /edit/i })).not.toBeInTheDocument();
  });

  it("shows a processor with the sources it operates", async () => {
    server.use(
      http.get(`${API}/processors/${UUID}`, () =>
        HttpResponse.json({
          processor_uuid: UUID,
          legal_name: "Acme Labs",
          type: "lab",
          contract_ref: "C-1",
          security_confirmed_at: "2026-09-01",
          status: "active",
          is_in_house: false,
          location_country: null,
          created_at: "2026-09-01T10:00:00Z",
        }),
      ),
      http.get(`${API}/sources`, () => HttpResponse.json({ items: [source], next_cursor: null, total: 1 })),
      http.get(`${API}/processors/${UUID}/respondents`, () => HttpResponse.json([])),
    );
    render(<ProcessorDetailPage />);
    expect(await screen.findByRole("heading", { name: "Acme Labs" })).toBeInTheDocument();
    expect(await screen.findByRole("link", { name: "Gait rig" })).toHaveAttribute("href", `/sources/${UUID}`);
    expect(screen.getByText(/not recorded - an export to this processor is refused/i)).toBeInTheDocument();
  });

  it("shows an account and how its person type changed", async () => {
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
        }),
      ),
      http.get(`${API}/users/${UUID}/person-type-history`, () =>
        HttpResponse.json([
          {
            history_uuid: "h1",
            from_type: "contractor",
            to_type: "employee",
            reason: null,
            changed_at: "2026-09-02T10:00:00Z",
            changed_by_uuid: "x",
            changed_by_name: "Admin One",
          },
        ]),
      ),
    );
    render(<UserDetailPage />);
    expect(await screen.findByRole("heading", { name: "Asha Rao" })).toBeInTheDocument();
    expect(await screen.findByText("Admin One")).toBeInTheDocument();
  });

  it("filters the source register by processor", async () => {
    const asked: (string | null)[] = [];
    server.use(
      http.get(`${API}/processors`, () =>
        HttpResponse.json({
          items: [{ processor_uuid: PROC, legal_name: "Acme Labs" }],
          next_cursor: null,
          total: 1,
        }),
      ),
      http.get(`${API}/sources`, ({ request }) => {
        asked.push(new URL(request.url).searchParams.get("processor"));
        return HttpResponse.json({ items: [source], next_cursor: null, total: 1 });
      }),
    );
    const { user } = render(<SourcesPage />);
    expect(await screen.findByRole("link", { name: /view/i })).toHaveAttribute("href", `/sources/${UUID}`);
    await user.selectOptions(screen.getByLabelText("Processor"), await screen.findByRole("option", { name: "Acme Labs" }));
    await vi.waitFor(() => expect(asked.at(-1)).toBe(PROC));
  });
});
