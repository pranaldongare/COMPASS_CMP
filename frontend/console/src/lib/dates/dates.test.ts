import { describe, expect, it } from "vitest";

import { endOfDay, lastDayBy, nowLocal, todayLocal } from "@/lib/dates";

describe("dates for inputs", () => {
  it("are the reader's own calendar, not Greenwich's", () => {
    // 1 a.m. local on the 12th: UTC may still be the 11th, the input must say the 12th.
    const at = new Date(2026, 10, 12, 1, 5);
    expect(todayLocal(at)).toBe("2026-11-12");
    expect(nowLocal(at)).toBe("2026-11-12T01:05");
  });
});

describe("the day a ticket falls due", () => {
  it("is the end of the chosen day, in the reader's own calendar", () => {
    // Due today is overdue tomorrow: one minute before the local midnight.
    expect(new Date(endOfDay("2026-11-20")).getTime()).toBe(new Date(2026, 10, 20, 23, 59).getTime());
  });

  it("is never past the moment the response itself is due (2026-11-12)", () => {
    // The response is due mid-morning on the 20th: a ticket due at the end
    // of that day would be late for it, so the 19th is the last day.
    expect(lastDayBy(new Date(2026, 10, 20, 10, 14).toISOString())).toBe("2026-11-19");
    // Due at the very end of the 20th, the 20th itself still fits.
    expect(lastDayBy(new Date(2026, 10, 20, 23, 59, 30).toISOString())).toBe("2026-11-20");
  });
});
