import { describe, expect, it } from "vitest";

import { returnTarget, withFrom } from "@/lib/navigation/return-to";

describe("withFrom", () => {
  it("adds where the link was opened from, keeping the section", () => {
    expect(withFrom("/notices/n-1", "/projects/p-1#notices")).toBe(
      `/notices/n-1?from=${encodeURIComponent("/projects/p-1#notices")}`,
    );
    expect(withFrom("/projects/p-1#sites", "/projects?status=approved")).toBe(
      `/projects/p-1?from=${encodeURIComponent("/projects?status=approved")}#sites`,
    );
  });
});

describe("returnTarget", () => {
  it("returns a filtered list under the expected prefix", () => {
    expect(returnTarget("/projects?status=approved&prev=", ["/projects"])).toBe(
      "/projects?status=approved&prev=",
    );
    expect(returnTarget("/projects/p-1#notices", ["/projects"])).toBe(
      "/projects/p-1#notices",
    );
  });

  it.each([
    ["another section", "/users?q=x"],
    ["another site", "https://evil.example/projects"],
    ["protocol-relative", "//evil.example/projects"],
    ["a lookalike prefix", "/projectsevil"],
    ["nothing", null],
  ])("refuses %s", (_why, from) => {
    expect(returnTarget(from, ["/projects"])).toBeNull();
  });
});
