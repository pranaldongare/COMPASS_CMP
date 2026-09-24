/**
 * An account whose age nobody knows is asked for it before anything else.
 *
 * Most accounts were created through a consent link that never asked for a date
 * of birth, and section 9 turns on it: until the platform knows, it cannot tell
 * an adult from a child, and the server refuses a new consent from either
 * (`age_required`). The decision taken for those accounts is to ask at the next
 * sign-in rather than wait until a consent fails, so every page here holds for
 * the answer - except the two a person must always be able to reach.
 * Withdrawing a consent is not a consent, and neither is exercising a right, so
 * `/my-consents` and `/my-requests` stay open without it and carry a reminder
 * instead.
 *
 * `is_minor` is the server's answer, derived from `minor_until`: **null means
 * unknown, not adult**. A known child is not held here - the server refuses
 * what it must refuse, and says so where it happens.
 *
 * Like `RequireSection`, this is not a security boundary: the gate that matters
 * is the server's refusal to record the consent. This is the product asking the
 * question at the moment it can be answered, instead of at a counter where the
 * person is trying to consent.
 */
"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { CalendarCheck } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import * as React from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Alert, Button, Card, CardBody, Field, Input } from "@/components/ui/primitives";
import { useUpdateMe } from "@/features/account/mutations";
import { ApiError } from "@/lib/errors";
import { useAuth } from "@/providers";
import { EARLIEST_DOB, dateOfBirth, today } from "@/schemas/primitives";

/** The pages that never wait for a date of birth. */
const ALWAYS_OPEN = ["/my-consents", "/my-requests"] as const;

function alwaysOpen(pathname: string): boolean {
  return ALWAYS_OPEN.some((p) => pathname === p || pathname.startsWith(`${p}/`));
}

export function RequireAge({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { me } = useAuth();

  // Known, either way, or not resolved yet: nothing to ask.
  if (!me || me.is_minor !== null) return <>{children}</>;

  if (alwaysOpen(pathname)) {
    return (
      <>
        <Alert tone="info" className="mb-4" title="We need your date of birth">
          You can withdraw a consent or make a request without it, but we need it before you
          give a new consent.{" "}
          <Link href="/" className="underline underline-offset-2">
            Add it now
          </Link>
          .
        </Alert>
        {children}
      </>
    );
  }

  return <DateOfBirthPrompt />;
}

const schema = z.object({ dob: dateOfBirth });
type Values = z.infer<typeof schema>;

export function DateOfBirthPrompt({ onSaved }: { onSaved?: () => void } = {}) {
  const { refresh } = useAuth();
  const update = useUpdateMe();
  const [error, setError] = React.useState<string | null>(null);
  const form = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { dob: "" } });

  const submit = form.handleSubmit(async ({ dob }) => {
    setError(null);
    try {
      await update.mutateAsync({ dob });
      await refresh();
      onSaved?.();
    } catch (err) {
      setError(err instanceof ApiError ? err.userMessage() : "Could not save your date of birth.");
    }
  });

  return (
    <div className="mx-auto max-w-lg py-10">
      <Card>
        <CardBody className="space-y-4">
          <div className="flex items-start gap-3">
            <CalendarCheck className="mt-0.5 size-5 text-accent-text" aria-hidden="true" />
            <div>
              <h1 className="text-lg font-semibold">Your date of birth</h1>
              <p className="mt-1 text-sm text-text-muted">
                The law protects people under 18 differently, and we do not have your date of
                birth yet. We need it before you can give a new consent.
              </p>
            </div>
          </div>

          {error && <Alert tone="danger">{error}</Alert>}

          <form method="post" onSubmit={submit} className="space-y-4" noValidate>
            <Field label="Date of birth" error={form.formState.errors.dob?.message} required>
              {(p) => (
                <Input
                  {...p}
                  {...form.register("dob")}
                  type="date"
                  max={today()}
                  min={EARLIEST_DOB}
                  autoComplete="bday"
                />
              )}
            </Field>
            <Button type="submit" variant="primary" disabled={form.formState.isSubmitting}>
              Save and continue
            </Button>
          </form>

          <p className="text-xs text-text-subtle">
            You can still{" "}
            <Link href="/my-consents" className="underline underline-offset-2">
              withdraw a consent
            </Link>{" "}
            or{" "}
            <Link href="/my-requests" className="underline underline-offset-2">
              make a request
            </Link>{" "}
            without it.
          </p>
        </CardBody>
      </Card>
    </div>
  );
}
