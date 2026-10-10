/**
 * Text is readable on every background it sits on, in both themes.
 *
 * Computed from `themes.css` itself, so changing a token re-runs the check.
 * The subtle text token measured about 3.9:1 on a card and 3.3:1 on an inset
 * in the light theme, used for small labels, dates and metadata (UX review
 * 2026-10-05). WCAG 2.2 asks 4.5:1 for normal text.
 */
import { readFileSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

const CSS = readFileSync(path.join(__dirname, "themes.css"), "utf8");
const TEXT = ["--text", "--text-muted", "--text-subtle"];
const GROUNDS = ["--bg", "--bg-subtle", "--bg-inset", "--surface", "--surface-hover", "--surface-raised", "--page-bg", "--card-head", "--table-head", "--row-hover"];

function block(selector: string): Record<string, [number, number, number]> {
  // The light block is also `.dark .frame-light`, so match a selector at
  // the start of a line followed by its brace or a comma.
  const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const start = CSS.search(new RegExp(`^${escaped}(?: \\{|,)`, "m"));
  const body = CSS.slice(start, CSS.indexOf("\n}", start));
  const tokens: Record<string, [number, number, number]> = {};
  for (const m of body.matchAll(/(--[\w-]+):\s*oklch\(([\d.]+)%\s+([\d.]+)\s+([\d.]+)\)/g)) {
    tokens[m[1]] = [Number(m[2]) / 100, Number(m[3]), Number(m[4])];
  }
  return tokens;
}

function luminance([L, C, h]: [number, number, number]): number {
  const a = C * Math.cos((h * Math.PI) / 180);
  const b = C * Math.sin((h * Math.PI) / 180);
  const l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3;
  const m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3;
  const s = (L - 0.0894841775 * a - 1.291485548 * b) ** 3;
  const clamp = (x: number) => Math.min(1, Math.max(0, x));
  const r = clamp(4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s);
  const g = clamp(-1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s);
  const bl = clamp(-0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s);
  return 0.2126 * r + 0.7152 * g + 0.0722 * bl;
}

function ratio(x: [number, number, number], y: [number, number, number]): number {
  const [hi, lo] = [luminance(x), luminance(y)].sort((p, q) => q - p);
  return (hi + 0.05) / (lo + 0.05);
}

describe.each([
  ["light", ":root"],
  ["dark", ".dark"],
])("%s theme", (_name, selector) => {
  const tokens = { ...block(":root"), ...block(selector) };
  for (const text of TEXT) {
    it(`${text} is at least 4.5:1 on every background`, () => {
      const failing = GROUNDS.filter((g) => tokens[g])
        .map((g) => [g, ratio(tokens[text], tokens[g])] as const)
        .filter(([, r]) => r < 4.5)
        .map(([g, r]) => `${g} ${r.toFixed(2)}:1`);
      expect(failing).toEqual([]);
    });
  }
});
