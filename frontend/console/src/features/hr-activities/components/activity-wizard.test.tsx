/**
 * Creating an HR activity (ADR 0033): the mandatory purpose is chosen and
 * cannot be unticked, the description is counted against the version's
 * limit, and Create sends what was chosen and shows the link once.
 */
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";

import { ActivityWizard } from "@/features/hr-activities/components/activity-wizard";
import { render, screen } from "@/test/render";
import { API, server } from "@/test/server";
import type { ActivityOptionCategory } from "@/types";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn(), refresh: vi.fn() }),
}));
vi.mock("@/providers", () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn(), warning: vi.fn() }),
}));

const SESSIONS = "c1c1c1c1-c1c1-41c1-81c1-c1c1c1c1c1c1";
const SURVEY = "c2c2c2c2-c2c2-42c2-82c2-c2c2c2c2c2c2";
const OPTIONS: ActivityOptionCategory[] = [
  {
    category_uuid: "d1d1d1d1-d1d1-41d1-81d1-d1d1d1d1d1d1",
    category_code: "WELLNESS",
    name: "Employee wellness",
    versions: [
      {
        version_uuid: "e1e1e1e1-e1e1-41e1-81e1-e1e1e1e1e1e1",
        version: 1,
        template_uuid: "f1f1f1f1-f1f1-41f1-81f1-f1f1f1f1f1f1",
        template_code: "TPL-0101",
        template_title: "Wellness sessions",
        slot_guidance: "Say what the sessions are and when.",
        slot_max_length: 40,
        reconsent_required: false,
        purposes: [
          {
            purpose_uuid: SESSIONS,
            purpose_code: "P-SESS",
            name: "Wellness sessions",
            is_mandatory: true,
            display_order: 0,
          },
          {
            purpose_uuid: SURVEY,
            purpose_code: "P-SURV",
            name: "Follow-up survey",
            is_mandatory: false,
            display_order: 1,
          },
        ],
      },
    ],
  },
];

describe("ActivityWizard", () => {
  it("locks the mandatory purpose, counts the description, and creates", async () => {
    let sent: Record<string, unknown> | null = null;
    server.use(
      http.get(`${API}/hr/activities/options`, () => HttpResponse.json(OPTIONS)),
      http.post(`${API}/hr/activities`, async ({ request }) => {
        sent = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(
          {
            activity_uuid: "a9a9a9a9-a9a9-49a9-89a9-a9a9a9a9a9a9",
            notice_uuid: null,
            link_uuid: "b9b9b9b9-b9b9-49b9-89b9-b9b9b9b9b9b9",
            url_path: "/c/token123",
            expires_at: "2026-12-01T00:00:00Z",
            audience_mode: "sso",
          },
          { status: 201 },
        );
      }),
    );
    const { user } = render(<ActivityWizard onDone={vi.fn()} />);

    await user.selectOptions(await screen.findByLabelText(/Category/), "d1d1d1d1-d1d1-41d1-81d1-d1d1d1d1d1d1");
    await user.selectOptions(screen.getByLabelText(/Template version/), "e1e1e1e1-e1e1-41e1-81e1-e1e1e1e1e1e1");
    await user.click(screen.getByRole("button", { name: "Next" }));

    const mandatory = screen.getByRole("checkbox", { name: /Wellness sessions/ });
    expect(mandatory).toBeChecked();
    expect(mandatory).toBeDisabled();
    await user.click(screen.getByRole("checkbox", { name: /Follow-up survey/ }));
    await user.click(screen.getByRole("button", { name: "Next" }));

    await user.type(screen.getByLabelText(/Activity name/), "Wellness week");
    await user.type(screen.getByLabelText(/Description/), "x".repeat(41));
    expect(screen.getByText("41 / 40")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();
    await user.clear(screen.getByLabelText(/Description/));
    await user.type(screen.getByLabelText(/Description/), "Four lunchtime sessions.");
    await user.click(screen.getByRole("button", { name: "Next" }));

    await user.click(screen.getByRole("button", { name: "Create the activity" }));
    expect(await screen.findByText("The activity is live")).toBeInTheDocument();
    expect(sent).toMatchObject({
      purpose_uuids: [SESSIONS, SURVEY],
      name: "Wellness week",
      description: "Four lunchtime sessions.",
      audience_mode: "sso",
    });
  });

  it("says so when there is nothing to make an activity from", async () => {
    server.use(http.get(`${API}/hr/activities/options`, () => HttpResponse.json([])));
    render(<ActivityWizard onDone={vi.fn()} />);
    expect(await screen.findByText("Nothing to make an activity from yet")).toBeInTheDocument();
  });
});
