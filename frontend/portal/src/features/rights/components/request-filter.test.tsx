/**
 * Narrowing her list of requests: open or closed as the server says
 * (`closed_at`), a search across what she would remember a request by, and a
 * way back to all of them.
 */

import { describe, expect, it } from "vitest";

import {
  RequestFilter,
  useRequestFilter,
} from "@/features/rights/components/request-filter";
import { makeMyRequest } from "@/test/fixtures";
import { render, screen, within } from "@/test/render";
import type { MyRequest } from "@/types";

const requests: MyRequest[] = [
  makeMyRequest({
    request_uuid: "a",
    reference: "RR-2026-000001",
    request_type: "access",
    request_text: "Everything you hold",
    closed_at: null,
  }),
  makeMyRequest({
    request_uuid: "b",
    reference: "RR-2026-000002",
    request_type: "erasure",
    request_text: "Delete the gait video",
    closed_at: null,
  }),
  makeMyRequest({
    request_uuid: "c",
    reference: "RR-2026-000003",
    request_type: "grievance",
    request_text: "Late answer",
    closed_at: "2026-09-20T10:00:00Z",
  }),
];

function Harness() {
  const filter = useRequestFilter(requests);
  return (
    <>
      <RequestFilter filter={filter} />
      <ul aria-label="Shown">
        {filter.shown.map((r) => (
          <li key={r.request_uuid}>{r.reference}</li>
        ))}
      </ul>
      <button onClick={filter.reset}>Reset</button>
    </>
  );
}

function shown(): string[] {
  return within(screen.getByRole("list", { name: "Shown" }))
    .queryAllByRole("listitem")
    .map((li) => li.textContent ?? "");
}

describe("RequestFilter", () => {
  it("counts open, closed and all from closed_at", () => {
    render(<Harness />);
    expect(screen.getByRole("radio", { name: /Open/ }).closest("label")).toHaveTextContent(
      "Open2",
    );
    expect(
      screen.getByRole("radio", { name: /Closed/ }).closest("label"),
    ).toHaveTextContent("Closed1");
    expect(screen.getByRole("radio", { name: /All/ })).toBeChecked();
    expect(shown()).toHaveLength(3);
  });

  it("shows only open or only closed requests", async () => {
    const { user } = render(<Harness />);

    await user.click(screen.getByRole("radio", { name: /Open/ }));
    expect(shown()).toEqual(["RR-2026-000001", "RR-2026-000002"]);

    await user.click(screen.getByRole("radio", { name: /Closed/ }));
    expect(shown()).toEqual(["RR-2026-000003"]);
  });

  it("finds a request by its reference, its kind or its words", async () => {
    const { user } = render(<Harness />);
    const box = screen.getByRole("searchbox", { name: "Search your requests" });

    await user.type(box, "000002");
    expect(shown()).toEqual(["RR-2026-000002"]);

    await user.clear(box);
    await user.type(box, "grievance");
    expect(shown()).toEqual(["RR-2026-000003"]);

    await user.clear(box);
    await user.type(box, "gait video");
    expect(shown()).toEqual(["RR-2026-000002"]);
  });

  it("clears the search with the button and with Escape", async () => {
    const { user } = render(<Harness />);
    const box = screen.getByRole("searchbox", { name: "Search your requests" });

    await user.type(box, "nothing like this");
    expect(shown()).toEqual([]);
    await user.click(screen.getByRole("button", { name: "Clear search" }));
    expect(box).toHaveValue("");
    expect(shown()).toHaveLength(3);

    await user.type(box, "late{Escape}");
    expect(box).toHaveValue("");
  });

  it("resets to every request", async () => {
    const { user } = render(<Harness />);
    await user.click(screen.getByRole("radio", { name: /Closed/ }));
    await user.type(screen.getByRole("searchbox"), "late");

    await user.click(screen.getByRole("button", { name: "Reset" }));

    expect(screen.getByRole("radio", { name: /All/ })).toBeChecked();
    expect(screen.getByRole("searchbox")).toHaveValue("");
    expect(shown()).toHaveLength(3);
  });
});
