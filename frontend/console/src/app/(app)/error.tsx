"use client";

/** A page inside the signed-in area failed: the shell stays, the page says so. */
import { RouteError } from "@/components/feedback/route-states";

export default function AppError(props: { error: Error & { digest?: string }; retry: () => void }) {
  return <RouteError {...props} />;
}
