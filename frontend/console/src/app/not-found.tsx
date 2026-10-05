/**
 * An address that leads nowhere.
 *
 * The framework's bare 404 offered no way back (UX review 2026-10-05). This
 * says the page is not here, without guessing why, and gives the two places
 * somebody most likely meant: their dashboard, and the manual.
 */
import Link from "next/link";

export default function NotFound() {
  return (
    <main id="main" className="grid min-h-dvh place-items-center px-4 py-12">
      <div className="max-w-md text-center">
        <p className="text-sm font-medium text-text-muted">404</p>
        <h1 className="mt-2 text-xl font-semibold">We can&apos;t find that page</h1>
        <p className="mt-2 text-sm text-text-muted">
          The address may be mistyped, or the page may have moved.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <Link
            href="/dashboard"
            className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-contrast hover:bg-accent-hover"
          >
            Go to your dashboard
          </Link>
          <Link
            href="/help"
            className="rounded-lg border border-border px-4 py-2 text-sm font-medium hover:bg-surface-hover"
          >
            Open the help manual
          </Link>
        </div>
      </div>
    </main>
  );
}
