import { describe, expect, it } from "vitest";

import { excerpt, relate } from "@/features/rights/relate";
import { makeMyRequest } from "@/test/fixtures";

const ORIGINAL = "11111111-1111-4111-8111-111111111111";
const GRIEVANCE = "22222222-2222-4222-8222-222222222222";
const RERUN = "33333333-3333-4333-8333-333333333333";

describe("relate", () => {
  it("pairs a grievance with the request it disputes, and the re-run with the grievance", () => {
    const original = makeMyRequest({ request_uuid: ORIGINAL, reference: "RR-1" });
    const grievance = makeMyRequest({ request_uuid: GRIEVANCE, reference: "RR-2", request_type: "grievance", linked_request_uuid: ORIGINAL, linked_reference: "RR-1" });
    const rerun = makeMyRequest({ request_uuid: RERUN, reference: "RR-3", linked_request_uuid: GRIEVANCE, linked_reference: "RR-2" });
    const { byUuid, followers } = relate([rerun, grievance, original]);
    expect(byUuid.get(grievance.linked_request_uuid!)).toBe(original);
    expect(followers.get(ORIGINAL)).toEqual([grievance]);
    expect(followers.get(GRIEVANCE)).toEqual([rerun]);
    expect(followers.get(RERUN)).toBeUndefined();
  });

  it("ignores a link to a request that is not on her list", () => {
    const grievance = makeMyRequest({ request_uuid: GRIEVANCE, request_type: "grievance", linked_request_uuid: ORIGINAL });
    const { followers } = relate([grievance]);
    expect(followers.size).toBe(0);
  });
});

describe("excerpt", () => {
  it("leaves a short answer alone", () => {
    expect(excerpt("Nothing held.")).toBe("Nothing held.");
  });
  it("cuts a long one at a word and marks the cut", () => {
    const long = "word ".repeat(80).trim();
    const cut = excerpt(long)!;
    expect(cut.endsWith("…")).toBe(true);
    expect(cut.length).toBeLessThanOrEqual(221);
    expect(cut).not.toMatch(/wor…$/);
  });
  it("is nothing when there is nothing", () => {
    expect(excerpt(null)).toBeNull();
  });
});
