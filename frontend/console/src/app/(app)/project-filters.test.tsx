/**
 * Approvals, consent links and collection sites, filtered by project
 * (2026-10-09): the choice goes to the API as `project` and stays in the URL.
 */
import { HttpResponse, http } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ApprovalsPage from "@/app/(app)/approvals/page";
import LinksPage from "@/app/(app)/links/page";
import SitesPage from "@/app/(app)/sites/page";
import { render, screen } from "@/test/render";
import { API, server } from "@/test/server";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(window.location.search),
  usePathname: () => window.location.pathname,
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
}));

vi.mock("@/providers", () => ({
  useAuth: () => ({ me: null }),
  useToast: () => ({ success: vi.fn(), error: vi.fn(), warning: vi.fn() }),
}));

const PROJECT = "11111111-1111-4111-8111-111111111111";

const pages = [
  { name: "Approval documents", path: "/approvals", Page: ApprovalsPage },
  { name: "Consent links", path: "/links", Page: LinksPage },
  { name: "Collection sites", path: "/sites", Page: SitesPage },
];

describe.each(pages)("$name", ({ path, Page }) => {
  beforeEach(() => window.history.replaceState(null, "", path));

  it("narrows to one project and asks the API for it", async () => {
    const asked: URLSearchParams[] = [];
    server.use(
      http.get(`${API}${path}`, ({ request }) => {
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
    );
    const { user } = render(<Page />);

    expect(await screen.findByRole("option", { name: "Gait Study 2026" })).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("Project"), PROJECT);

    await vi.waitFor(() => expect(asked.at(-1)!.get("project")).toBe(PROJECT));
    expect(new URLSearchParams(window.location.search).get("project")).toBe(PROJECT);
  });
});
