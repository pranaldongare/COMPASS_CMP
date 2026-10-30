/**
 * A Legal office template's versions (0053): the list, a draft with its
 * slots checked as it is written, Approve behind a confirmation, and an
 * approved version shown read-only with its hash.
 */
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";

import {
  CurrentText,
  VersionsPanel,
} from "@/features/notice-templates/components/versions-panel";
import { makePurpose } from "@/test/fixtures";
import { makeTemplate } from "@/test/notice-templates";
import { render, screen, within } from "@/test/render";
import { API, server } from "@/test/server";
import type { TemplateVersionDetail } from "@/types";

vi.mock("@/providers", () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn(), warning: vi.fn() }),
}));

const TEMPLATE = makeTemplate({ office_code: "hr", category_code: "WELLNESS", version_count: 2 });
const BASE = `${API}/notice-templates/${TEMPLATE.template_uuid}/versions`;

function version(over: Partial<TemplateVersionDetail> = {}): TemplateVersionDetail {
  return {
    version_uuid: "a1a1a1a1-a1a1-41a1-81a1-a1a1a1a1a1a1",
    version: 1,
    status: "approved",
    reconsent_required: false,
    slot_guidance: "Say what the sessions are and when.",
    slot_max_length: 600,
    withdraw_url: "https://example.org/withdraw",
    exercise_rights_url: "https://example.org/rights",
    board_complaint_url: "https://example.org/board",
    dpo_contact: "legal@example.org",
    applicable_to: "employee",
    template_uuid: TEMPLATE.template_uuid,
    template_code: TEMPLATE.template_code,
    template_title: TEMPLATE.title,
    category_uuid: null,
    category_code: "WELLNESS",
    created_by_name: "Meera Nair",
    created_at: "2026-10-28T09:00:00Z",
    updated_at: "2026-10-28T09:00:00Z",
    approved_by_name: "Meera Nair",
    approved_at: "2026-10-28T10:00:00Z",
    retired_at: null,
    language_count: 1,
    purpose_count: 1,
    activity_count: 3,
    languages: [
      {
        language_code: "english",
        locked_text: "For:\n{{purposes}}\nAbout: {{description}}",
        content_hash: "0123456789abcdef0123456789abcdef",
        updated_at: "2026-10-28T09:00:00Z",
        updated_by_name: "Meera Nair",
      },
    ],
    purposes: [
      {
        ...makePurpose({ name: "Wellness sessions" }),
        is_mandatory: true,
        display_order: 0,
      },
    ],
    ...over,
  };
}

const DRAFT = version({
  version_uuid: "b2b2b2b2-b2b2-42b2-82b2-b2b2b2b2b2b2",
  version: 2,
  status: "draft",
  approved_by_name: null,
  approved_at: null,
  activity_count: 0,
  languages: [
    {
      language_code: "english",
      locked_text: "For:\n{{purposes}}\nNo description slot yet.",
      content_hash: null,
      updated_at: "2026-10-28T11:00:00Z",
      updated_by_name: "Meera Nair",
    },
  ],
});

function serve() {
  server.use(
    http.get(BASE, () => HttpResponse.json([DRAFT, version()])),
    http.get(`${BASE}/2`, () => HttpResponse.json(DRAFT)),
    http.get(`${BASE}/1`, () => HttpResponse.json(version())),
    http.get(`${API}/purposes`, () =>
      HttpResponse.json({ items: [], next_cursor: null, total: 0 }),
    ),
  );
}

describe("VersionsPanel", () => {
  it("lists the versions and opens the newest, a draft, with its slots checked", async () => {
    serve();
    render(<VersionsPanel template={TEMPLATE} canWrite />);
    expect(await screen.findByRole("heading", { name: "Version 2" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "v1" })).toBeInTheDocument();
    // One slot is there, the other is not, and the editor says which.
    expect(await screen.findByText(/missing/)).toBeInTheDocument();
    expect(screen.getAllByText(/once/).length).toBeGreaterThan(0);
    // One draft at a time: no Open button while version 2 is a draft.
    expect(screen.queryByRole("button", { name: /Open version/ })).not.toBeInTheDocument();
  });

  it("asks before approving", async () => {
    serve();
    const { user } = render(<VersionsPanel template={TEMPLATE} canWrite />);
    await user.click(await screen.findByRole("button", { name: "Approve" }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText(/frozen and hashed/)).toBeInTheDocument();
  });

  it("shows an approved version read-only, with its hash", async () => {
    serve();
    const { user } = render(<VersionsPanel template={TEMPLATE} canWrite />);
    await user.click(await screen.findByRole("button", { name: "v1" }));
    expect(await screen.findByRole("heading", { name: "Version 1" })).toBeInTheDocument();
    expect(screen.getByText(/0123456789abcdef/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Save text" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retire" })).toBeInTheDocument();
  });

  it("offers nothing to change to a reader", async () => {
    serve();
    render(<VersionsPanel template={TEMPLATE} canWrite={false} />);
    expect(await screen.findByRole("heading", { name: "Version 2" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Save text" })).not.toBeInTheDocument();
  });
});

describe("CurrentText", () => {
  it("shows the approved version's text, not the newer draft's", async () => {
    serve();
    const onVersions = vi.fn();
    const { user } = render(<CurrentText template={TEMPLATE} onVersions={onVersions} />);
    expect(await screen.findByText(/About: \{\{description\}\}/)).toBeInTheDocument();
    expect(screen.getByText("Version 1.")).toBeInTheDocument();
    expect(screen.queryByText(/No description slot yet/)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "All versions" }));
    expect(onVersions).toHaveBeenCalled();
  });

  it("before version 1, shows the text written with the template", async () => {
    server.use(http.get(BASE, () => HttpResponse.json([])));
    const written = {
      ...TEMPLATE,
      version_count: 0,
      languages: [
        {
          language_code: "english" as const,
          rendered_text: "Written at creation: {{purposes}} {{description}}",
          updated_at: "2026-10-30T09:00:00Z",
          updated_by_name: "Meera Nair",
        },
      ],
    };
    render(<CurrentText template={written} onVersions={vi.fn()} />);
    expect(await screen.findByText(/Written at creation/)).toBeInTheDocument();
    expect(screen.getByText(/Version 1 starts from it/)).toBeInTheDocument();
  });
});
