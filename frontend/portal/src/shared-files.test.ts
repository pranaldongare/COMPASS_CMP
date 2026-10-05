/**
 * The files both portals share are still the same in both (review ARCH-4).
 *
 * `frontend/shared-files.txt` lists them and says why. A file changed in one
 * portal and not the other fails here, naming the file; change both, or take
 * the file off the list in the same commit and say why it now differs.
 */
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

const FRONTEND = path.resolve(__dirname, "..", "..");
const APPS = ["console", "portal"] as const;

function listed(): string[] {
  return readFileSync(path.join(FRONTEND, "shared-files.txt"), "utf8")
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line && !line.startsWith("#"));
}

describe("files shared between the portals", () => {
  const files = listed();

  it("lists something, so an empty list cannot pass for agreement", () => {
    expect(files.length).toBeGreaterThan(50);
  });

  it("are byte-identical in both", () => {
    const missing: string[] = [];
    const differ: string[] = [];
    for (const file of files) {
      const [a, b] = APPS.map((app) => path.join(FRONTEND, app, file));
      if (!existsSync(a) || !existsSync(b)) {
        missing.push(file);
        continue;
      }
      if (!readFileSync(a).equals(readFileSync(b))) differ.push(file);
    }
    expect(missing, "listed but missing from a portal").toEqual([]);
    expect(differ, "changed in one portal and not the other").toEqual([]);
  });
});
