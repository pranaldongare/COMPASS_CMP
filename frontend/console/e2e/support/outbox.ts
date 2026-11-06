/**
 * The dev outbox the API writes one-time codes to.
 *
 * A single append-only *file*, not a directory of messages - the console
 * transport writes one log. Getting that wrong is what produced the original
 * failure: `readdirSync` on a file throws ENOTDIR, the catch swallowed it, and
 * the message said "no code in the dev outbox", which was true and useless.
 *
 * Only exists in a local deployment; a real one sends mail. Absence is why the
 * roles that need a code skip rather than fail.
 */
import { expect } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

export const OUTBOX =
  process.env.E2E_OUTBOX ??
  path.join(__dirname, "..", "..", "..", "..", "backend", "api", "var", "outbox.log");

/** Why no code was found. Kept so the failure message can say something. */
let outboxProblem = "not read yet";

/**
 * The newest code the outbox holds **for one recipient**.
 *
 * Recipient-aware because the outbox is a single append-only log and the setup
 * projects run in parallel: reading "the newest six-digit number" hands the
 * data principal the DPO's code, which the server then rejects as invalid. The
 * failure reads like a broken sign-in and is nothing of the sort.
 *
 * Walks forward rather than backwards, because the `to:` header precedes the
 * code in each block, so the recipient is only known once it has been seen.
 */
export function latestCodeFor(recipient: string): string | null {
  try {
    const lines = fs.readFileSync(OUTBOX, "utf8").split(/\r?\n/);
    let current: string | null = null;
    let found: string | null = null;
    for (const line of lines) {
      const to = /\bto:\s*(\S+)/.exec(line);
      if (to) {
        current = to[1];
        continue;
      }
      // The words are the office's to change (Messages, in the console), so
      // the reader matches the shapes the default templates use rather than
      // one sentence: "code is 123456", a code on a line of its own, or a line
      // or subject that opens with the code ("123456 is your...", "123456
      // confirms..."). A reference such as RR-2026-000042 never matches.
      const code =
        /code is (\d{6})/.exec(line) ??
        /^\s*(\d{6})\s*$/.exec(line) ??
        // ...allowing the organisation's name in front of the code, which is
        // how every SMS opens ("COMPASS: 123456 confirms...").
        /^(?:subject: )?(?:[^:\n]{1,60}: )?(\d{6}) (?:is your|confirms|signs)/.exec(line);
      if (code && current?.toLowerCase() === recipient.toLowerCase()) found = code[1];
    }
    if (!found) {
      outboxProblem = `read ${OUTBOX} (${lines.length} lines), no code addressed to ${recipient}`;
    }
    return found;
  } catch (error) {
    outboxProblem = `could not read ${OUTBOX}: ${(error as Error).message}`;
    return null;
  }
}

/**
 * Prefer a newly-arrived code; settle for the one already there.
 *
 * Two failure modes pull in opposite directions, and both were hit here.
 *
 * Reading "the latest code" succeeds instantly against a previous run's, which
 * the server rejects as expired - so newness has to be waited for.
 *
 * But the API allows only a handful of codes per contact per hour, and that is
 * a control working correctly rather than something the suite should disable.
 * Once it bites, no new code is written and waiting for one never succeeds.
 *
 * So: wait for a new one, and if none comes, use the newest that exists. It has
 * a ten-minute life, so it is very often still good - and if it is not, the
 * verify step fails with the server's own message rather than a timeout that
 * says nothing.
 */
export async function freshCode(
  recipient: string,
  previous: string | null,
): Promise<string> {
  await expect
    .poll(() => latestCodeFor(recipient), { timeout: 15_000 })
    .not.toBe(previous)
    .catch(() => {
      /* Rate-limited, most likely. Fall through to whatever is there. */
    });
  const code = latestCodeFor(recipient);
  if (!code) throw new Error(`no one-time code for ${recipient}: ${outboxProblem}`);
  return code;
}

/** One message in the outbox: who it went to, and what it said. */
export interface OutboxEntry {
  channel: string;
  to: string;
  subject: string;
  /** The files it carried, as "name (type, N bytes)". */
  attached: string[];
  body: string;
}

/** Where the outbox ends now: `entriesSince` reads what is written after it. */
export function outboxMark(): number {
  return fs.statSync(OUTBOX).size;
}

/**
 * What was written after a mark, as messages.
 *
 * From the mark rather than from the top, because the outbox of a machine that
 * has run the suites for months is hundreds of megabytes, and because "who was
 * mailed" is a question about this run alone. An entry opens with a line of
 * equals signs, then `<when>  [<channel>]  to: <address>`.
 */
export function entriesSince(mark: number): OutboxEntry[] {
  const size = fs.statSync(OUTBOX).size;
  const bytes = Buffer.alloc(Math.max(0, size - mark));
  const handle = fs.openSync(OUTBOX, "r");
  try {
    fs.readSync(handle, bytes, 0, bytes.length, mark);
  } finally {
    fs.closeSync(handle);
  }
  const entries: OutboxEntry[] = [];
  for (const block of bytes.toString("utf8").split(/^={78}$/m)) {
    const head = /^\S+\s+\[(\w+)\]\s+to:\s*(\S+)/m.exec(block);
    if (!head) continue;
    const [top, ...rest] = block.split(/^-{78}$/m);
    entries.push({
      channel: head[1],
      to: head[2],
      subject: /^subject: (.*)$/m.exec(top)?.[1] ?? "",
      attached: [...top.matchAll(/^attached: (.*)$/gm)].map((m) => m[1]),
      body: rest.join("").trim(),
    });
  }
  return entries;
}
