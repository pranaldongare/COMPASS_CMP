/**
 * Development only: a popup with each one-time code the moment it is sent.
 *
 * Locally, codes are not emailed or texted - the API's console transports
 * write them to `var/outbox.log`. Reading that file is fine at the machine
 * running the API and impossible from a phone or a second machine opening
 * the portal by IP. With `NEXT_PUBLIC_DEV_SHOW_CODES=true` here and
 * `DEV_SHOW_CODES=true` on the API, this polls `/api/dev/codes` and shows
 * each new code with who it went to.
 *
 * Never in a real deployment: the API refuses the setting outside local and
 * test, and without it `/dev/codes` does not exist - a 404 here stops the
 * polling for good. A code shown on the screen that asks for it proves
 * nothing about who holds the phone.
 */
"use client";

import { Copy, KeyRound, X } from "lucide-react";
import * as React from "react";

import { reachableApiBase } from "@/lib/api/client";
import { copyText } from "@/lib/browser";
import { config } from "@/lib/config";

interface SentCode {
  to: string;
  channel: string;
  code: string;
  at: number;
}

const ON = process.env.NEXT_PUBLIC_DEV_SHOW_CODES === "true";
const POLL_MS = 2000;
const SHOW_MS = 120_000;

export function DevCodePopup() {
  const [shown, setShown] = React.useState<SentCode[]>([]);
  const [copied, setCopied] = React.useState<string | null>(null);
  const seen = React.useRef<Set<string>>(new Set());
  // When this page started listening; set in the effect, not during render.
  const since = React.useRef<number>(0);

  React.useEffect(() => {
    if (!ON) return;
    since.current = Date.now() / 1000;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;

    async function poll() {
      if (stopped) return;
      if (document.visibilityState === "visible") {
        try {
          // Plain fetch, same origin: not the API client, whose 401 handling
          // and decryption have nothing to do with this.
          const base = reachableApiBase(config.apiUrl, window.location.hostname);
          const response = await fetch(`${base}/dev/codes`, { cache: "no-store" });
          if (response.status === 404) {
            console.warn(
              "[dev codes] /dev/codes is not on the API - set DEV_SHOW_CODES=true there and restart it.",
            );
            return; // off on the API side: stop for good
          }
          if (response.ok) {
            const body = (await response.json()) as { items: SentCode[] };
            const fresh = body.items.filter((c) => {
              const key = `${c.at}:${c.to}:${c.code}`;
              if (c.at < since.current || seen.current.has(key)) return false;
              seen.current.add(key);
              return true;
            });
            if (fresh.length) setShown((now) => [...fresh, ...now].slice(0, 4));
          }
        } catch {
          // The API is restarting, or not up yet. Try again next tick.
        }
      }
      timer = setTimeout(poll, POLL_MS);
    }

    void poll();
    return () => {
      stopped = true;
      clearTimeout(timer);
    };
  }, []);

  // Each popup goes away on its own after two minutes; a code is spent
  // well before then.
  React.useEffect(() => {
    if (!shown.length) return;
    const t = setInterval(() => {
      const cutoff = Date.now() / 1000 - SHOW_MS / 1000;
      setShown((now) => now.filter((c) => c.at >= cutoff));
    }, 5000);
    return () => clearInterval(t);
  }, [shown.length]);

  if (!ON || !shown.length) return null;

  return (
    <div
      role="region"
      aria-label="Development one-time codes"
      className="no-print fixed top-4 right-4 z-[60] flex w-[min(22rem,calc(100vw-2rem))] flex-col gap-2"
    >
      {shown.map((c) => {
        const key = `${c.at}:${c.to}:${c.code}`;
        return (
          <div
            key={key}
            role="status"
            className="rounded-xl border border-amber-400 bg-amber-50 px-4 py-3 text-amber-950 shadow-[var(--shadow-pop)] dark:bg-amber-950 dark:text-amber-50"
          >
            <div className="flex items-start gap-3">
              <KeyRound className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
              <div className="min-w-0 flex-1">
                <p className="text-xs font-semibold tracking-wide uppercase">
                  Development only · {c.channel}
                </p>
                <p className="mt-0.5 truncate text-xs" title={c.to}>
                  Code sent to {c.to}
                </p>
                <p className="mt-1 font-mono text-2xl font-semibold tracking-[0.3em]">
                  {c.code}
                </p>
              </div>
              <button
                type="button"
                aria-label="Dismiss"
                className="rounded p-1 hover:bg-amber-100 dark:hover:bg-amber-900"
                onClick={() => setShown((now) => now.filter((x) => x !== c))}
              >
                <X className="size-4" />
              </button>
            </div>
            <button
              type="button"
              className="mt-2 inline-flex items-center gap-1.5 rounded-md border border-amber-400 px-2 py-1 text-xs font-medium hover:bg-amber-100 dark:hover:bg-amber-900"
              onClick={async () => {
                if (await copyText(c.code)) {
                  setCopied(key);
                  setTimeout(() => setCopied(null), 1500);
                }
              }}
            >
              <Copy className="size-3.5" aria-hidden="true" />
              {copied === key ? "Copied" : "Copy code"}
            </button>
          </div>
        );
      })}
    </div>
  );
}
