/**
 * Session state for the whole app.
 *
 * The session itself lives in an HttpOnly cookie the browser cannot read, so
 * "who am I" is answered by asking the server (`GET /auth/me`) rather than by
 * decoding a token. That is slower by one request on first paint and correct in
 * every other respect: the client cannot mint, extend or misread a session, and
 * a revoked session stops working immediately instead of when a JWT expires.
 *
 * `nav` comes from the server too. The frontend does not hold a second copy of
 * the permission matrix - a copy is a thing that drifts, and a drifted copy
 * shows people buttons that 403 on click.
 */
"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { usePathname, useRouter } from "next/navigation";
import * as React from "react";

import { apiGet, apiPost, setUnauthenticatedHandler } from "@/lib/api";
import { config } from "@/lib/config";
import { ApiError } from "@/lib/errors";
import { isPublicPath } from "@/lib/security/public-routes";
import type { Me, Role } from "@/types";

interface AuthContextValue {
  me: Me | null;
  isLoading: boolean;
  /** True once we know the answer either way - the signal to stop showing a
   *  skeleton and render either the app or the sign-in screen. */
  isResolved: boolean;
  /** Password accepted, MFA outstanding. */
  needsMfa: boolean;
  role: Role | null;
  can: (section: string) => boolean;
  refresh: () => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = React.createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const ctx = React.useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}

export const ME_QUERY_KEY = ["auth", "me"] as const;

/** Routes that render without a session. Everything else redirects. */
// The one list of public routes, shared with the proxy. A private copy here once
// omitted `/sign-up`, and every visitor to the registration page was redirected
// to sign in by the 401 their own "who am I" request produced.
const isPublic = isPublicPath;

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const queryClient = useQueryClient();

  const query = useQuery<Me, ApiError>({
    queryKey: ME_QUERY_KEY,
    queryFn: () => apiGet<Me>("/auth/me"),
    // On a public page there is nobody to identify, and asking produces a 401 in
    // the console on every consent-link visit.
    enabled: !isPublic(pathname),
    retry: false,
    staleTime: 60_000,
  });

  // Distinguish "not signed in" from "signed in, MFA outstanding". They look the
  // same in HTTP (both 401) and need completely different screens.
  //
  // Derived during render rather than mirrored into state by an effect: the
  // query already holds the answer, and a copy of it is a second source of truth
  // that is briefly wrong on every transition.
  const needsMfa = query.error instanceof ApiError && query.error.needsMfa;

  // One redirect for the whole app, wired into the HTTP client so a 401 from any
  // request lands here rather than in thirty catch blocks.
  React.useEffect(() => {
    setUnauthenticatedHandler(() => {
      queryClient.setQueryData(ME_QUERY_KEY, null);
      if (!isPublic(window.location.pathname)) {
        const next = encodeURIComponent(window.location.pathname + window.location.search);
        router.replace(`/sign-in?next=${next}`);
      }
    });
    return () => setUnauthenticatedHandler(null);
  }, [router, queryClient]);

  const refresh = React.useCallback(async () => {
    await queryClient.invalidateQueries({ queryKey: ME_QUERY_KEY });
  }, [queryClient]);

  const signOut = React.useCallback(async () => {
    try {
      await apiPost("/auth/logout");
    } catch {
      // A failed logout must still clear the client. The cookie may already be
      // dead, and leaving the UI signed in would be worse than a silent failure.
    }
    queryClient.clear();
    router.replace("/sign-in");
  }, [queryClient, router]);

  const me = query.data ?? null;

  const can = React.useCallback(
    (section: string) => Boolean(me?.nav.includes(section)),
    [me],
  );

  const value = React.useMemo<AuthContextValue>(
    () => ({
      me,
      isLoading: query.isLoading,
      isResolved: !query.isLoading && (query.isFetched || isPublic(pathname)),
      needsMfa,
      role: me?.role ?? null,
      can,
      refresh,
      signOut,
    }),
    [me, query.isLoading, query.isFetched, pathname, needsMfa, can, refresh, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/**
 * Gate for authenticated pages.
 *
 * Renders nothing until the session is resolved, so a protected page never
 * flashes its contents before the redirect - a flash of a project list is a
 * disclosure, however brief.
 */
export function RequireAuth({
  children,
  roles,
  fallback,
}: {
  children: React.ReactNode;
  roles?: Role[];
  fallback?: React.ReactNode;
}) {
  const { me, isResolved, needsMfa, signOut } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  React.useEffect(() => {
    if (!isResolved) return;
    if (needsMfa) {
      router.replace("/sign-in/verify");
      return;
    }
    if (!me) {
      router.replace(`/sign-in?next=${encodeURIComponent(pathname)}`);
    }
  }, [isResolved, me, needsMfa, router, pathname]);

  if (!isResolved || !me) return <>{fallback ?? null}</>;

  // The session cookie is shared with the data principal's portal when both
  // run on the same host, so somebody who signed in there and opened this
  // console arrives signed in. Nothing here is for her; say where she belongs.
  if (me.role === "data_subject") {
    return (
      <div className="mx-auto max-w-lg px-6 py-16 text-center">
        <h1 className="text-lg font-semibold">This console is for staff</h1>
        <p className="mt-2 text-sm text-text-muted">
          You are signed in as {me.full_name}. Your consents, your requests and
          your rights are on the consent portal.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <a
            href={config.subjectPortalUrl}
            className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white"
          >
            Go to the consent portal
          </a>
          <button
            type="button"
            onClick={() => void signOut()}
            className="rounded-lg border border-border px-4 py-2 text-sm font-medium"
          >
            Sign out
          </button>
        </div>
      </div>
    );
  }

  if (roles && !roles.includes(me.role)) {
    return (
      <div className="mx-auto max-w-lg px-6 py-16 text-center">
        <h1 className="text-lg font-semibold">Not available to your role</h1>
        <p className="mt-2 text-sm text-text-muted">
          You are signed in as {me.full_name}. This area is restricted, and the
          attempt has been recorded in the audit trail.
        </p>
      </div>
    );
  }

  return <>{children}</>;
}
