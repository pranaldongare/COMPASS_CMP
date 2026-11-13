/**
 * DataVault on the trail, and the holders the platform finds as a request
 * starts (2026-11-13): each said from what its row carries.
 */
import { describe, expect, it } from "vitest";

import { datavaultSentence } from "@/components/data-display/audit-datavault-words";
import { eventSentence } from "@/components/data-display/audit-detail";
import type { AuditEntry } from "@/types";

const entry = (event_type: string, detail: Record<string, unknown> = {}): AuditEntry =>
  ({
    log_uuid: "l1",
    event_type,
    entity_type:
      event_type === "datavault.connection_changed"
        ? "datavault_connection"
        : "rights_request",
    entity_id: 7,
    occurred_at: "2026-11-13T10:00:00Z",
    detail: { reference: "RR-2026-0200", ...detail },
  }) as unknown as AuditEntry;

const said = (event_type: string, detail?: Record<string, unknown>) =>
  eventSentence(entry(event_type, detail));

describe("a request checked in DataVault", () => {
  it("says who asked, and what came back", () => {
    expect(
      said("datavault.checked", { outcome: "answered", assets: 3, unmatched: 1 }),
    ).toBe(
      "DataVault was asked what it holds of the person. It listed 3 assets, 1 not matched to this person's records.",
    );
    expect(
      said("datavault.checked", { outcome: "answered", assets: 1, unmatched: 0 }),
    ).toBe("DataVault was asked what it holds of the person. It listed 1 asset.");
    expect(
      said("datavault.checked", { automatic: true, outcome: "answered", assets: 0 }),
    ).toBe(
      "The platform asked DataVault what it holds of the person, as holders were found. It holds nothing.",
    );
  });

  it("says why a check was not answered, by its code and nothing more", () => {
    expect(said("datavault.checked", { outcome: "failed", failure: "timeout" })).toBe(
      "DataVault was asked what it holds of the person. It was not answered: DataVault did not answer in time.",
    );
    expect(
      said("datavault.checked", {
        automatic: true,
        outcome: "failed",
        failure: "status_503",
      }),
    ).toMatch(
      /as holders were found\. It was not answered: DataVault answered with an error \(503\)\.$/,
    );
    expect(
      said("datavault.checked", { outcome: "failed", failure: "something new" }),
    ).toMatch(/the check did not complete\.$/);
  });

  it("invents nothing a row does not carry", () => {
    expect(said("datavault.checked", {})).toBe(
      "DataVault was asked what it holds of the person.",
    );
    expect(datavaultSentence(entry("rights.status_changed"))).toBeNull();
  });
});

describe("the DataVault connection", () => {
  it("says what changed, never the address or the key", () => {
    expect(
      said("datavault.connection_changed", {
        address_changed: true,
        key_changed: true,
        key_set: true,
        header_changed: false,
        enabled: true,
        was_enabled: false,
      }),
    ).toBe(
      "The DataVault connection was changed: the address, the key. It was switched on.",
    );
    expect(
      said("datavault.connection_changed", {
        address_changed: false,
        key_changed: true,
        key_set: false,
        header_changed: true,
        enabled: true,
        was_enabled: true,
      }),
    ).toBe(
      "The DataVault connection was changed: the key, which was removed, the header the key is sent in.",
    );
    expect(
      said("datavault.connection_changed", {
        key_set: true,
        enabled: false,
        was_enabled: true,
      }),
    ).toBe("The DataVault connection was saved. It was switched off.");
  });
});

describe("the records read for who holds a person's data", () => {
  it("says the platform read them as the request started", () => {
    expect(said("rights.holders_derived", { automatic: true, added: 2 })).toBe(
      "The platform read the records for who holds the person's data as the request started. 2 holders were added.",
    );
    expect(said("rights.holders_derived", { automatic: true, added: 0 })).toBe(
      "The platform read the records for who holds the person's data as the request started. Nobody new was found.",
    );
  });

  it("says a press of the button as it always was one", () => {
    expect(said("rights.holders_derived", { added: 1 })).toBe(
      "The records were read for who holds the person's data. 1 holder was added.",
    );
    expect(said("rights.holders_derived", {})).toBe(
      "The records were read for who holds the person's data.",
    );
  });
});
