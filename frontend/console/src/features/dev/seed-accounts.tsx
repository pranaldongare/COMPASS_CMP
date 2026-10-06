/**
 * Development only: the seed accounts, with their password, on the sign-in
 * page (2026-10-06) - so nobody has to ask for it.
 *
 * The API lists only the seed's own logins (`DEV_SEED_LOGINS`) that are
 * active and still have the seed password, checked against the password each
 * has now: one whose password was changed, and any account the seed did not
 * make - a breach-only login, a test's leftovers - is never shown. **Use**
 * fills the form; signing in is still a password and an emailed code.
 *
 * Behind the same switch as the one-time-code popup: shown only while
 * `NEXT_PUBLIC_DEV_SHOW_CODES=true` here and `DEV_SHOW_CODES=true` on the API,
 * which refuses the setting outside local and test - without it the route
 * does not exist, and this renders nothing.
 */
"use client";

import { KeyRound } from "lucide-react";
import * as React from "react";

import { Button } from "@/components/ui/primitives";
import { reachableApiBase } from "@/lib/api/client";
import { config } from "@/lib/config";
import { DEV_CODES_ON } from "@/lib/dev/dev-client";

interface SeedAccount {
  login: string;
  role: string;
  role_title: string;
}

interface SeedAccounts {
  password: string | null;
  accounts: SeedAccount[];
}

export function SeedAccounts({ onUse }: { onUse: (login: string, password: string) => void }) {
  const [data, setData] = React.useState<SeedAccounts | null>(null);

  React.useEffect(() => {
    if (!DEV_CODES_ON) return;
    let live = true;
    // Plain fetch, as the code popup does: no session yet, and nothing here
    // is for the API client's decryption or 401 handling.
    const base = reachableApiBase(config.apiUrl, window.location.hostname);
    fetch(`${base}/dev/seed-accounts`, { cache: "no-store" })
      .then((r) => (r.ok ? (r.json() as Promise<SeedAccounts>) : null))
      .then((body) => {
        if (live) setData(body);
      })
      .catch(() => {
        // The API is not up yet, or the route is off: show nothing.
      });
    return () => {
      live = false;
    };
  }, []);

  if (!DEV_CODES_ON || !data?.password || data.accounts.length === 0) return null;
  const password = data.password;

  return (
    <details className="rounded-lg border border-dashed border-warning-border bg-warning-subtle/40 p-3 text-sm">
      <summary className="flex cursor-pointer items-center gap-2 font-medium text-warning-text">
        <KeyRound className="size-4" aria-hidden="true" />
        Development accounts ({data.accounts.length})
      </summary>
      <p className="mt-2 text-xs text-text-muted">
        Seed accounts still on the seed password <code className="font-mono text-text">{password}</code>. An account
        whose password was changed is not listed. Development only.
      </p>
      <ul className="mt-2 max-h-64 divide-y divide-border overflow-y-auto">
        {data.accounts.map((a) => (
          <li key={a.login} className="flex items-center justify-between gap-2 py-1.5">
            <span className="min-w-0">
              <span className="block truncate font-mono text-xs">{a.login}</span>
              <span className="block text-2xs text-text-subtle">{a.role_title}</span>
            </span>
            <Button
              type="button"
              variant="secondary"
              size="sm"
              aria-label={`Use ${a.login}`}
              onClick={() => onUse(a.login, password)}
            >
              Use
            </Button>
          </li>
        ))}
      </ul>
    </details>
  );
}
