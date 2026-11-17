/**
 * This machine's address, read once, and the addresses built from it.
 *
 * `APP_BASE_URL` (http://<ip> or https://<name>, no port) is written in the
 * repository's `.env`, beside CONSOLE_PORT, PORTAL_PORT and API_PORT. The API
 * reads the same file. `next.config.ts` calls this before anything else, so
 * the other portal's address, the API's and the origins the dev server
 * accepts all follow one line. A value given by its own name in this app's
 * env file wins over what is built.
 *
 * With APP_BASE_URL not set, nothing is built: `next dev` keeps its local
 * defaults and a production build is still refused without the other
 * portal's address (review ARCH-6).
 *
 * Plain functions over an environment object and the file's text, so they
 * can be tested without a server (`addresses.test.ts`).
 */

type Env = Record<string, string | undefined>;

export type Addresses = {
  /** `http://<ip>:<port>` of the console; undefined when APP_BASE_URL is not set. */
  console?: string;
  /** The data principal's portal, likewise. */
  portal?: string;
  /** Where the API listens, as this server reaches it. */
  api: string;
  /** The hosts people use, for the dev server's allowed origins. */
  hosts: string[];
};

/** `KEY=value` lines of an env file. Comments and blank lines are skipped;
 *  quotes around a value are dropped. */
export function parseEnvFile(text: string): Env {
  const out: Env = {};
  for (const line of text.split(/\r?\n/)) {
    const match = /^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$/.exec(line);
    if (!match || line.trimStart().startsWith("#")) continue;
    out[match[1]] = match[2].replace(/^(['"])(.*)\1$/, "$2");
  }
  return out;
}

function port(raw: string | undefined, fallback: number): number {
  const n = Number(raw ?? "");
  return raw !== undefined && raw.trim() !== "" && Number.isInteger(n) && n >= 0
    ? n
    : fallback;
}

/** The addresses, from this app's environment over the repository's file. */
export function addresses(env: Env, repositoryEnv: Env = {}): Addresses {
  const read = (name: string) =>
    env[name]?.trim() || repositoryEnv[name]?.trim() || undefined;
  const whole = (name: string, defaultPort = 0) => {
    const raw = read(name)?.replace(/\/+$/, "");
    if (!raw) return undefined;
    let url: URL;
    try {
      url = new URL(raw);
    } catch {
      throw new Error(`${name} must be http(s)://<ip or name>[:port]`);
    }
    if (!/^https?:$/.test(url.protocol) || url.pathname !== "/") {
      throw new Error(`${name} must be http(s)://<ip or name>[:port], no path`);
    }
    // `http://<ip>` gets that part's port; one written with a port, or an
    // https name, is used as it is.
    return url.protocol === "http:" && !url.port && defaultPort
      ? `${raw}:${defaultPort}`
      : raw;
  };
  const api =
    read("API_ORIGIN") ??
    whole("API_URL", port(read("API_PORT"), 8000)) ??
    `http://127.0.0.1:${port(read("API_PORT"), 8000)}`;
  const base = read("APP_BASE_URL")?.replace(/\/+$/, "");
  let at: ((p: number) => string) | undefined;
  if (base) {
    let url: URL;
    try {
      url = new URL(base);
    } catch {
      throw new Error("APP_BASE_URL must be http://<ip or name> or https://<name>");
    }
    if (!/^https?:$/.test(url.protocol) || url.port || url.pathname !== "/") {
      throw new Error(
        "APP_BASE_URL must be http://<ip or name> or https://<name>, no port, no path",
      );
    }
    at = (p: number) => (p ? `${base}:${p}` : base);
  }
  // Each part's whole address when it is given (three machines), else the
  // one address and that part's port.
  const consoleUrl =
    whole("CONSOLE_URL", port(read("CONSOLE_PORT"), 3000)) ??
    at?.(port(read("CONSOLE_PORT"), 3000));
  const portalUrl =
    whole("PORTAL_URL", port(read("PORTAL_PORT"), 3001)) ??
    at?.(port(read("PORTAL_PORT"), 3001));
  const hosts = [
    ...new Set([consoleUrl, portalUrl].flatMap((u) => (u ? [new URL(u).hostname] : []))),
  ];
  return { console: consoleUrl, portal: portalUrl, api, hosts };
}
