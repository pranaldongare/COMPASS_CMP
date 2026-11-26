/**
 * Retention (ADR 0047): the officer's register - tiles that filter it, one row
 * per project, purpose and month - and the one asked answering in their inbox.
 */
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";

import RetentionActionsPage from "@/app/(app)/retention-actions/page";
import RetentionPage from "@/app/(app)/retention/page";
import type { RetentionAction, RetentionReview } from "@/features/retention/api";
import { render, screen } from "@/test/render";
import { API, server } from "@/test/server";

vi.mock("next/navigation", () => ({
  usePathname: () => "/retention",
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

const review = (over: Partial<RetentionReview>): RetentionReview => ({
  review_uuid: "r1",
  reference: "RET-2026-11-0001-0001",
  kind: "retention",
  status: "in_progress",
  office: "rnd",
  cohort: "2026-11-01",
  project_uuid: "p1",
  project_name: "Gait study",
  project_status: "approved",
  is_activity: false,
  purpose_code: "PUR-0001",
  purpose_name: "Model training",
  retention_days: 365,
  validity_days: null,
  lapse_behaviour: "quarantine",
  notify_before_erasure: true,
  people: 12,
  held: 0,
  renewed: 0,
  first_due_at: "2026-11-02T00:00:00Z",
  last_due_at: "2026-11-20T00:00:00Z",
  actions: 2,
  actions_open: 1,
  actions_to_review: 1,
  reconsent: null,
  opened_at: "2026-11-02T00:00:00Z",
  closed_at: null,
  closed_by_name: null,
  close_note: null,
  ...over,
});

const action: RetentionAction = {
  action_uuid: "a1",
  review_uuid: "r1",
  reference: "VAL-2026-12-0001-0001",
  review_kind: "validity",
  kind: "owner",
  label: "Test DCO Admin",
  channel: "console",
  assignee_name: "Test DCO Admin",
  status: "open",
  outcome: null,
  reason: null,
  keep_until: null,
  reconsent: null,
  due_at: "2026-12-20T00:00:00Z",
  answered_at: null,
  answered_by_name: null,
  accepted_at: null,
  accepted_by_name: null,
  sent_back_reason: null,
  overdue: false,
};

describe("the retention register", () => {
  it("counts by status and filters by the tile pressed", async () => {
    server.use(
      http.get(`${API}/retention/reviews`, () =>
        HttpResponse.json([
          review({}),
          review({
            review_uuid: "r2",
            reference: "VAL-2026-12-0002-0001",
            kind: "validity",
            status: "upcoming",
            project_name: "Speech study",
            actions: 0,
            actions_open: 0,
            actions_to_review: 0,
          }),
        ]),
      ),
    );
    const { user } = render(<RetentionPage />);

    expect(await screen.findByText("Gait study")).toBeInTheDocument();
    expect(screen.getByText("Speech study")).toBeInTheDocument();
    expect(screen.getByText("1 to review")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /^Upcoming/ }));
    expect(screen.queryByText("Gait study")).not.toBeInTheDocument();
    expect(screen.getByText("Speech study")).toBeInTheDocument();
  });
});

describe("my retention actions", () => {
  it("asks whether to invite the people again, and sends the answer", async () => {
    let sent: unknown = null;
    server.use(
      http.get(`${API}/retention-actions`, () => HttpResponse.json([action])),
      http.get(`${API}/retention-actions/a1`, () =>
        HttpResponse.json({
          action,
          review: {
            reference: action.reference,
            kind: "validity",
            project_name: "Speech study",
            is_activity: false,
            purpose_code: "PUR-0002",
            purpose_name: "Voice samples",
            people: 30,
            first_due_at: "2026-12-10T00:00:00Z",
            last_due_at: "2026-12-10T00:00:00Z",
            retention_days: 365,
            validity_days: 365,
            status: "in_progress",
          },
        }),
      ),
      http.post(`${API}/retention-actions/a1/answer`, async ({ request }) => {
        sent = await request.json();
        return HttpResponse.json({ ...action, status: "answered", reconsent: true });
      }),
    );
    const { user } = render(<RetentionActionsPage />);

    await user.click(await screen.findByRole("button", { name: "Send the answer" }));
    expect(await screen.findByText(/choose whether to invite/i)).toBeInTheDocument();
    await user.click(screen.getByLabelText(/^Yes, invite them/));
    await user.click(screen.getByRole("button", { name: "Send the answer" }));
    await vi.waitFor(() => expect(sent).toMatchObject({ reconsent: true }));
  });
});
