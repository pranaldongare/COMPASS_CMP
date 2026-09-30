import { describe, expect, it } from "vitest";

import { clockText, span } from "@/features/breach/components/copy";
import type { BreachClock } from "@/types";

const base: BreachClock = {
  without_delay: false,
  seconds_remaining: null,
  overdue: false,
  seconds_elapsed: null,
  target_at: null,
  past_target: false,
};

describe("a duty's clock, in words", () => {
  it("counts down a dated duty and says when it is overdue", () => {
    expect(clockText("outstanding", { ...base, seconds_remaining: 3_600 + 20 * 60 })).toBe("1 h 20 min left");
    expect(clockText("outstanding", { ...base, seconds_remaining: -2 * 86_400, overdue: true })).toBe(
      "Overdue by 2 d 0 h",
    );
  });

  it("reads 'without delay' as time since awareness, and says when no target is set", () => {
    const clock = { ...base, without_delay: true, seconds_elapsed: 5 * 3_600 };
    expect(clockText("outstanding", clock)).toBe("5 h 0 min since awareness (no internal target set)");
  });

  it("flags a duty past the internal target only when the server says so", () => {
    const clock = {
      ...base,
      without_delay: true,
      seconds_elapsed: 30 * 3_600,
      target_at: "2026-09-30T10:00:00Z",
      past_target: true,
    };
    expect(clockText("outstanding", clock)).toBe("1 d 6 h since awareness - past the internal target");
  });

  it("says nothing for a duty that is done or does not apply", () => {
    expect(clockText("done", { ...base, seconds_remaining: -10, overdue: true })).toBe("");
    expect(clockText("not_applicable", base)).toBe("");
  });

  it("spans minutes, hours and days", () => {
    expect(span(59)).toBe("0 min");
    expect(span(-90 * 60)).toBe("1 h 30 min");
    expect(span(3 * 86_400 + 7_200)).toBe("3 d 2 h");
  });
});
