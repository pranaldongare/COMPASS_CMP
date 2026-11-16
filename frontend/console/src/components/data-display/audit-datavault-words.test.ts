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

describe("an erasure in DataVault", () => {
  it("says how many went, and what a request about one consent left out", () => {
    expect(
      said("datavault.erasure_sent", { assets: 3, instructions: 1, left_out: 0 }),
    ).toBe("DataVault was told to erase 3 assets.");
    expect(
      said("datavault.erasure_sent", { assets: 1200, instructions: 2, left_out: 1 }),
    ).toBe(
      "DataVault was told to erase 1200 assets, in 2 instructions. 1 asset DataVault listed was left out: the request is about one consent.",
    );
  });

  it("says what DataVault answered, as counts", () => {
    expect(
      said("datavault.erasure_checked", {
        again: false,
        outcome: "answered",
        erased: 1,
        pending: 1,
        failed: 0,
        not_held: 0,
      }),
    ).toBe(
      "DataVault was sent the instruction to erase. It answered: 1 erased, 1 pending.",
    );
    expect(
      said("datavault.erasure_checked", {
        again: true,
        outcome: "answered",
        erased: 2,
        failed: 1,
        not_held: 1,
      }),
    ).toBe(
      "DataVault was asked how far the erasure has got. It answered: 2 erased, 1 not erased, 1 not held.",
    );
  });

  it("says why an ask was not answered, by its code", () => {
    expect(
      said("datavault.erasure_checked", {
        again: true,
        outcome: "failed",
        failure: "status_409",
      }),
    ).toBe(
      "DataVault was asked how far the erasure has got. It was not answered: DataVault has this instruction with a different list of assets.",
    );
    expect(
      said("datavault.erasure_checked", { outcome: "failed", failure: "anything" }),
    ).toBe(
      "DataVault was sent the instruction to erase. It was not answered: the instruction was not answered.",
    );
  });
});

describe("a consent change told to DataVault", () => {
  const consent = (event_type: string, detail: Record<string, unknown>) =>
    eventSentence({
      ...entry(event_type, detail),
      entity_type: "consent_artefact",
    } as AuditEntry);

  it("says what changed and what the assets may be used for", () => {
    expect(
      consent("datavault.consent_change_queued", {
        sequence: 1042,
        change: "partly_withdrawn",
        action: "restrict",
        purposes_granted: ["RND-IMG-01"],
        purposes_removed: ["RND-VID-02"],
      }),
    ).toBe(
      "To tell DataVault (message 1042): part of the consent was withdrawn. The assets are to be used only for RND-IMG-01. Taken away: RND-VID-02.",
    );
    expect(
      consent("datavault.consent_change_queued", {
        sequence: 7,
        change: "withdrawn",
        action: "restrict",
        purposes_granted: [],
        purposes_removed: ["RND-IMG-01"],
      }),
    ).toBe(
      "To tell DataVault (message 7): the consent was withdrawn. The assets are not to be used at all. Taken away: RND-IMG-01.",
    );
    expect(
      consent("datavault.consent_change_queued", {
        sequence: 8,
        change: "granted_again",
        action: "lift_restriction",
        purposes_granted: ["RND-IMG-01", "RND-VID-02"],
        purposes_removed: [],
      }),
    ).toBe(
      "To tell DataVault (message 8): purposes were granted again. The assets may be used again for RND-IMG-01, RND-VID-02.",
    );
  });

  it("says what DataVault did with it", () => {
    const delivered = (detail: Record<string, unknown>) =>
      consent("datavault.consent_change_delivered", {
        sequence: 1043,
        change: "expired",
        action: "restrict",
        ...detail,
      });
    expect(delivered({ result: "applied", assets_affected: 2 })).toBe(
      "DataVault was told (message 1043): the validity of a purpose ran out. It applied it to 2 assets.",
    );
    expect(delivered({ result: "applied", assets_affected: 0 })).toMatch(
      /It applied it; it holds no asset under this consent\.$/,
    );
    expect(delivered({ result: "duplicate", assets_affected: 0 })).toMatch(
      /It had the message already\.$/,
    );
    expect(delivered({ result: "stale", assets_affected: 0 })).toMatch(
      /It had a later message for this consent already, and changed nothing\.$/,
    );
  });
});

describe("the connection, since erasures and consent changes (0071)", () => {
  it("says the erasure address, the ID switch and consent changes", () => {
    expect(
      said("datavault.connection_changed", {
        address_changed: false,
        key_changed: false,
        key_set: true,
        header_changed: false,
        enabled: true,
        was_enabled: true,
        erasure_address_changed: true,
        id_format: "uuid",
        id_format_was: "numeric",
        consent_changes: true,
        consent_changes_were: false,
      }),
    ).toBe(
      "The DataVault connection was saved. The erasure address was changed. IDs are now sent as UUIDs. Consent changes were switched on.",
    );
  });
});
