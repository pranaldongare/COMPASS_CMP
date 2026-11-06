/**
 * The fallback covers what a public report seals (0058), so a key service
 * writing another envelope still has the report's words opened in the intake.
 * `reporter_*` and `dismissal_reason` were there already; these were not.
 */
import { describe, expect, it } from "vitest";

import { TYPE_BY_FIELD } from "@/lib/dkms/field-types";

describe("TYPE_BY_FIELD", () => {
  it.each([
    "title",
    "origin",
    "discovery",
    "affected_systems",
    "incident_details",
    "impact_scale",
    "countries_involved",
    "data_nature",
    "subject_types",
    "entities_involved",
    "third_parties",
  ])("labels a report's %s as free text", (field) => {
    expect(TYPE_BY_FIELD[field]).toBe("FREE_TEXT");
  });
});
