/**
 * Asking first (2026-11-12): the pop-up a handler raises before something is
 * sent outside or ended for good. Yes runs the act, Cancel and Escape do not,
 * and a second question answers the first with no.
 */
import { describe, expect, it, vi } from "vitest";

import { Button } from "@/components/ui/primitives";
import { useConfirm } from "@/components/ui/confirm";
import { render, screen, within } from "@/test/render";

function Sender({ onSend }: { onSend: (what: string) => void }) {
  const confirm = useConfirm();
  async function send(what: string) {
    if (
      !(await confirm.ask({
        title: `Send the ${what}?`,
        consequence: `The ${what} is emailed to the requester.`,
        confirmLabel: `Send the ${what}`,
      }))
    )
      return;
    onSend(what);
  }
  return (
    <>
      <Button onClick={() => send("response")}>Release</Button>
      <Button onClick={() => send("code")}>Code</Button>
      {confirm.dialog}
    </>
  );
}

describe("useConfirm", () => {
  it("does nothing until the question is answered yes, with the verb on the button", async () => {
    const onSend = vi.fn();
    const { user } = render(<Sender onSend={onSend} />);

    await user.click(screen.getByRole("button", { name: "Release" }));
    const dialog = await screen.findByRole("dialog", { name: "Send the response?" });
    expect(within(dialog).getByText("The response is emailed to the requester.")).toBeInTheDocument();
    expect(onSend).not.toHaveBeenCalled();

    await user.click(within(dialog).getByRole("button", { name: "Send the response" }));
    await vi.waitFor(() => expect(onSend).toHaveBeenCalledWith("response"));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("takes Cancel and Escape for a no", async () => {
    const onSend = vi.fn();
    const { user } = render(<Sender onSend={onSend} />);

    await user.click(screen.getByRole("button", { name: "Release" }));
    await user.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "Cancel" }));
    await vi.waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: "Release" }));
    await screen.findByRole("dialog");
    await user.keyboard("{Escape}");
    await vi.waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(onSend).not.toHaveBeenCalled();
  });
});
