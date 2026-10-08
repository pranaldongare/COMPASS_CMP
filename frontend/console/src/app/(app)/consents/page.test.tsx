/**
 * Consents, filtered (2026-10-08): by project, the project's site, full or
 * partial, and when the consent was given - each sent to the API and kept in
 * the URL.
 */
import { HttpResponse, http } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ConsentsPage from "@/app/(app)/consents/page";
import { render, screen } from "@/test/render";
import { API, server } from "@/test/server";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(window.location.search),
  usePathname: () => window.location.pathname,
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
}));

const PROJECT = "11111111-1111-4111-8111-111111111111";
const SITE = "22222222-2222-4222-8222-222222222222";

beforeEach(() => window.history.replaceState(null, "", "/consents"));

describe("Consents filters", () => {
  it("narrows by project, site, partial and dates, and asks the API for exactly that", async () => {
    const asked: URLSearchParams[] = [];
    server.use(
      http.get(`${API}/consents`, ({ request }) => {
        asked.push(new URL(request.url).searchParams);
        return HttpResponse.json({ items: [], next_cursor: null, total: 0 });
      }),
      http.get(`${API}/projects`, () =>
        HttpResponse.json({
          items: [{ project_uuid: PROJECT, project_name: "Gait Study 2026" }],
          next_cursor: null,
          total: 1,
        }),
      ),
      http.get(`${API}/projects/${PROJECT}/sites`, () =>
        HttpResponse.json([{ site_uuid: SITE, site_label: "Pune lab" }]),
      ),
    );
    const { user } = render(<ConsentsPage />);

    expect(await screen.findByRole("option", { name: "Gait Study 2026" })).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("Project"), PROJECT);
    await user.selectOptions(await screen.findByLabelText("Site"), await screen.findByRole("option", { name: "Pune lab" }));
    await user.selectOptions(screen.getByLabelText("Status"), "partial");
    await user.type(screen.getByLabelText("Given from"), "2026-10-01");

    await vi.waitFor(() => {
      const last = asked.at(-1)!;
      expect(last.get("project")).toBe(PROJECT);
      expect(last.get("site")).toBe(SITE);
      expect(last.get("status")).toBe("partial");
      expect(last.get("from")).toBe("2026-10-01T00:00:00");
    });
    expect(new URLSearchParams(window.location.search).get("site")).toBe(SITE);
    expect(screen.getByText("No consents match")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Clear filters" }));
    await vi.waitFor(() => expect([...asked.at(-1)!.keys()].filter((k) => k !== "limit")).toEqual([]));
  });
});
