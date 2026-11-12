/**
 * A respondent added is saved (2026-11-12).
 *
 * The Respondents window stays open after an add, for the next one. It went
 * on saying "You have changes that are not saved" when it was closed, because
 * the form never told the window its work was done. It now does - and typing
 * a second respondent and closing before adding still asks.
 */
import { HttpResponse, http } from "msw";
import * as React from "react";
import { describe, expect, it, vi } from "vitest";

import { Dialog, DialogContent } from "@/components/ui/dialog";
import { RespondentsPanel } from "@/features/registry/components/respondents";
import { makeMe } from "@/test/fixtures";
import { render, screen, within } from "@/test/render";
import { API, server } from "@/test/server";
import type { Processor } from "@/types";

vi.mock("@/providers", () => ({
  useAuth: () => ({ me: makeMe({ role: "dpo" }) }),
  useToast: () => ({ success: vi.fn(), error: vi.fn() }),
}));

const PROC = "34343434-3434-4434-8434-343434343434";
const processor = {
  processor_uuid: PROC,
  legal_name: "Acme Labs",
  type: "data_processor",
  contract_ref: "MSA-1",
  security_confirmed_at: "2026-01-01",
  status: "active",
  is_in_house: false,
  location_country: null,
  created_at: "2026-09-01T10:00:00Z",
} as unknown as Processor;

function Window() {
  const [open, setOpen] = React.useState(true);
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent title="Respondents · Acme Labs">
        <RespondentsPanel processor={processor} />
      </DialogContent>
    </Dialog>
  );
}

describe("RespondentsPanel in its window", () => {
  it("closes without asking once the respondent is added, and asks about one not yet added", async () => {
    const added: unknown[] = [];
    server.use(
      http.get(`${API}/processors/${PROC}/respondents`, () => HttpResponse.json(added)),
      http.post(`${API}/processors/${PROC}/respondents`, async ({ request }) => {
        const body = (await request.json()) as { name: string; contact: string };
        const row = {
          respondent_uuid: `r-${added.length}`,
          name: body.name,
          contact: body.contact,
          user_uuid: null,
          user_role: null,
          created_at: "2026-11-12T10:00:00Z",
        };
        added.push(row);
        return HttpResponse.json(row);
      }),
    );
    const { user } = render(<Window />);
    const dialog = await screen.findByRole("dialog");

    await user.type(within(dialog).getByLabelText(/^name/i), "Asha Rao");
    await user.type(within(dialog).getByLabelText(/email address/i), "asha@acme.example");
    await user.click(within(dialog).getByRole("button", { name: /add respondent/i }));
    expect(await within(dialog).findByText("asha@acme.example")).toBeInTheDocument();

    // A second one typed and not added is still work to lose.
    await user.type(within(dialog).getByLabelText(/^name/i), "Ravi");
    await user.click(within(dialog).getByRole("button", { name: "Close" }));
    expect(within(dialog).getByText(/not saved/i)).toBeInTheDocument();
    await user.click(within(dialog).getByRole("button", { name: "Keep editing" }));
    await user.clear(within(dialog).getByLabelText(/^name/i));
    await user.type(within(dialog).getByLabelText(/^name/i), "Ravi Iyer");
    await user.type(within(dialog).getByLabelText(/email address/i), "ravi@acme.example");
    await user.click(within(dialog).getByRole("button", { name: /add respondent/i }));
    expect(await within(dialog).findByText("ravi@acme.example")).toBeInTheDocument();

    // Both are on the list: nothing is waiting to be saved.
    await user.click(within(dialog).getByRole("button", { name: "Close" }));
    expect(screen.queryByText(/not saved/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
