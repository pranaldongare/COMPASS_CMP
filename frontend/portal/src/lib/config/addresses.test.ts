import { describe, expect, it } from "vitest";

import { addresses, parseEnvFile } from "./addresses";

describe("addresses", () => {
  it("builds both portals and the dev host from the one address", () => {
    const file = parseEnvFile("# where\nAPP_BASE_URL=http://10.1.2.3/\nPORTAL_PORT=4001\n");
    expect(addresses({}, file)).toEqual({
      console: "http://10.1.2.3:3000",
      portal: "http://10.1.2.3:4001",
      api: "http://127.0.0.1:8000",
      hosts: ["10.1.2.3"],
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
    expect(addresses({}, {})).toEqual({
      console: undefined,
      portal: undefined,
      api: "http://127.0.0.1:8000",
      hosts: [],
    });
  });

  it("takes each part's whole address when the three are on different machines", () => {
    const file = parseEnvFile(
      "APP_BASE_URL=http://10.0.0.1\nPORTAL_URL=http://10.0.0.2\nAPI_URL=http://10.0.0.3\n",
    );
    expect(addresses({}, file)).toEqual({
      console: "http://10.0.0.1:3000",
      portal: "http://10.0.0.2:3001",
      api: "http://10.0.0.3:8000",
      hosts: ["10.0.0.1", "10.0.0.2"],
    });
  });

  it("keeps a port written in API_URL, the scheme's default included (ARCH-7)", () => {
    expect(addresses({ API_URL: "http://api.example:80" }).api).toBe(
      "http://api.example:80",
    );
    expect(addresses({ API_URL: "http://api.example:80/", API_PORT: "8100" }).api).toBe(
      "http://api.example:80",
    );
    expect(addresses({ API_URL: "http://api.example:9000" }).api).toBe(
      "http://api.example:9000",
    );
    expect(addresses({ API_URL: "https://api.example:443" }).api).toBe(
      "https://api.example:443",
    );
    expect(addresses({ API_URL: "http://[2001:db8::1]:80" }).api).toBe(
      "http://[2001:db8::1]:80",
    );
  });

  it("gives API_URL without a port the API's port, on http only", () => {
    expect(addresses({ API_URL: "http://api.example" }).api).toBe(
      "http://api.example:8000",
    );
    expect(addresses({ API_URL: "http://api.example", API_PORT: "8100" }).api).toBe(
      "http://api.example:8100",
    );
    expect(addresses({ API_URL: "https://api.example" }).api).toBe("https://api.example");
    expect(addresses({ API_URL: "http://[2001:db8::1]" }).api).toBe(
      "http://[2001:db8::1]:8000",
    );
  });

  it("keeps API_ORIGIN over API_URL over the local default", () => {
    expect(
      addresses({
        API_ORIGIN: "http://origin.example:7000",
        API_URL: "http://api.example:80",
      }).api,
    ).toBe("http://origin.example:7000");
    expect(addresses({}, { API_URL: "http://api.example:80" }).api).toBe(
      "http://api.example:80",
    );
  });

  it("keeps a port written in CONSOLE_URL and PORTAL_URL, the default included (ARCH-7)", () => {
    const got = addresses({
      APP_BASE_URL: "http://192.0.2.1",
      CONSOLE_URL: "http://console.example:80",
      PORTAL_URL: "http://portal.example:4001",
    });
    expect(got.console).toBe("http://console.example:80");
    expect(got.portal).toBe("http://portal.example:4001");
    expect(got.hosts).toEqual(["console.example", "portal.example"]);
  });

  it("gives CONSOLE_URL and PORTAL_URL without a port their part's port, on http only", () => {
    const got = addresses({
      CONSOLE_URL: "http://console.example",
      PORTAL_URL: "https://portal.example",
      CONSOLE_PORT: "3100",
    });
    expect(got.console).toBe("http://console.example:3100");
    expect(got.portal).toBe("https://portal.example");
    expect(addresses({ PORTAL_URL: "http://portal.example" }).portal).toBe(
      "http://portal.example:3001",
    );
  });

  it("prefers CONSOLE_URL and PORTAL_URL over APP_BASE_URL and the ports", () => {
    const got = addresses({
      APP_BASE_URL: "http://192.0.2.1",
      PORTAL_URL: "http://portal.example:80",
    });
    expect(got.console).toBe("http://192.0.2.1:3000");
    expect(got.portal).toBe("http://portal.example:80");
  });

  it("refuses a whole address that is not one or has a path", () => {
    expect(() => addresses({ API_URL: "not a url" })).toThrow(
      "API_URL must be http(s)://<ip or name>[:port]",
    );
    expect(() => addresses({ PORTAL_URL: "http://portal.example/app" })).toThrow(/no path/);
  });

  it("refuses an address with a port or a path", () => {
    expect(() => addresses({ APP_BASE_URL: "http://10.1.2.3:3000" })).toThrow(/no port/);
    expect(() => addresses({ APP_BASE_URL: "http://10.1.2.3/app" })).toThrow(/no path/);
  });
});
