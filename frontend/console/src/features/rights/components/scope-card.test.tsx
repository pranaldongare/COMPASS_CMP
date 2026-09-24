/**
 * The scope card shows each store as the server reports it (S2-03): an item
 * applied but not carried out reads as quarantined and in progress, never as
 * erased; a hold says so and offers its release; a carried-out item shows its
 * disposition and nothing left to retry.
 */
import { describe, expect, it } from "vitest";

import { ScopeCard } from "@/features/rights/components/scope-card";
import { ToastProvider } from "@/providers/toast-provider";
import { makeRequestDetail } from "@/test/fixtures";
import { render, screen } from "@/test/render";
import type { RightsItemExecution, RightsScopeItem } from "@/types";

function item(overrides: Partial<RightsScopeItem> = {}): RightsScopeItem {
  return {
    item_uuid: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    other_subjects: 0,
    state: "applied",
    decision: "erase",
    basis: "She asked",
    retain_until: null,
    floor_passed_at: null,
    decided_at: "2026-09-20T10:00:00Z",
    decided_by_name: "DPO",
    applied_at: "2026-09-20T10:00:00Z",
    disposition: "quarantined",
    disposition_at: "2026-09-20T10:00:00Z",
    subject_role: "consented",
    asset_uuid: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
    asset_type: "video",
    source_asset_ref: "ASSET-7",
    source_code: "SRC",
    source_name: "Rig",
    processor_name: "Lab",
    project_uuid: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
    project_name: "Gait",
    collected_on: "2026-09-01",
    holder_uuid: null,
    holder_label: null,
    holder_ticket_status: null,
    executed_at: null,
    execution: [],
    ...overrides,
  };
}

const at = "2026-09-21T10:00:00Z";
const waiting: RightsItemExecution = { store: "holder_copy", status: "waiting", detail: { reason: "awaiting_return" }, attempted_at: at };

function card(i: RightsScopeItem) {
  return render(
    <ToastProvider>
      <ScopeCard request={makeRequestDetail({ status: "collating", request_type: "erasure", items: [i] })} />
    </ToastProvider>,
  );
}

describe("ScopeCard execution", () => {
  it("reads an applied, unfinished erasure as quarantined and in progress - not erased", () => {
    card(item({ execution: [waiting] }));
    expect(screen.getByText(/quarantined - being erased/i)).toBeInTheDocument();
    expect(screen.getByText(/waiting for the holder's ticket/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /try again now/i })).toBeInTheDocument();
    expect(screen.queryByText(/^erased$/i)).not.toBeInTheDocument();
  });

  it("says a hold stopped it and offers the release", () => {
    card(item({ execution: [{ store: "legal_hold", status: "held", detail: { hold: "dddddddd-dddd-4ddd-8ddd-dddddddddddd", covers: "asset" }, attempted_at: at }] }));
    expect(screen.getByText(/legal hold/i, { selector: "span" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /release hold/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /try again now/i })).not.toBeInTheDocument();
  });

  it("shows the disposition once carried out, with nothing left to retry", () => {
    card(item({ disposition: "erased", executed_at: at, execution: [{ ...waiting, status: "done", detail: {} }] }));
    expect(screen.getByText("erased")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /try again now/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /legal hold/i })).not.toBeInTheDocument();
  });

  it("stops showing a hold once it is released", () => {
    card(
      item({
        disposition: "erased",
        executed_at: at,
        execution: [
          { store: "legal_hold", status: "done", detail: { released: "dddddddd-dddd-4ddd-8ddd-dddddddddddd" }, attempted_at: at },
          { ...waiting, status: "done", detail: {} },
        ],
      }),
    );
    expect(screen.getByText(/legal hold: released/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /release hold/i })).not.toBeInTheDocument();
    expect(screen.getByText("erased")).toBeInTheDocument();
  });
});
