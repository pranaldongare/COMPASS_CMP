/**
 * Breach settings (0058): the link to give out, who is told of a report, and
 * the organisation's board. The two officers are always told, whatever is
 * chosen; an empty board list says what it holds up.
 */
import { HttpResponse, http } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import BreachSettingsPage from "@/app/(app)/breach-settings/page";
import { render, screen, within } from "@/test/render";
import { API, server } from "@/test/server";
import type { BreachSettings } from "@/types";

const toast = vi.hoisted(() => ({ success: vi.fn(), error: vi.fn(), warning: vi.fn() }));
vi.mock("@/providers", () => ({ useToast: () => toast }));

const RECIPIENT = "77777777-7777-4777-8777-777777777777";

const person = {
  recipient_uuid: RECIPIENT,
  full_name: "Meera Iyer",
  email: "meera@cmp.local",
  added_at: "2026-11-06T09:00:00Z",
  added_by_name: "Priya Menon",
};

const settings = (over: Partial<BreachSettings> = {}): BreachSettings => ({
  intake_roles: ["dpo", "legal"],
  roles: [
    { role: "dpo", title: "DPO" },
    { role: "legal", title: "Legal PoC" },
    { role: "admin", title: "Administrator" },
  ],
  officers: ["dpo", "legal"],
  board_recipients: [person],
  report_link: "https://portal.cmp.local/report-incident",
  ...over,
});

function serve(found: BreachSettings) {
  server.use(http.get(`${API}/breach-settings`, () => HttpResponse.json(found)));
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("Breach settings", () => {
  it("gives the public link to copy", async () => {
    serve(settings());
    render(<BreachSettingsPage />);

    expect(await screen.findByText("https://portal.cmp.local/report-incident")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Copy" })).toBeInTheDocument();
  });

  it("keeps the two officers ticked, whatever is chosen", async () => {
    serve(settings({ intake_roles: [] }));
    render(<BreachSettingsPage />);

    for (const name of ["DPO", "Legal PoC"]) {
      const box = await screen.findByRole("checkbox", { name });
      expect(box).toBeChecked();
      expect(box).toBeDisabled();
    }
    expect(screen.getByRole("checkbox", { name: "Administrator" })).not.toBeChecked();
    expect(screen.getByRole("checkbox", { name: "Administrator" })).toBeEnabled();
  });

  it("adds a role to those told", async () => {
    let sent: unknown = null;
    serve(settings());
    server.use(
      http.put(`${API}/breach-settings/intake-roles`, async ({ request }) => {
        sent = await request.json();
        return HttpResponse.json(settings({ intake_roles: ["dpo", "legal", "admin"] }));
      }),
    );
    const { user } = render(<BreachSettingsPage />);

    await user.click(await screen.findByRole("checkbox", { name: "Administrator" }));

    await vi.waitFor(() => expect(sent).toEqual({ roles: ["dpo", "legal", "admin"] }));
    await vi.waitFor(() => expect(screen.getByRole("checkbox", { name: "Administrator" })).toBeChecked());
  });

  it("adds a board address, and takes the fields back to empty", async () => {
    let sent: unknown = null;
    const added = { ...person, recipient_uuid: crypto.randomUUID(), full_name: null, email: "chair@cmp.local" };
    serve(settings());
    server.use(
      http.post(`${API}/breach-settings/board-recipients`, async ({ request }) => {
        sent = await request.json();
        return HttpResponse.json(settings({ board_recipients: [person, added] }));
      }),
    );
    const { user } = render(<BreachSettingsPage />);

    await screen.findByText("meera@cmp.local");
    const add = screen.getByRole("button", { name: "Add" });
    expect(add).toBeDisabled();
    await user.type(screen.getByLabelText(/^Mail ID/), "chair@cmp.local");
    await user.click(add);

    await vi.waitFor(() => expect(sent).toEqual({ full_name: null, email: "chair@cmp.local" }));
    const row = (await screen.findByText("chair@cmp.local")).closest("tr") as HTMLElement;
    expect(within(row).getByText("No name")).toBeInTheDocument();
    expect(screen.getByLabelText(/^Mail ID/)).toHaveValue("");
  });

  it("says when the server refuses an address, and keeps what was typed", async () => {
    serve(settings());
    server.use(
      http.post(`${API}/breach-settings/board-recipients`, () =>
        HttpResponse.json(
          { error: { code: "validation_failed", message: "That is not an email address" } },
          { status: 422 },
        ),
      ),
    );
    const { user } = render(<BreachSettingsPage />);

    await screen.findByText("meera@cmp.local");
    await user.type(screen.getByLabelText(/^Mail ID/), "chair@cmp");
    await user.click(screen.getByRole("button", { name: "Add" }));

    await vi.waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith("Not added", "That is not an email address"),
    );
    expect(screen.getByLabelText(/^Mail ID/)).toHaveValue("chair@cmp");
  });

  it("removes a board address, and says what an empty list holds up", async () => {
    let removed = false;
    serve(settings());
    server.use(
      http.delete(`${API}/breach-settings/board-recipients/${RECIPIENT}`, () => {
        removed = true;
        return HttpResponse.json(settings({ board_recipients: [] }));
      }),
    );
    const { user } = render(<BreachSettingsPage />);

    await user.click(await screen.findByRole("button", { name: "Remove meera@cmp.local" }));

    await vi.waitFor(() => expect(removed).toBe(true));
    expect(await screen.findByText("Nobody is on the list")).toBeInTheDocument();
    expect(screen.queryByText("meera@cmp.local")).not.toBeInTheDocument();
  });

  it("keeps the hidden Remove heading inside the table, or the page scrolls sideways on a phone", async () => {
    serve(settings());
    render(<BreachSettingsPage />);

    expect(await screen.findByRole("columnheader", { name: "Remove" })).toHaveClass("relative");
  });
});
