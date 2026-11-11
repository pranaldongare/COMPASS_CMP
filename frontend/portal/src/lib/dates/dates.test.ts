import { describe, expect, it } from "vitest";

import { nowLocal, todayLocal } from "@/lib/dates";

describe("dates for inputs", () => {
  it("are the reader's own calendar, not Greenwich's", () => {
    // 1 a.m. local on the 12th: UTC may still be the 11th, the input must say the 12th.
    const at = new Date(2026, 10, 12, 1, 5);
    expect(todayLocal(at)).toBe("2026-11-12");
    expect(nowLocal(at)).toBe("2026-11-12T01:05");
  });
});
