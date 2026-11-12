/**
 * Choosing a member of staff by typing (2026-11-12).
 *
 * A search box above a drop-down - "Find them", then "Who" - asked one
 * question with two controls, and the second looked empty until the first was
 * understood. One box now: the matches are listed under it as the name is
 * typed, and a click or the arrow keys and Enter chooses one.
 */
import { HttpResponse, http } from "msw";
import * as React from "react";
import { describe, expect, it } from "vitest";

import { StaffPicker, type StaffChoice } from "@/features/users/components/staff-picker";
import { render, screen, within } from "@/test/render";
import { API, server } from "@/test/server";

const people = [
  { uuid: "a1", full_name: "Arun Shetty", email: "arun@cmp.local", role: "dco" },
  { uuid: "a2", full_name: "Aruna Rao", email: "aruna@cmp.local", role: "dpo" },
  // Not staff: nobody is assigned work through these accounts.
  { uuid: "a3", full_name: "Arun Verma", email: "arun.v@example.org", role: "data_subject" },
];

function Picker() {
  const [value, setValue] = React.useState<StaffChoice | null>(null);
  return <StaffPicker label="Assign to" value={value} onChange={setValue} />;
}

function serve(asked: string[] = []) {
  server.use(
    http.get(`${API}/users`, ({ request }) => {
      const q = new URL(request.url).searchParams.get("q") ?? "";
      asked.push(q);
      const items = people.filter((p) => p.full_name.toLowerCase().includes(q.toLowerCase()));
      return HttpResponse.json({ items, next_cursor: null, total: items.length });
    }),
  );
}

describe("StaffPicker", () => {
  it("lists nobody before three letters, then the staff who match as it is typed", async () => {
    const asked: string[] = [];
    serve(asked);
    const { user } = render(<Picker />);
    const box = screen.getByRole("combobox", { name: /assign to/i });

    await user.type(box, "Ar");
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    expect(asked).toEqual([]);

    await user.type(box, "un");
    const list = await screen.findByRole("listbox", { name: "Matching staff" });
    const options = await within(list).findAllByRole("option");
    // Staff only, each with the address that tells two people apart.
    expect(options).toHaveLength(2);
    expect(options[0]).toHaveTextContent("Arun Shetty");
    expect(options[0]).toHaveTextContent("arun@cmp.local");
    expect(options[1]).toHaveTextContent("Aruna Rao");
    expect(within(list).queryByText("Arun Verma")).not.toBeInTheDocument();
    // Asked once the typing settled, with what was typed.
    expect(asked.at(-1)).toBe("Arun");
  });

  it("chooses with a click, shows who was chosen, and lets it be changed", async () => {
    serve();
    const { user } = render(<Picker />);
    await user.type(screen.getByRole("combobox", { name: /assign to/i }), "Arun");
    await user.click(await screen.findByRole("option", { name: /Aruna Rao/ }));

    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
    expect(screen.getByText("Aruna Rao")).toBeInTheDocument();
    expect(screen.getByText("aruna@cmp.local")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /change/i }));
    expect(screen.getByRole("combobox", { name: /assign to/i })).toHaveValue("");
  });

  it("chooses with the arrow keys and Enter", async () => {
    serve();
    const { user } = render(<Picker />);
    const box = screen.getByRole("combobox", { name: /assign to/i });
    await user.type(box, "Arun");
    await screen.findByRole("option", { name: /Arun Shetty/ });
    await user.keyboard("{ArrowDown}{Enter}");
    expect(screen.getByText("Aruna Rao")).toBeInTheDocument();
  });

  it("says so when nobody matches", async () => {
    serve();
    const { user } = render(<Picker />);
    await user.type(screen.getByRole("combobox", { name: /assign to/i }), "Zed");
    expect(await screen.findByText(/No staff member matches “Zed”/)).toBeInTheDocument();
  });
});
