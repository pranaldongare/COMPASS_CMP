/**
 * What a production build must be told, checked when it is built.
 *
 * Read by `next.config.ts` in the production-build phase only, so `next dev`
 * and `next start` are untouched. A `NEXT_PUBLIC_*` value is inlined into the
 * bundle at build time; a wrong one cannot be fixed by restarting the server,
 * only by building again - which is why it is refused at the build.
 *
 * Plain functions over an environment object, so they can be tested without
 * a build (`deployment.test.ts`).
 */

type Env = Record<string, string | undefined>;

/** Reasons the build must stop. Empty when every named address is usable. */
export function deploymentProblems(env: Env, names: readonly string[]): string[] {
  const problems: string[] = [];
  for (const name of names) {
    const raw = env[name]?.trim();
    if (!raw) {
      problems.push(
        `${name} is not set. It is the other portal's address, inlined into this ` +
          `build; without it people are sent to http://localhost.`,
      );
      continue;
    }
    let url: URL;
    try {
      url = new URL(raw);
    } catch {
      problems.push(`${name} is not an absolute URL: it must start https:// (or http://).`);
      continue;
    }
    if (url.protocol !== "https:" && url.protocol !== "http:") {
      problems.push(`${name} must be an http(s) address.`);
    }
  }
  return problems;
}

/** Usable, but almost certainly not what a deployment meant. Printed, not fatal. */
export function deploymentWarnings(env: Env, names: readonly string[]): string[] {
  const warnings: string[] = [];
  for (const name of names) {
    const raw = env[name]?.trim();
    if (!raw) continue;
    let url: URL;
    try {
      url = new URL(raw);
    } catch {
      continue;
    }
    if (["localhost", "127.0.0.1", "[::1]"].includes(url.hostname)) {
      warnings.push(`${name} points at this machine (${url.host}). Fine for a local build only.`);
    } else if (url.protocol === "http:") {
      warnings.push(`${name} is plain http; a deployment should use https.`);
    }
  }
  return warnings;
}
