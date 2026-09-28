/**
 * "Use an existing notice" offers every approved or published notice the
 * server names - including other authors' projects - not only the notices on
 * the caller's own projects, which is all `GET /notices` shows an R&D User.
 */
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";

import { NoticeCopyForm } from "@/features/notices/components/notice-copy-form";
import { render, screen } from "@/test/render";
import { API, server } from "@/test/server";

vi.mock("@/providers", () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn() }),
}));

const source = (over: Record<string, unknown>) => ({
  notice_uuid: "55555555-5555-4555-8555-555555555555",
  notice_code: "NTC-ASR-2026",
  version: 1,
  status: "published",
  published_at: "2026-09-28T10:00:00Z",
  created_at: "2026-09-28T09:00:00Z",
  project_uuid: "66666666-6666-4666-8666-666666666666",
  project_name: "Hindi Speech Corpus",
  purpose_count: 2,
  language_count: 1,
  ...over,
});

describe("NoticeCopyForm", () => {
  it("offers every approved or published notice, whichever project it is on", async () => {
    let asked = false;
    server.use(
      http.get(`${API}/notices/copy-sources`, () => {
        asked = true;
        return HttpResponse.json([
          source({
            notice_uuid: "77777777-7777-4777-8777-777777777777",
            status: "approved",
            notice_code: "NTC-MODEL-2026",
            project_name: "Model notices",
          }),
          source({}),
        ]);
      }),
    );
    render(
      <NoticeCopyForm
        projectUuid="88888888-8888-4888-8888-888888888888"
        onDone={() => undefined}
      />,
    );

    expect(
      await screen.findByRole("option", { name: "NTC-ASR-2026 v1 — Hindi Speech Corpus" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("option", {
        name: "NTC-MODEL-2026 v1 — Model notices (approved, not yet published)",
      }),
    ).toBeInTheDocument();
    expect(asked).toBe(true);
  });

  it("says so when nothing has been approved yet", async () => {
    server.use(http.get(`${API}/notices/copy-sources`, () => HttpResponse.json([])));
    render(
      <NoticeCopyForm
        projectUuid="88888888-8888-4888-8888-888888888888"
        onDone={() => undefined}
      />,
    );
    expect(await screen.findByText(/nothing to copy from yet/i)).toBeInTheDocument();
  });
});
