/**
 * Root route.
 *
 * This portal has one signed-in audience, the data principal, and her home is
 * her consent list. Anyone without a session is sent to sign-in by the proxy.
 * Redirecting server-side avoids a flash of an empty page before the client
 * router works out where to go.
 */
import { redirect } from "next/navigation";

export default function RootPage(): never {
  redirect("/my-consents");
}
