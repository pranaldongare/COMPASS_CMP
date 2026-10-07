/**
 * The Notices screen (2026-10-07): the DPO has a Templates tab - notices
 * written before any project exists - and starts a new one there. Nobody else
 * sees the tab.
 */
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";

import NoticesPage from "@/app/(app)/notices/page";
import { makeMe } from "@/test/fixtures";
import { makeTemplate } from "@/test/notice-templates";
import { render, screen, waitFor } from "@/test/render";
import { API, server } from "@/test/server";
import type { Role } from "@/types";

const push = vi.fn();
let role: Role = "dpo";

vi.mock("next/navigation", () => ({
  useParams: () => ({}),
  useSearchParams: () => new URLSearchParams(window.location.search),
  usePathname: () => "/notices",
  useRouter: () => ({ push, replace: vi.fn(), back: vi.fn(), refresh: vi.fn() }),
}));

vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: React.AnchorHTMLAttributes<HTMLAnchorElement>) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

vi.mock("@/providers", () => ({
  useAuth: () => ({ me: makeMe({ role, nav: ["dashboard", "notices"] }) }),
  useToast: () => ({ success: vi.fn(), error: vi.fn(), warning: vi.fn() }),
}));

function serve(onCreate: (body: Record<string, unknown>) => void = () => {}) {
  server.use(
    http.get(`${API}/notices`, () => HttpResponse.json({ items: [], next_cursor: null, total: 0 })),
    http.get(`${API}/notice-templates`, () => HttpResponse.json([makeTemplate()])),
    http.post(`${API}/notice-templates`, async ({ request }) => {
      onCreate((await request.json()) as Record<string, unknown>);
      return HttpResponse.json(
        makeTemplate({ template_uuid: "52525252-5252-4252-8252-525252525252" }),
        { status: 201 },
      );
    }),
  );
}

describe("NoticesPage", () => {
  it("gives the DPO a Templates tab, with each template's ID", async () => {
    role = "dpo";
    window.history.replaceState(null, "", "/notices");
    serve();
    const { user } = render(<NoticesPage />);
    await user.click(await screen.findByRole("tab", { name: "Templates" }));
    expect(await screen.findByText("TPL-0007")).toBeInTheDocument();
    expect(screen.getByText("Gait video studies, adults")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "TPL-0007" })).toHaveAttribute(
      "href",
      "/notices/templates/51515151-5151-4151-8151-515151515151",
    );
  });

  it("lets the DPO write a template with no project, and opens it", async () => {
    role = "dpo";
    window.history.replaceState(null, "", "/notices?tab=templates");
    const created = vi.fn();
    serve(created);
    const { user } = render(<NoticesPage />);
    await user.click(await screen.findByRole("button", { name: /New template/ }));

    await user.type(screen.getByLabelText(/Template name/), "Speech studies");
    await user.type(screen.getByLabelText(/DPO contact/), "dpo@example.org");
    await user.type(screen.getByLabelText(/Withdraw consent URL/), "https://example.org/w");
    await user.type(screen.getByLabelText(/Exercise rights URL/), "https://example.org/r");
    await user.type(screen.getByLabelText(/Board complaint URL/), "https://example.org/b");
    await user.click(screen.getByRole("button", { name: "Create template" }));

    await waitFor(() =>
      expect(push).toHaveBeenCalledWith(
        "/notices/templates/52525252-5252-4252-8252-525252525252",
      ),
    );
    expect(created).toHaveBeenCalledWith(
      expect.objectContaining({ title: "Speech studies", rendered_text: null }),
    );
    expect(created.mock.calls[0][0]).not.toHaveProperty("project_uuid");
  });

  it("shows no templates to anybody but the DPO", async () => {
    role = "rnd_user";
    window.history.replaceState(null, "", "/notices?tab=templates");
    serve();
    render(<NoticesPage />);
    await screen.findByText(/No notices yet/);
    expect(screen.queryByRole("tab", { name: "Templates" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /New template/ })).not.toBeInTheDocument();
  });
});
