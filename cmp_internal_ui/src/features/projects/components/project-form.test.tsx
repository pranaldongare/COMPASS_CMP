/**
 * The project form submits in both of its modes.
 *
 * Written for a bug an R&D User reported: pressing "Save changes" on a draft
 * project did nothing at all. No request, no toast, no error text, and the
 * dialog stayed open.
 *
 * The cause was the same shape as the one `approval-form.test.tsx` was written
 * about. `projectSchema` required at least one processor, the edit mode seeded
 * `processor_uuids` as `[]`, and the checkboxes that would have filled it are
 * rendered only when registering — so `handleSubmit` validated an empty array
 * against `min(1)`, failed, and returned. The message for that field lives
 * inside the same block as the checkboxes, so in edit mode even the error was
 * invisible.
 *
 * A silent no-op is the worst failure a form can have, and it is invisible to
 * every test that only exercises the happy path of the other mode. So both
 * modes are asserted here, bluntly: fill it in, submit, and check that the
 * request happened and `onDone` was called.
 */

import { describe, expect, it, vi } from "vitest";

import { ProjectForm } from "@/features/projects/components/project-form";
import { render, screen, waitFor } from "@/test/render";
import { API, HttpResponse, http, server } from "@/test/server";
import type { Project } from "@/types";

vi.mock("@/providers", async () => {
  const actual = await vi.importActual<Record<string, unknown>>("@/providers");
  return {
    ...actual,
    useToast: () => ({
      success: vi.fn(),
      error: vi.fn(),
      info: vi.fn(),
      warning: vi.fn(),
    }),
  };
});

const PROJECT_UUID = "33333333-3333-4333-8333-333333333333";
const PROCESSOR_UUID = "44444444-4444-4444-8444-444444444444";

const DRAFT: Project = {
  project_uuid: PROJECT_UUID,
  project_name: "Gait Identification Study 2026",
  internal_project_name: "GAIT-2026",
  description: "Collection of gait video for model training.",
  requesting_team: "Computer Vision",
  project_status: "in_draft",
  dco_uuid: null,
  dco_name: null,
  created_by_name: "Kavya Rao",
  current_notice_uuid: null,
  created_at: "2026-09-01T10:00:00Z",
  updated_at: "2026-09-01T10:00:00Z",
};

/** The processor list the "who will collect" checkboxes are built from. */
function withProcessors() {
  server.use(
    http.get(`${API}/processors`, () =>
      HttpResponse.json({
        items: [
          {
            processor_uuid: PROCESSOR_UUID,
            legal_name: "SEED Labs",
            is_in_house: false,
            status: "active",
          },
        ],
        total: 1,
      }),
    ),
  );
}

describe("editing a draft", () => {
  it("saves and closes, without asking who collects", async () => {
    let sent: unknown = null;
    server.use(
      http.put(`${API}/projects/:uuid`, async ({ request }) => {
        sent = await request.json();
        return HttpResponse.json({ ...DRAFT, project_name: "Renamed" });
      }),
    );

    const onDone = vi.fn();
    const { user } = render(<ProjectForm project={DRAFT} onDone={onDone} />);

    const name = screen.getByLabelText(/project name/i);
    await user.clear(name);
    await user.type(name, "Renamed");
    await user.click(screen.getByRole("button", { name: /save changes/i }));

    await waitFor(() => expect(onDone).toHaveBeenCalled());
    expect(sent).toMatchObject({ project_name: "Renamed" });
  });

  it("offers no collector field at all", () => {
    render(<ProjectForm project={DRAFT} onDone={vi.fn()} />);

    expect(screen.queryByText(/who will collect/i)).not.toBeInTheDocument();
  });
});

describe("registering one", () => {
  it("still refuses a project with nobody named to collect, and says so", async () => {
    withProcessors();
    let called = false;
    server.use(
      http.post(`${API}/projects`, () => {
        called = true;
        return HttpResponse.json(DRAFT, { status: 201 });
      }),
    );

    const { user } = render(<ProjectForm onDone={vi.fn()} />);
    await user.type(screen.getByLabelText(/project name/i), "A new study");
    await user.type(screen.getByLabelText(/^description/i), "What it collects and why.");
    await user.click(screen.getByRole("button", { name: /register project/i }));

    await waitFor(() =>
      expect(screen.getByText(/choose at least one processor/i)).toBeInTheDocument(),
    );
    expect(called).toBe(false);
  });

  it("registers and closes once somebody is named", async () => {
    withProcessors();
    server.use(
      http.post(`${API}/projects`, () => HttpResponse.json(DRAFT, { status: 201 })),
    );

    const onDone = vi.fn();
    const { user } = render(<ProjectForm onDone={onDone} />);
    await user.type(screen.getByLabelText(/project name/i), "A new study");
    await user.type(screen.getByLabelText(/^description/i), "What it collects and why.");
    await waitFor(() => expect(screen.getByText(/SEED Labs/)).toBeInTheDocument());
    await user.click(screen.getByRole("checkbox"));
    await user.click(screen.getByRole("button", { name: /register project/i }));

    await waitFor(() => expect(onDone).toHaveBeenCalled());
  });
});
