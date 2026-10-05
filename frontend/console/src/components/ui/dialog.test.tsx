/**
 * A dialog with unsaved typing does not vanish on Escape (UX review 2026-10-05).
 *
 * Register project, type a name, press Escape: the dialog closed and the name
 * was gone. A dialog somebody has typed in now asks first - Keep editing, or
 * Discard changes - when it is dismissed by Escape, a click outside or its
 * close button. One that nobody has typed in closes as before, and a form's
 * own Cancel or a successful save closes it without asking.
 */
import * as React from "react";
import { describe, expect, it } from "vitest";

import { Dialog, DialogContent } from "@/components/ui/dialog";
import { render, screen } from "@/test/render";

function Harness() {
  const [open, setOpen] = React.useState(true);
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent title="Register a project">
        <label>
          Project name
          <input />
        </label>
      </DialogContent>
    </Dialog>
  );
}

describe("DialogContent", () => {
  it("closes on Escape when nothing has been typed", async () => {
    const { user } = render(<Harness />);
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("asks before throwing typing away, and keeps it if asked to", async () => {
    const { user } = render(<Harness />);
    await user.type(screen.getByLabelText("Project name"), "Gait 2026");
    await user.keyboard("{Escape}");

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText(/not saved/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Keep editing" }));
    expect(screen.getByLabelText("Project name")).toHaveValue("Gait 2026");

    await user.click(screen.getByRole("button", { name: "Close" }));
    await user.click(screen.getByRole("button", { name: "Discard changes" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
