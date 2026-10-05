/**
 * A production build names the other portal's address, or does not build.
 *
 * Both portals send people across - a data principal who lands on the console
 * to her portal, staff who land on the portal to the console - and both read
 * the address from a `NEXT_PUBLIC_*` variable inlined at build time. It used
 * to default to `http://localhost:300x`, so a deployment that forgot it built
 * cleanly and sent people to their own computers (review 2026-10-01, ARCH-6).
 */
import { describe, expect, it } from "vitest";

import { deploymentProblems, deploymentWarnings } from "@/lib/config/deployment";

const NAME = "NEXT_PUBLIC_OTHER_PORTAL_URL";

describe("deploymentProblems", () => {
  it("refuses an address that was never set", () => {
    const [problem] = deploymentProblems({}, [NAME]);
    expect(problem).toContain(NAME);
    expect(problem).toContain("not set");
  });

  it("refuses an empty or relative address", () => {
    expect(deploymentProblems({ [NAME]: "  " }, [NAME])).toHaveLength(1);
    expect(deploymentProblems({ [NAME]: "/portal" }, [NAME])).toHaveLength(1);
  });

  it("refuses an address that is not http or https", () => {
    expect(deploymentProblems({ [NAME]: "javascript:alert(1)" }, [NAME])).toHaveLength(1);
  });

  it("accepts a real address", () => {
    expect(deploymentProblems({ [NAME]: "https://consent.example.org" }, [NAME])).toEqual([]);
  });

  it("accepts localhost when somebody wrote it down - a local production build", () => {
    expect(deploymentProblems({ [NAME]: "http://localhost:3001" }, [NAME])).toEqual([]);
  });
});

describe("deploymentWarnings", () => {
  it("says so when a production build points at this machine or at plain http", () => {
    expect(deploymentWarnings({ [NAME]: "http://localhost:3001" }, [NAME])).toHaveLength(1);
    expect(deploymentWarnings({ [NAME]: "http://consent.example.org" }, [NAME])).toHaveLength(1);
    expect(deploymentWarnings({ [NAME]: "https://consent.example.org" }, [NAME])).toEqual([]);
  });
});
