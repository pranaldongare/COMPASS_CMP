/**
 * The way to report a personal data incident, shown plainly (2026-11-16).
 *
 * `/report-incident` is public: anybody may use it, signed in or not. It was
 * reachable only by the link the Privacy Office hands out, and by one small
 * line under the sign-in form. This is the same destination as a row nobody
 * has to look for, on the sign-in and sign-up cards; the signed-in menu has
 * its own entry.
 */
import { ChevronRight, ShieldAlert } from "lucide-react";
import Link from "next/link";

export function ReportIncidentLink() {
  return (
    <Link
      href="/report-incident"
      className="group flex items-center gap-3 rounded-xl border border-border bg-bg-subtle px-4 py-3 text-left hover:border-border-strong hover:bg-bg-inset"
    >
      <ShieldAlert className="size-5 shrink-0 text-warning-text" aria-hidden="true" />
      <span className="min-w-0 flex-1">
        <span className="block text-sm font-semibold text-text">
          Report a personal data incident
        </span>
        <span className="block text-xs text-text-muted">
          Lost, stolen or wrongly shared data. No account needed.
        </span>
      </span>
      <ChevronRight className="size-4 shrink-0 text-text-subtle" aria-hidden="true" />
    </Link>
  );
}
