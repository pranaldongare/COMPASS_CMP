/**
 * One notice template (0044): its ID up front to hand out, its purposes and
 * text edited in place, retiring it, and the project notices made from it.
 */
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";

import TemplatePage from "@/app/(app)/notices/templates/[uuid]/page";
import { makeMe, makePurpose } from "@/test/fixtures";
import { makeTemplate } from "@/test/notice-templates";
import { render, screen, waitFor, within } from "@/test/render";
import { API, server } from "@/test/server";

const UUID = "51515151-5151-4151-8151-515151515151";

vi.mock("next/navigation", () => ({
  useParams: () => ({ uuid: UUID }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => `/notices/templates/${UUID}`,
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
  useAuth: () => ({ me: makeMe({ role: "dpo", nav: ["dashboard", "notices"] }) }),
  useToast: () => ({ success: vi.fn(), error: vi.fn(), warning: vi.fn() }),
}));

const SPEECH = makePurpose({
  purpose_uuid: "71717171-7171-4171-8171-717171717171",
  purpose_code: "P-SPEECH",
  name: "Speech model training",
  status: "draft",
});

describe("NoticeTemplatePage", () => {
  it("leads with the ID to give out, and lists what a notice from it carries", async () => {
    server.use(
      http.get(`${API}/notice-templates/${UUID}`, () =>
        HttpResponse.json(
          makeTemplate({
            used_count: 1,
            notices: [
              {
                notice_uuid: "81818181-8181-4181-8181-818181818181",
                notice_code: "NTC-GAIT-2026",
                version: 1,
                status: "draft",
                created_at: "2026-10-07T10:00:00Z",
                project_uuid: "91919191-9191-4191-8191-919191919191",
                project_name: "Gait Study Two",
              },
            ],
          }),
        ),
      ),
      http.get(`${API}/purposes`, () =>
        HttpResponse.json({ items: [SPEECH], next_cursor: null, total: 1 }),
      ),
    );
    render(<TemplatePage />);
    expect(await screen.findByText("TPL-0007")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Copy ID/ })).toBeInTheDocument();
    expect(screen.getByText("Gait model training")).toBeInTheDocument();
    expect(screen.getByText("We collect your gait video.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "NTC-GAIT-2026 v1" })).toHaveAttribute(
      "href",
      "/notices/81818181-8181-4181-8181-818181818181",
    );
  });

  it("adds a purpose, draft ones included, and retires the template", async () => {
    const attached = vi.fn();
    const status = vi.fn();
    server.use(
      http.get(`${API}/notice-templates/${UUID}`, () => HttpResponse.json(makeTemplate())),
      http.get(`${API}/purposes`, () =>
        HttpResponse.json({ items: [SPEECH], next_cursor: null, total: 1 }),
      ),
      http.post(`${API}/notice-templates/${UUID}/purposes`, async ({ request }) => {
        attached(await request.json());
        return HttpResponse.json(makeTemplate(), { status: 201 });
      }),
      http.post(`${API}/notice-templates/${UUID}/status`, async ({ request }) => {
        status(await request.json());
        return HttpResponse.json(makeTemplate({ status: "retired" }));
      }),
    );
    const { user } = render(<TemplatePage />);
    const picker = await screen.findByLabelText(/Add a purpose/);
    await within(picker).findByRole("option", { name: /Speech model training.*draft/ });
    await user.selectOptions(picker, SPEECH.purpose_uuid);
    await user.click(screen.getByRole("checkbox", { name: "Mandatory" }));
    await user.click(screen.getByRole("button", { name: "Add" }));
    await waitFor(() =>
      expect(attached).toHaveBeenCalledWith({
        purpose_uuid: SPEECH.purpose_uuid,
        is_mandatory: true,
      }),
    );

    await user.click(screen.getByRole("button", { name: "Retire" }));
    await waitFor(() => expect(status).toHaveBeenCalledWith({ status: "retired" }));
    expect(await screen.findByRole("button", { name: "Bring back" })).toBeInTheDocument();
  });
});
