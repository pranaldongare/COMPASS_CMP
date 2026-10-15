import { describe, expect, it } from "vitest";

import { consentIdsIn } from "@/features/consent/consent-ids";

const A = "46a27302-6b59-417c-bc89-a8d68895bedc";
const B = "655d1760-6f31-4c25-8766-9a16917ae116";
const PERSON = "23df7bbe-fe88-40cc-bec2-5e625d0f86eb";

describe("consentIdsIn", () => {
  it("reads one a line, commas and spaces, and counts a repeat once", () => {
    expect(consentIdsIn(`${A}\n${B}, ${A.toUpperCase()}\n`)).toEqual({
      ids: [A, B],
      repeats: 1,
      unread: [],
    });
  });

  it("reads only the consent_uuid column of a CSV, not the person's or project's IDs", () => {
    const csv = `file,sha256,consent_uuid,principal_uuid\nconsent-${A}.pdf,ab,${A},${PERSON}\nconsent-${B}.pdf,cd,"${B}",${PERSON}\n`;
    expect(consentIdsIn(csv).ids).toEqual([A, B]);
  });

  it("names a line with no ID in it", () => {
    expect(consentIdsIn(`${A}\nnot an id\n\n`).unread).toEqual(["not an id"]);
  });
});
