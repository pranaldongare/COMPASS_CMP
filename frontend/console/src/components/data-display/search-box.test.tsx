/**
 * The list search.
 *
 * What it owes a list: one search per pause in the typing (never one per
 * keystroke), Enter and × at once, nothing resent that is already in force -
 * each search resets the list's pagination - and a box that follows the search
 * when it is cleared from somewhere else.
 */

import * as React from "react";
import { describe, expect, it, vi } from "vitest";

import { SearchBox } from "@/components/data-display/resource-list";
import { render, screen, waitFor } from "@/test/render";

describe("SearchBox", () => {
  it("searches once when the typing pauses, not on every key", async () => {
    const onSubmit = vi.fn();
    const { user } = render(<SearchBox placeholder="Name or code" onSubmit={onSubmit} />);

    await user.type(screen.getByPlaceholderText("Name or code"), "CIT");

    await waitFor(() => expect(onSubmit).toHaveBeenCalledWith("CIT"));
    expect(onSubmit).toHaveBeenCalledOnce();
  });

  it("searches at once on Enter, and does not search the same term again after the pause", async () => {
    const onSubmit = vi.fn();
    const { user } = render(<SearchBox placeholder="Name or code" onSubmit={onSubmit} />);

    await user.type(screen.getByPlaceholderText("Name or code"), "SEED{Enter}");
    expect(onSubmit).toHaveBeenCalledWith("SEED");

    await new Promise((r) => setTimeout(r, 450));
    expect(onSubmit).toHaveBeenCalledOnce();
  });

  it("empties with the clear button and searches for everything", async () => {
    const onSubmit = vi.fn();
    const { user } = render(
      <SearchBox value="CIT" placeholder="Name or code" onSubmit={onSubmit} />,
    );
    const box = screen.getByPlaceholderText("Name or code");
    expect(box).toHaveValue("CIT");

    await user.click(screen.getByRole("button", { name: "Clear search" }));

    expect(box).toHaveValue("");
    expect(box).toHaveFocus();
    expect(onSubmit).toHaveBeenCalledWith("");
    expect(screen.queryByRole("button", { name: "Clear search" })).not.toBeInTheDocument();
  });

  it("follows the search in force when it is cleared elsewhere", async () => {
    const onSubmit = vi.fn();
    function Page() {
      const [q, setQ] = React.useState("SRIB");
      return (
        <>
          <SearchBox
            value={q}
            placeholder="Name or code"
            onSubmit={(term) => {
              onSubmit(term);
              setQ(term);
            }}
          />
          <button onClick={() => setQ("")}>Remove the search chip</button>
        </>
      );
    }
    const { user } = render(<Page />);
    expect(screen.getByPlaceholderText("Name or code")).toHaveValue("SRIB");

    await user.click(screen.getByRole("button", { name: "Remove the search chip" }));

    expect(screen.getByPlaceholderText("Name or code")).toHaveValue("");
    await new Promise((r) => setTimeout(r, 450));
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("with instant off, waits for Enter or the button", async () => {
    const onSubmit = vi.fn();
    const { user } = render(
      <SearchBox instant={false} placeholder="Whole email" onSubmit={onSubmit} />,
    );

    await user.type(screen.getByPlaceholderText("Whole email"), "asha@");
    await new Promise((r) => setTimeout(r, 450));
    expect(onSubmit).not.toHaveBeenCalled();

    await user.type(screen.getByPlaceholderText("Whole email"), "example.org");
    await user.click(screen.getByRole("button", { name: "Search" }));
    expect(onSubmit).toHaveBeenCalledWith("asha@example.org");
  });
});
