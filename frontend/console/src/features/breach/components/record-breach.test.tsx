/**
 * The processor picker on Log an incident (2026-10-06): every processor,
 * not the newest fifty - the seeded ones had fallen off - A to Z whatever the
 * case, and narrowed by what is typed.
 */
import { HttpResponse, http } from "msw";
import * as React from "react";
import { describe, expect, it, vi } from "vitest";

import { ProcessorPicker } from "@/features/breach/components/record-breach";
import { render, screen, within } from "@/test/render";
import { API, server } from "@/test/server";

vi.mock("@/providers", () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn() }),
}));

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
});
