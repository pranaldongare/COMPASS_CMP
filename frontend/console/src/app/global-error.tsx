"use client";

/**
 * The root layout itself failed, so this replaces it - with its own <html>
 * and <body>, and the styles imported here because the layout that imports
 * them is the thing that broke.
 */
import "./globals.css";

import { RouteError } from "@/components/feedback/route-states";

export default function GlobalError(props: {
  error: Error & { digest?: string };
  retry: () => void;
}) {
  return (
    <html lang="en">
      <body>
        <main id="main">
          <RouteError {...props} />
        </main>
      </body>
    </html>
  );
}
