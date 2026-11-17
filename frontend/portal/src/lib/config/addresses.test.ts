import { describe, expect, it } from "vitest";

import { addresses, parseEnvFile } from "./addresses";

describe("addresses", () => {
  it("builds both portals and the dev host from the one address", () => {
    const file = parseEnvFile("# where\nAPP_BASE_URL=http://10.1.2.3/\nPORTAL_PORT=4001\n");
    expect(addresses({}, file)).toEqual({
      console: "http://10.1.2.3:3000",
      portal: "http://10.1.2.3:4001",
      api: "http://127.0.0.1:8000",
      host: "10.1.2.3",
    });
  });

  it("lets this app's own environment win over the repository's file", () => {
    const got = addresses(
      {
        APP_BASE_URL: "https://cmp.example.org",
        CONSOLE_PORT: "0",
        API_ORIGIN: "http://api:9000",
      },
      { APP_BASE_URL: "http://10.1.2.3" },
    );
    expect(got.console).toBe("https://cmp.example.org");
    expect(got.api).toBe("http://api:9000");
  });

  it("builds nothing without the address, so the build's own check still runs", () => {
    expect(addresses({}, {})).toEqual({ api: "http://127.0.0.1:8000" });
  });

  it("refuses an address with a port or a path", () => {
    expect(() => addresses({ APP_BASE_URL: "http://10.1.2.3:3000" })).toThrow(/no port/);
    expect(() => addresses({ APP_BASE_URL: "http://10.1.2.3/app" })).toThrow(/no path/);
  });
});
