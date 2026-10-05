/**
 * Two fixes from acceptance testing:
 *
 * - The project page offers its next move again at the foot of the page, with
 *   the header's other actions, so nobody scrolls back up to act. The same
 *   controls render twice, so each copy must keep its own ids.
 * - Attaching purposes to a notice has one action, "Attach", which leaves the
 *   dialog open for the next one - not "Attach" and "Done" side by side.
 */
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";

import { TransitionControls } from "@/features/projects/components/transition-controls";
import { NoticePurposesForm } from "@/features/notices/components/notice-purposes-form";
import { makePurpose } from "@/test/fixtures";
import { render, screen, within } from "@/test/render";
import { API, server } from "@/test/server";

vi.mock("@/providers", () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn() }),
}));

const PROJECT = "11111111-2222-4333-8444-555555555555";
const NOTICE = "66666666-7777-4888-8999-000000000000";

describe("the project's next move", () => {
  it("keeps its ids per instance, so two copies never share a description", async () => {
    server.use(
      http.get(`${API}/projects/${PROJECT}/transitions`, () =>
        HttpResponse.json({
          current: "in_draft",
          available: [
            {
              to: "pending_approval",
              allowed: false,
              blocked_by: "No approval with a proof file",
              blockers: ["No approval with a proof file"],
            },
          ],
        }),
      ),
    );
    render(
      <>
        <TransitionControls projectUuid={PROJECT} currentStatus="in_draft" />
        <TransitionControls
          projectUuid={PROJECT}
          currentStatus="in_draft"
          heading="Next steps"
        />
      </>,
    );

    expect(await screen.findByText("What happens next")).toBeInTheDocument();
    expect(screen.getByText("Next steps")).toBeInTheDocument();
    const moves = screen.getAllByRole("button", { name: /submit for approval/i });
    expect(moves).toHaveLength(2);
    // Each copy names its own blocker; one shared id would describe both
    // buttons with whichever element came first.
    const described = moves.map((b) => b.getAttribute("aria-describedby"));
    expect(new Set(described).size).toBe(2);
    for (const id of described)
      expect(document.getElementById(id as string)).not.toBeNull();

  });
});

describe("attaching purposes to a notice", () => {
  function serve(attached: ReturnType<typeof makePurpose>[]) {
    server.use(
      http.get(`${API}/notices/${NOTICE}/purposes`, () =>
        HttpResponse.json(
          attached.map((p) => ({ ...p, is_mandatory: false, display_order: 0 })),
        ),
      ),
      http.get(`${API}/purposes`, () =>
        HttpResponse.json({
          items: [
            makePurpose({
              purpose_uuid: "aaaaaaaa-0000-4000-8000-000000000001",
              name: "Gait model training",
              purpose_code: "PUR-GAIT",
            }),
            makePurpose({
              purpose_uuid: "aaaaaaaa-0000-4000-8000-000000000002",
              name: "Study communications",
              purpose_code: "PUR-CONTACT",
            }),
          ],
          next_cursor: null,
          total: 2,
        }),
      ),
    );
  }

  it("has one action, Attach, and no Done", async () => {
    serve([]);
    render(<NoticePurposesForm noticeUuid={NOTICE} />);
    await screen.findByRole("option", { name: /Gait model training/ });

    expect(screen.getAllByRole("button", { name: "Attach" })).toHaveLength(1);
    expect(screen.queryByRole("button", { name: "Done" })).not.toBeInTheDocument();
    // Nothing chosen yet, nothing to attach.
    expect(screen.getByRole("button", { name: "Attach" })).toBeDisabled();
  });

  it("attaches the chosen purpose and stays open for the next", async () => {
    serve([]);
    let posted: unknown = null;
    server.use(
      http.post(`${API}/notices/${NOTICE}/purposes`, async ({ request }) => {
        posted = await request.json();
        return HttpResponse.json({ ok: true }, { status: 201 });
      }),
    );
    const { user } = render(<NoticePurposesForm noticeUuid={NOTICE} />);
    await screen.findByRole("option", { name: /Gait model training/ });

    await user.selectOptions(
      screen.getByLabelText(/Attach a purpose/),
      "aaaaaaaa-0000-4000-8000-000000000001",
    );
    await user.click(screen.getByRole("button", { name: "Attach" }));

    expect(posted).toMatchObject({ purpose_uuid: "aaaaaaaa-0000-4000-8000-000000000001" });
    // Still here, ready for another: the choice is cleared, not the dialog.
    const box = screen.getByLabelText(/Attach a purpose/);
    expect(box).toHaveValue("");
    expect(
      within(box).getByRole("option", { name: /Study communications/ }),
    ).toBeInTheDocument();
  });
});
