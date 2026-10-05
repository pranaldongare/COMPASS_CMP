/**
 * The phone navigation drawer behaves like the modal it is (review UX-4).
 *
 * It covered the page and took no focus: a keyboard user opened it and was
 * still on the button behind it, Tab walked into the page underneath, and
 * Escape did nothing. Opening now moves focus into the drawer, Tab stays
 * inside it, Escape closes it, and closing gives focus back to the button
 * that opened it.
 */
import * as React from "react";
import { describe, expect, it } from "vitest";

import { useDrawer } from "@/components/layout/use-drawer";
import { render, screen } from "@/test/render";

function Harness() {
  const [open, setOpen] = React.useState(false);
  const panel = useDrawer(open, () => setOpen(false));
  return (
    <>
      <button type="button" onClick={() => setOpen(true)}>
        Open navigation
      </button>
      <a href="#behind">Behind the drawer</a>
      {open && (
        <nav ref={panel} aria-label="Main">
          <a href="#one">First</a>
          <a href="#two">Last</a>
        </nav>
      )}
    </>
  );
}

describe("useDrawer", () => {
  it("moves focus in, keeps it in, and gives it back", async () => {
    const { user } = render(<Harness />);
    const opener = screen.getByRole("button", { name: "Open navigation" });

    await user.click(opener);
    expect(screen.getByRole("link", { name: "First" })).toHaveFocus();

    await user.tab();
    expect(screen.getByRole("link", { name: "Last" })).toHaveFocus();
    await user.tab();
    expect(screen.getByRole("link", { name: "First" })).toHaveFocus();
    await user.tab({ shift: true });
    expect(screen.getByRole("link", { name: "Last" })).toHaveFocus();

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
    expect(opener).toHaveFocus();
  });
});
