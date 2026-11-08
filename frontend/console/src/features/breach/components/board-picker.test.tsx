/**
 * Who a report goes to (0064): everyone on the board's list, ticked, less any
 * the sender leaves out, and anyone added for that report alone. A mandatory
 * address is ticked and cannot be unticked. What is chosen is kept as what was
 * left out, so it holds through a change to the list.
 */
import * as React from "react";
import { describe, expect, it } from "vitest";

import {
  BoardPicker,
  NOTHING_CHANGED,
  chosen,
  type BoardPick,
} from "@/features/breach/components/board-picker";
import { render, screen, within } from "@/test/render";
import type { BreachBoardEntry } from "@/types";

const CHAIR = "11111111-1111-4111-8111-111111111111";
const DEPUTY = "22222222-2222-4222-8222-222222222222";

const entry = (over: Partial<BreachBoardEntry> = {}): BreachBoardEntry => ({
  recipient_uuid: CHAIR,
  full_name: "Asha Rao",
  email: "chair@cmp.local",
  mandatory: false,
  ...over,
});

const BOARD = [
  entry(),
  entry({ recipient_uuid: DEPUTY, full_name: null, email: "deputy@cmp.local" }),
];

/** The picker as the window holds it, with what a press would send beside it. */
function Harness({
  board = BOARD,
  holds = false,
}: {
  board?: BreachBoardEntry[];
  holds?: boolean;
}) {
  const [pick, setPick] = React.useState<BoardPick>(NOTHING_CHANGED);
  return (
    <>
      <BoardPicker board={board} pick={pick} onChange={setPick} holds={holds} />
      <output data-testid="body">{JSON.stringify(chosen(board, pick).body)}</output>
    </>
  );
}

const body = () => JSON.parse(screen.getByTestId("body").textContent ?? "{}") as unknown;

