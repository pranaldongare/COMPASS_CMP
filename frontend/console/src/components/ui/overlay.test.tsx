/**
 * The row menu and truncation (2026-10-10): every row action behind one ⋯,
 * destructive ones last and red, links as links.
 */
import { describe, expect, it, vi } from "vitest";

import { RowActions, Truncate } from "@/components/ui/overlay";
import { render, screen } from "@/test/render";

describe("RowActions", () => {
  it("opens a menu of the row's actions, links as links and the risky one last", async () => {
    const edit = vi.fn();
    const suspend = vi.fn();
    const { user } = render(
      <RowActions
        label="Actions for Gait rig"
        actions={[
          { label: "Suspend", destructive: true, onSelect: suspend },
          { label: "View", href: "/sources/1" },
          { label: "Edit", onSelect: edit },
        ]}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Actions for Gait rig" }));
    const items = await screen.findAllByRole("menuitem");
    expect(items.map((i) => i.textContent)).toEqual(["View", "Edit", "Suspend"]);
    expect(items[0]).toHaveAttribute("href", "/sources/1");

    await user.click(screen.getByRole("menuitem", { name: "Edit" }));
    expect(edit).toHaveBeenCalledTimes(1);
    expect(suspend).not.toHaveBeenCalled();
  });

  it("renders nothing when a row has nothing to do", () => {
    const { container } = render(<RowActions label="Actions" actions={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe("Truncate", () => {
  it("keeps the whole text in the page for screen readers", () => {
    render(<Truncate>Singapore Annotation Partners Pte Ltd</Truncate>);
    expect(screen.getByText("Singapore Annotation Partners Pte Ltd")).toHaveClass("truncate");
  });
});
