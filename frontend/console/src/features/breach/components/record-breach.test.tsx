/**
 * The processor picker on Log an incident (2026-10-06): every processor,
 * not the newest fifty - the seeded ones had fallen off - A to Z whatever the
 * case, and narrowed by what is typed. What is chosen stays in the list
 * whatever is typed. A role with no sources section is not offered a data
 * source to pick from.
 */
import { HttpResponse, http } from "msw";
import * as React from "react";
import { describe, expect, it, vi } from "vitest";

import { ProcessorPicker, RecordBreachForm } from "@/features/breach/components/record-breach";
import { makeMe } from "@/test/fixtures";
import { render, screen, within } from "@/test/render";
import { API, server } from "@/test/server";

const nav = vi.hoisted(() => ({ current: ["breaches", "sources"] }));

vi.mock("@/providers", () => ({
  useAuth: () => ({ me: makeMe({ nav: nav.current as never }) }),
  useToast: () => ({ success: vi.fn(), error: vi.fn() }),
}));

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

const processor = (name: string, n: number) => ({
  processor_uuid: `00000000-0000-4000-8000-${String(n).padStart(12, "0")}`,
  legal_name: name,
  contract_ref: `CTR-${n}`,
});

function Harness() {
  const [value, setValue] = React.useState("");
  return <ProcessorPicker value={value} onChange={setValue} />;
}

describe("ProcessorPicker", () => {
  it("offers every page of the register, A to Z, narrowed by typing", async () => {
    const asked: string[] = [];
    server.use(
      http.get(`${API}/processors`, ({ request }) => {
        const url = new URL(request.url);
        asked.push(url.search);
        return url.searchParams.get("cursor") === "page-2"
          ? HttpResponse.json({ items: [processor("SEED", 3)], next_cursor: null, total: 3 })
          : HttpResponse.json({
              items: [processor("Zeta Lab", 1), processor("alpha Labs", 2)],
              next_cursor: "page-2",
              total: 3,
            });
      }),
    );
    const { user } = render(<Harness />);

    const select = screen.getByLabelText(/^Processor/);
    await vi.waitFor(() => expect(within(select).getAllByRole("option")).toHaveLength(4));
    expect(within(select).getAllByRole("option").map((o) => o.textContent)).toEqual([
      "Choose…",
      "alpha Labs",
      "SEED",
      "Zeta Lab",
    ]);
    expect(asked[0]).toContain("sort=legal_name");

    await user.type(screen.getByLabelText(/^Find the processor/), "see");
    expect(within(select).getAllByRole("option").map((o) => o.textContent)).toEqual(["Choose…", "SEED"]);
  });

  it("keeps what is chosen in the list, whatever the search says", async () => {
    server.use(
      http.get(`${API}/processors`, () =>
        HttpResponse.json({
          items: [processor("Zeta Lab", 1), processor("alpha Labs", 2)],
          next_cursor: null,
          total: 2,
        }),
      ),
    );
    const { user } = render(<Harness />);

    const select = screen.getByLabelText(/^Processor/);
    await vi.waitFor(() => expect(within(select).getAllByRole("option")).toHaveLength(3));
    await user.selectOptions(select, processor("alpha Labs", 2).processor_uuid);

    await user.type(screen.getByLabelText(/^Find the processor/), "zeta");
    expect(select).toHaveDisplayValue("alpha Labs");
    expect(within(select).getAllByRole("option").map((o) => o.textContent)).toEqual([
      "Choose…",
      "alpha Labs",
      "Zeta Lab",
    ]);
  });
});

describe("RecordBreachForm", () => {
  const places = () =>
    within(screen.getByLabelText(/^Where it occurred/))
      .getAllByRole("option")
      .map((o) => o.getAttribute("value"));

  it("offers a data source to whoever has the sources section", () => {
    nav.current = ["breaches", "sources"];
    render(<RecordBreachForm onDone={() => {}} />);
    expect(places()).toContain("data_source");
  });

  it("does not offer one to whoever has nothing to choose from", () => {
    nav.current = ["breaches"];
    render(<RecordBreachForm onDone={() => {}} />);
    expect(places()).not.toContain("data_source");
    expect(places()).toContain("processor");
  });
});
