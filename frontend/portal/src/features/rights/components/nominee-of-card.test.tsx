/**
 * The badge on a nomination names its state. Revoked and declined read
 * "Awaiting your acceptance", which asks the nominee to do something that is
 * no longer possible.
 */
import { HttpResponse, http } from "msw";
import { describe, expect, it } from "vitest";

import { NomineeOfCard } from "@/features/rights/components/nominee-of-card";
import { render, screen } from "@/test/render";
import { API, server } from "@/test/server";
import type { NominationStatus, NomineeOf } from "@/types";

function nomination(status: NominationStatus): NomineeOf {
  return {
    nomination_uuid: "55555555-5555-4555-8555-555555555555",
    principal_name: "Anjali Verma",
    rights: ["access"],
    status,
    contact: "+91 98707 00001",
    accept_expires_at: null,
    accepted_at: null,
    created_at: "2026-09-20T10:00:00Z",
    invoked_at: null,
    invoked_event: null,
    invoked_reference: null,
    invoked_evidenced_at: null,
    invoked_request_uuid: null,
    invoked_request_type: null,
    invoked_status: null,
    invoked_outcome: null,
    invoked_due_at: null,
    invoked_responded_at: null,
    invoked_closed_at: null,
  } as NomineeOf;
}

describe("NomineeOfCard badge", () => {
  it.each([
    ["active", "In place"],
    ["pending", "Awaiting your acceptance"],
    ["revoked", "Revoked"],
    ["declined", "Declined"],
  ] as const)("a %s nomination reads %s", async (status, label) => {
    server.use(http.get(`${API}/me/nominee-of`, () => HttpResponse.json([nomination(status)])));
    render(<NomineeOfCard />);
    expect(await screen.findByText(label)).toBeInTheDocument();
    if (status !== "pending") {
      expect(screen.queryByText("Awaiting your acceptance")).not.toBeInTheDocument();
    }
  });
});