describe("BoardPicker", () => {
  it("ticks everyone on the list, and locks a mandatory address ticked", () => {
    render(<Harness board={[entry({ mandatory: true }), BOARD[1]]} />);

    const chair = screen.getByRole("checkbox", { name: "Asha Rao, chair@cmp.local" });
    expect(chair).toBeChecked();
    expect(chair).toBeDisabled();
    expect(chair).toHaveAccessibleDescription("Mandatory");
    expect(screen.getByRole("checkbox", { name: "deputy@cmp.local" })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: "deputy@cmp.local" })).toBeEnabled();
    expect(screen.getByText("Mandatory")).toBeInTheDocument();
    expect(
      screen.getByText(/A mandatory address goes with every report and cannot be left out/),
    ).toBeInTheDocument();
    expect(screen.getByText("Goes to 2 addresses.")).toBeInTheDocument();
  });

  it("leaves an address out and counts what is left", async () => {
    const { user } = render(<Harness />);

    await user.click(screen.getByRole("checkbox", { name: "deputy@cmp.local" }));

    expect(screen.getByRole("checkbox", { name: "deputy@cmp.local" })).not.toBeChecked();
    expect(screen.getByText("Goes to 1 address.")).toBeInTheDocument();
    expect(body()).toEqual({ recipients: [CHAIR], extra: [] });

    await user.click(screen.getByRole("checkbox", { name: "deputy@cmp.local" }));
    expect(body()).toEqual({ recipients: [CHAIR, DEPUTY], extra: [] });
  });

  it("adds an address for this report only, with or without a name, and removes it again", async () => {
    const { user } = render(<Harness />);

    await user.type(screen.getByLabelText(/^Name/), "  Ravi Kumar ");
    await user.type(screen.getByLabelText(/^Mail ID/), " ravi@cmp.local ");
    await user.click(screen.getByRole("button", { name: "Add for this report" }));
    await user.type(screen.getByLabelText(/^Mail ID/), "auditor@cmp.local{Enter}");

    const added = screen.getByRole("list", { name: "Added for this report" });
    expect(within(added).getByText("Ravi Kumar, ravi@cmp.local")).toBeInTheDocument();
    expect(within(added).getAllByText("This report only")).toHaveLength(2);
    // Back to empty, ready for the next.
    expect(screen.getByLabelText(/^Mail ID/)).toHaveValue("");
    expect(screen.getByLabelText(/^Name/)).toHaveValue("");
    expect(screen.getByText("Goes to 4 addresses.")).toBeInTheDocument();
    expect(body()).toEqual({
      recipients: [CHAIR, DEPUTY],
      extra: [
        { full_name: "Ravi Kumar", email: "ravi@cmp.local" },
        { full_name: null, email: "auditor@cmp.local" },
      ],
    });

    await user.click(
      screen.getByRole("button", { name: "Remove ravi@cmp.local from this report" }),
    );
    expect(body()).toEqual({
      recipients: [CHAIR, DEPUTY],
      extra: [{ full_name: null, email: "auditor@cmp.local" }],
    });
  });

  it("will not add an address already on the list or already added, and says which", async () => {
    const { user } = render(<Harness />);
    const box = screen.getByLabelText(/^Mail ID/);

    await user.type(box, "Chair@CMP.local");
    await user.click(screen.getByRole("button", { name: "Add for this report" }));
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Already on the board list: tick it above",
    );
    expect(box).toHaveValue("Chair@CMP.local");

    await user.clear(box);
    await user.type(box, "ravi@cmp.local");
    await user.click(screen.getByRole("button", { name: "Add for this report" }));
    await user.type(box, "RAVI@cmp.local");
    await user.click(screen.getByRole("button", { name: "Add for this report" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Already added to this report");
    expect(body()).toEqual({
      recipients: [CHAIR, DEPUTY],
      extra: [{ full_name: null, email: "ravi@cmp.local" }],
    });
  });

  it("takes no more than twenty addresses for one report, the server's limit, and says so", async () => {
    const { user } = render(<Harness />);
    const box = screen.getByLabelText(/^Mail ID/);

    for (let i = 1; i <= 20; i += 1) await user.type(box, `extra${i}@cmp.local{Enter}`);

    const extra = () => (body() as { extra: unknown[] }).extra;
    expect(extra()).toHaveLength(20);
    expect(
      screen.getByText("At most 20 addresses can be added for one report."),
    ).toBeInTheDocument();
    expect(box).toBeDisabled();
    expect(screen.getByLabelText(/^Name/)).toBeDisabled();
    expect(screen.getByRole("button", { name: "Add for this report" })).toBeDisabled();
    await user.type(box, "extra21@cmp.local{Enter}");
    expect(extra()).toHaveLength(20);

    // One taken off makes room again.
    await user.click(
      screen.getByRole("button", { name: "Remove extra20@cmp.local from this report" }),
    );
    expect(box).toBeEnabled();
    await user.type(box, "extra21@cmp.local{Enter}");
    expect(extra()).toHaveLength(20);
    expect(
      screen.queryByText("At most 20 addresses can be added for one report."),
    ).toBeInTheDocument();
  });

  it("asks for an email address when what is typed is not shaped like one", async () => {
    const { user } = render(<Harness />);

    await user.type(screen.getByLabelText(/^Mail ID/), "ravi at cmp");
    await user.click(screen.getByRole("button", { name: "Add for this report" }));

    expect(screen.getByRole("alert")).toHaveTextContent("Enter an email address");
    expect(
      screen.queryByRole("list", { name: "Added for this report" }),
    ).not.toBeInTheDocument();
    await user.type(screen.getByLabelText(/^Mail ID/), "x");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("says to choose at least one address when everyone is left out", async () => {
    const { user } = render(<Harness />);

    await user.click(screen.getByRole("checkbox", { name: "Asha Rao, chair@cmp.local" }));
    await user.click(screen.getByRole("checkbox", { name: "deputy@cmp.local" }));

    expect(screen.getByText("Choose at least one address.")).toBeInTheDocument();
    expect(screen.queryByText(/^Goes to/)).not.toBeInTheDocument();
  });

  it("says the board's mail waits for validation when it will be held", () => {
    const { unmount } = render(<Harness holds />);
    expect(screen.getByText("The board's mail waits for validation")).toBeInTheDocument();
    expect(
      screen.getByText(/goes to the addresses chosen here at the first Yes/),
    ).toBeInTheDocument();
    unmount();

    render(<Harness />);
    expect(
      screen.queryByText("The board's mail waits for validation"),
    ).not.toBeInTheDocument();
  });
});

describe("chosen", () => {
  it("sends every mandatory entry, whatever was left out, and drops a left-out entry no longer listed", () => {
    const pick: BoardPick = { leftOut: new Set([CHAIR, DEPUTY, "gone"]), extra: [] };

    expect(chosen([entry({ mandatory: true }), BOARD[1]], pick)).toEqual({
      body: { recipients: [CHAIR], extra: [] },
      count: 1,
    });
  });
});
