/**
 * A dialog with unsaved typing does not vanish on Escape (UX review 2026-10-05).
 *
 * Register project, type a name, press Escape: the dialog closed and the name
 * was gone. A dialog somebody has typed in now asks first - Keep editing, or
 * Discard changes - when it is dismissed by Escape, a click outside or its
 * close button. One that nobody has typed in closes as before, and a form's
 * own Cancel or a successful save closes it without asking.
 *
 * A dialog that saves and stays open - a message sent on a ticket's thread -
 * is clean again after the save: closing it asked about a message already
 * sent (2026-10-06). Typing after the save makes it ask again.
 *
 * A form answers for its own typing (2026-11-12): a respondent added, a
 * ticket sent back, and the window still said "changes that are not saved"
 * on the way out, because those forms never said they were done. Each now
 * does, naming itself, so one form finishing does not answer for another's
 * half-typed words. A step of a wizard going off screen says nothing, and
 * its typing is still asked about.
 */
import * as React from "react";
import { describe, expect, it } from "vitest";

import {
  Dialog,
  DialogContent,
  useDialogHold,
  useDialogPart,
  useDialogSaved,
} from "@/components/ui/dialog";
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

  it("does not ask about a message already sent, and asks again once typed in", async () => {
    // A composer that saves and stays open, as a ticket's reply box does.
    function Composer() {
      const [body, setBody] = React.useState("");
      const saved = useDialogSaved();
      return (
        <form
          method="post"
          onSubmit={(e) => {
            e.preventDefault();
            setBody("");
            saved();
          }}
        >
          <label>
            Message
            <textarea value={body} onChange={(e) => setBody(e.target.value)} />
          </label>
          <button type="submit">Send</button>
        </form>
      );
    }
    function Thread() {
      const [open, setOpen] = React.useState(true);
      return (
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogContent title="Breach ticket">
            <Composer />
          </DialogContent>
        </Dialog>
      );
    }
    const { user } = render(<Thread />);
    const box = screen.getByLabelText("Message");
    await user.type(box, "Exported the log");
    await user.click(screen.getByRole("button", { name: "Send" }));

    await user.type(box, "One more");
    await user.keyboard("{Escape}");
    expect(screen.getByText(/not saved/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Keep editing" }));

    await user.click(screen.getByRole("button", { name: "Send" }));
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
  it("lets a form answer for its own typing and nobody else's", async () => {
    // A ticket: a reason being typed to send it back, and a message beside it.
    function Reason({ onDone }: { onDone: () => void }) {
      const { part, done } = useDialogPart();
      return (
        <form
          {...part}
          method="post"
          onSubmit={(e) => {
            e.preventDefault();
            done();
            onDone();
          }}
        >
          <label>
            What is missing
            <textarea />
          </label>
          <button type="submit">Send it back</button>
        </form>
      );
    }
    function Ticket() {
      const [open, setOpen] = React.useState(true);
      const [acting, setActing] = React.useState(true);
      return (
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogContent title="Ticket">
            {acting ? <Reason onDone={() => setActing(false)} /> : <p>Sent back</p>}
            <label>
              Message
              <textarea />
            </label>
          </DialogContent>
        </Dialog>
      );
    }
    const { user } = render(<Ticket />);
    await user.type(screen.getByLabelText("What is missing"), "The export is missing");
    await user.click(screen.getByRole("button", { name: "Send it back" }));
    expect(screen.getByText("Sent back")).toBeInTheDocument();

    // The reason was sent: nothing left to ask about.
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("still asks about a message half-typed beside a form that finished", async () => {
    function Reason() {
      const { part, done } = useDialogPart();
      return (
        <form
          {...part}
          method="post"
          onSubmit={(e) => {
            e.preventDefault();
            done();
          }}
        >
          <label>
            What is missing
            <textarea />
          </label>
          <button type="submit">Send it back</button>
        </form>
      );
    }
    function Ticket() {
      const [open, setOpen] = React.useState(true);
      return (
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogContent title="Ticket">
            <Reason />
            <label>
              Message
              <textarea />
            </label>
          </DialogContent>
        </Dialog>
      );
    }
    const { user } = render(<Ticket />);
    await user.type(screen.getByLabelText("Message"), "Before you answer");
    await user.type(screen.getByLabelText("What is missing"), "The export");
    await user.click(screen.getByRole("button", { name: "Send it back" }));

    await user.keyboard("{Escape}");
    expect(screen.getByText(/not saved/i)).toBeInTheDocument();
  });

  it("asks about a wizard's earlier step once it is off screen", async () => {
    // The name lives on in the wizard, not in a field: gone from the screen
    // is not saved.
    function Wizard() {
      const [open, setOpen] = React.useState(true);
      const [step, setStep] = React.useState(1);
      const [name, setName] = React.useState("");
      return (
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogContent title="New activity">
            {step === 1 ? (
              <label>
                Name
                <input value={name} onChange={(e) => setName(e.target.value)} />
              </label>
            ) : (
              <p>Review: {name}</p>
            )}
            <button type="button" onClick={() => setStep(2)}>
              Next
            </button>
          </DialogContent>
        </Dialog>
      );
    }
    const { user } = render(<Wizard />);
    await user.type(screen.getByLabelText("Name"), "CSR day");
    await user.click(screen.getByRole("button", { name: "Next" }));
    await user.keyboard("{Escape}");
    expect(screen.getByText(/not saved/i)).toBeInTheDocument();
  });
  it("asks in the content's own words before losing what was not typed", async () => {
    // A consent link shown once: nothing typed, and closing loses it.
    function Minted() {
      const [copied, setCopied] = React.useState(false);
      useDialogHold(copied ? null : "This link is shown only once.");
      return (
        <button type="button" onClick={() => setCopied(true)}>
          Copy link
        </button>
      );
    }
    function Link() {
      const [open, setOpen] = React.useState(true);
      return (
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogContent title="Consent link">
            <Minted />
          </DialogContent>
        </Dialog>
      );
    }
    const { user } = render(<Link />);
    await user.keyboard("{Escape}");
    expect(screen.getByRole("alert")).toHaveTextContent("This link is shown only once.");
    expect(screen.queryByText(/not saved/i)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Stay" }));

    // Copied: nothing left to lose.
    await user.click(screen.getByRole("button", { name: "Copy link" }));
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
