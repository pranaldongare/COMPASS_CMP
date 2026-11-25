/**
 * Employee check (ADR 0046): the administrator sets VerifyEmail's address and
 * key, keeps the organisation's domains, and can ask about one address. The
 * key is never shown again; saving without typing one keeps it.
 */
import { HttpResponse, http } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import EmployeeCheckPage from "@/app/(app)/employee-check/page";
import type { EmployeeCheckSettings } from "@/features/employee-check/api";
import { render, screen, within } from "@/test/render";
import { API, server } from "@/test/server";

vi.mock("next/navigation", () => ({
  usePathname: () => "/employee-check",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(""),
}));

const toast = vi.hoisted(() => ({
  success: vi.fn(),
  error: vi.fn(),
  warning: vi.fn(),
  info: vi.fn(),
}));
vi.mock("@/providers", () => ({
  useToast: () => toast,
  useOptionalAuth: () => null,
}));

const saved = (over: Partial<EmployeeCheckSettings> = {}): EmployeeCheckSettings => ({
  base_url: null,
  api_key_set: false,
  api_key_header: "X-API-Key",
  enabled: false,
  allow_other_domains: true,
  domains: [{ domain: "cmp.local", added_at: "2026-11-25T10:00:00Z", added_by_name: null }],
  updated_at: null,
  updated_by_name: null,
  ...over,
});

function serve(now: EmployeeCheckSettings) {
  const sent: Record<string, unknown>[] = [];
  server.use(
    http.get(`${API}/employee-check`, () => HttpResponse.json(now)),
    http.put(`${API}/employee-check`, async ({ request }) => {
      const body = (await request.json()) as Record<string, unknown>;
      sent.push(body);
      return HttpResponse.json(
        saved({
          base_url: body.base_url as string | null,
          enabled: Boolean(body.enabled),
          allow_other_domains: Boolean(body.allow_other_domains),
          api_key_set: Boolean(body.api_key) || now.api_key_set,
        }),
      );
    }),
    http.post(`${API}/employee-check/domains`, async ({ request }) => {
      const { domain } = (await request.json()) as { domain: string };
      return HttpResponse.json(
        [
          ...now.domains,
          { domain, added_at: "2026-11-25T11:00:00Z", added_by_name: "Admin" },
        ],
        { status: 201 },
      );
    }),
    http.delete(`${API}/employee-check/domains/:domain`, () => HttpResponse.json([])),
    http.post(`${API}/employee-check/test`, () =>
      HttpResponse.json({
        result: "inactive",
        message: "Not an active employee: left, or not known to the organisation.",
        on_company_domain: true,
      }),
    ),
  );
  return sent;
}

beforeEach(() => vi.clearAllMocks());

describe("Employee check", () => {
  it("says what the answer does before anything is set", async () => {
    serve(saved());
    render(<EmployeeCheckPage />);
    expect(
      await screen.findByText(/The administrator is never checked/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/never refused - a former employee keeps their rights/),
    ).toBeInTheDocument();
  });

  it("saves the address and key, and keeps a stored key when none is typed", async () => {
    const sent = serve(saved({ api_key_set: true, base_url: "https://hr.test/api" }));
    const { user } = render(<EmployeeCheckPage />);
    const address = await screen.findByLabelText("VerifyEmail address");
    expect(address).toHaveValue("https://hr.test/api");
    expect(screen.getByLabelText("API key")).toHaveValue("");
    await user.click(screen.getByLabelText("Check employees at sign-in"));
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(sent[0]).toMatchObject({
      base_url: "https://hr.test/api",
      enabled: true,
      allow_other_domains: true,
    });
    expect(sent[0]).not.toHaveProperty("api_key");
    expect(toast.success).toHaveBeenCalledWith("Employee check saved", "Switched on.");
  });

  it("will not switch on without an address", async () => {
    const sent = serve(saved());
    const { user } = render(<EmployeeCheckPage />);
    await user.click(await screen.findByLabelText("Check employees at sign-in"));
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(
      screen.getByText("Enter VerifyEmail's address before switching it on."),
    ).toBeInTheDocument();
    expect(sent).toEqual([]);
  });

  it("adds and removes the organisation's domains", async () => {
    serve(saved());
    const { user } = render(<EmployeeCheckPage />);
    const list = await screen.findByRole("list", { name: "Domains" });
    expect(within(list).getByText("cmp.local")).toBeInTheDocument();
    await user.type(screen.getByLabelText("Add a domain"), "company.example");
    await user.click(screen.getByRole("button", { name: "Add" }));
    expect(await screen.findByText("company.example")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Remove cmp.local" }));
    expect(await screen.findByText(/No domains yet/)).toBeInTheDocument();
  });

  it("asks about one address once switched on, and says the answer in words", async () => {
    serve(saved({ enabled: true, base_url: "https://hr.test/api" }));
    const { user } = render(<EmployeeCheckPage />);
    await user.type(await screen.findByLabelText("Email address"), "someone@cmp.local");
    await user.click(screen.getByRole("button", { name: "Ask VerifyEmail" }));
    expect(await screen.findByText(/Not an active employee: left/)).toBeInTheDocument();
  });

  it("offers no test while the check is off", async () => {
    serve(saved());
    render(<EmployeeCheckPage />);
    expect(await screen.findByRole("button", { name: "Ask VerifyEmail" })).toBeDisabled();
  });
});
