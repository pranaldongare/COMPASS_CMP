/**
 * The processor's country (S2-04): optional to register, two letters when
 * given, and sent upper-cased - the server refuses an export to a processor
 * without one, and the form must not be the reason one is malformed.
 */
import { describe, expect, it } from "vitest";

import { processorSchema } from "@/features/registry/schemas";

const base = {
  legal_name: "Pune Motion Lab Pvt Ltd",
  type: "lab",
  contract_ref: "CTR-2026-0091",
  security_confirmed_at: "2026-01-15",
  is_in_house: false,
};

describe("processorSchema location_country", () => {
  it("is optional, and an empty box sends null", () => {
    expect(processorSchema.parse({ ...base, location_country: "" }).location_country).toBeNull();
  });

  it("upper-cases a two-letter code", () => {
    expect(processorSchema.parse({ ...base, location_country: "in" }).location_country).toBe("IN");
  });

  it.each(["IND", "I", "1N"])("refuses %s", (bad) => {
    expect(processorSchema.safeParse({ ...base, location_country: bad }).success).toBe(false);
  });
});
