/**
 * Compact filters (2026-10-10): the label inside the control and still its
 * accessible name; a filter that is set reads as set.
 */
import { describe, expect, it, vi } from "vitest";

import { FilterDate, FilterSelect, FilterToggle } from "@/components/data-display/resource-list";
import { render, screen } from "@/test/render";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => "/",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

const OPTIONS = [
  { value: "open", label: "Open" },
  { value: "closed", label: "Closed" },
];

describe("compact filters", () => {
  it("names the select by its inside label and marks it once set", async () => {
    const onChange = vi.fn();
    const { rerender, user } = render(
      <FilterSelect label="Status" value="" onChange={onChange} options={OPTIONS} allLabel="All statuses" />,
    );
    const select = screen.getByLabelText("Status");
    expect(select.parentElement).not.toHaveClass("bg-accent-subtle");
    await user.selectOptions(select, "closed");
    expect(onChange).toHaveBeenCalledWith("closed");

    rerender(
      <FilterSelect label="Status" value="closed" onChange={onChange} options={OPTIONS} allLabel="All statuses" />,
    );
    expect(screen.getByLabelText("Status").parentElement).toHaveClass("bg-accent-subtle");
  });

  it("offers no 'all' choice when told not to, and reads as set off its first option", () => {
    render(<FilterSelect label="Show" value="closed" onChange={() => {}} options={OPTIONS} allLabel={null} />);
    expect(screen.getAllByRole("option").map((o) => o.textContent)).toEqual(["Open", "Closed"]);
    expect(screen.getByLabelText("Show").parentElement).toHaveClass("bg-accent-subtle");
  });

  it("dates and toggles carry their labels too", async () => {
    const onDate = vi.fn();
    const onToggle = vi.fn();
    const { user } = render(
      <>
        <FilterDate label="Given from" value="" onChange={onDate} />
        <FilterToggle label="Nobody accountable" checked={false} onChange={onToggle} />
      </>,
    );
    await user.type(screen.getByLabelText("Given from"), "2026-10-01");
    expect(onDate).toHaveBeenLastCalledWith("2026-10-01");
    await user.click(screen.getByLabelText("Nobody accountable"));
    expect(onToggle).toHaveBeenCalledWith(true);
  });
});
