/**
 * Nomination - section 14. Registering, and seeing whether it is usable.
 *
 * Two facts are shown more prominently than the rest, because they are the
 * ones that matter when she cannot be asked: whether the nominee has
 * accepted (a nomination he has never heard of cannot safely be acted on),
 * and which of her rights he may exercise. Revocation is one click; it is her
 * decision and it stays hers.
 */
"use client";

import { UserRoundCheck, UserRoundX } from "lucide-react";
import * as React from "react";

import { CheckboxGroup, FormError, useApiForm } from "@/components/forms";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Field,
  Input,
  Mono,
  Skeleton,
} from "@/components/ui/primitives";
import { REQUEST_TYPE_COPY } from "@/features/rights/components/copy";
import { useNominate, useRevokeNomination } from "@/features/rights/mutations";
import { useMyNominations } from "@/features/rights/queries";
import {
  nominationSchema,
  type NominationForm as NominationFormValues,
  type NominationValues,
} from "@/features/rights/schemas";
import { formatDate } from "@/lib/format";
import { useToast } from "@/providers";
import type { Nomination } from "@/types";
import { RIGHTS_REQUEST_TYPES } from "@/types";

const STATUS: Record<Nomination["status"], { label: string; tone: "neutral" | "info" | "success" | "warning" | "danger" }> = {
  pending: { label: "Waiting for the nominee to accept", tone: "warning" },
  active: { label: "In place", tone: "success" },
  declined: { label: "Declined by the nominee", tone: "neutral" },
  revoked: { label: "Revoked", tone: "neutral" },
};

export function NominationCard() {
  const nominations = useMyNominations();
  const live = nominations.data?.find((n) => n.status === "pending" || n.status === "active");
  const past = (nominations.data ?? []).filter((n) => n !== live);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <UserRoundCheck className="size-4" aria-hidden="true" />
          Somebody to act for you
        </CardTitle>
        <p className="mt-1 text-xs text-text-muted">
          Section 14. A person you name, while you are well, to exercise these rights if you
          die or cannot act. Nothing is in effect until they accept, and you can revoke it at
          any time.
        </p>
      </CardHeader>
      <CardBody className="space-y-4">
        {nominations.isLoading && <Skeleton className="h-24" />}
        {nominations.error && (
          <Alert tone="danger">{nominations.error.userMessage()}</Alert>
        )}
        {live ? <LiveNomination nomination={live} /> : nominations.data && <NominationForm />}
        {past.length > 0 && (
          <details className="text-sm">
            <summary className="cursor-pointer text-text-muted">Earlier nominations</summary>
            <ul className="mt-2 space-y-1">
              {past.map((n) => (
                <li key={n.nomination_uuid} className="flex flex-wrap items-center gap-2 text-xs text-text-muted">
                  <span className="font-medium text-text">{n.nominee_name}</span>
                  <Badge tone={STATUS[n.status].tone} dot={false}>
                    {STATUS[n.status].label}
                  </Badge>
                  <span>{formatDate(n.revoked_at ?? n.declined_at ?? n.created_at)}</span>
                </li>
              ))}
            </ul>
          </details>
        )}
      </CardBody>
    </Card>
  );
}

function LiveNomination({ nomination: n }: { nomination: Nomination }) {
  const toast = useToast();
  const revoke = useRevokeNomination();

  async function end() {
    try {
      await revoke.mutateAsync(n.nomination_uuid);
      toast.success("Nomination revoked", `${n.nominee_name} can no longer act for you.`);
    } catch {
      toast.error("Could not revoke", "Nothing has changed.");
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium">{n.nominee_name}</p>
          <p className="text-xs text-text-muted">
            {[n.nominee_mobile, n.nominee_email].filter(Boolean).join(" · ")}
          </p>
        </div>
        <Badge tone={STATUS[n.status].tone}>{STATUS[n.status].label}</Badge>
      </div>

      <p className="text-xs text-text-muted">
        May ask for:{" "}
        {n.rights.map((r) => REQUEST_TYPE_COPY[r].label.toLowerCase()).join(", ")}.
      </p>

      {n.status === "pending" ? (
        <Alert tone="warning">
          <p className="text-sm">
            Not yet usable. We have sent {n.nominee_name} a link to accept
            {n.accept_expires_at && ` - it expires on ${formatDate(n.accept_expires_at)}`}.
            A nomination they have not accepted cannot be acted on.
          </p>
        </Alert>
      ) : (
        <Alert tone="info">
          <p className="text-sm">
            In place. If the time comes, {n.nominee_name} will identify themselves with the
            contact you recorded, evidence the event, and the request will run as normal.
          </p>
          {/* Shown here too: the nominee was sent it on acceptance, and this is
              the place the nominee page tells them to ask if they lost it. */}
          <p className="mt-2 text-xs text-text-muted">
            Their nomination reference: <Mono className="break-all">{n.nomination_uuid}</Mono>
          </p>
        </Alert>
      )}

      <Button variant="subtle" size="sm" loading={revoke.isPending} onClick={end}>
        <UserRoundX className="size-4" aria-hidden="true" />
        Revoke this nomination
      </Button>
    </div>
  );
}

function NominationForm() {
  const toast = useToast();
  const nominate = useNominate();
  const form = useApiForm<NominationValues, NominationFormValues>(nominationSchema, {
    nominee_name: "",
    nominee_mobile: "",
    nominee_email: "",
    rights: [...RIGHTS_REQUEST_TYPES],
  });
  const rights = form.watch("rights") as string[];

  const submit = form.submit(async (values) => {
    const created = await nominate.mutateAsync(values);
    toast.success(
      "Nomination recorded",
      `We have asked ${created.nominee_name} to accept. It is not usable until they do.`,
    );
    form.reset();
  });

  return (
    <form method="post" onSubmit={submit} noValidate className="space-y-4">
      <FormError message={form.formError} />
      <Field label="Their name" required error={form.formState.errors.nominee_name?.message}>
        {(p) => <Input {...p} autoComplete="off" {...form.register("nominee_name")} />}
      </Field>
      <Field
        label="Their mobile"
        hint="We will send the acceptance link there, and later verify them against it - not against whatever they tell us then."
        required
        error={form.formState.errors.nominee_mobile?.message}
      >
        {(p) => <Input {...p} type="tel" autoComplete="off" {...form.register("nominee_mobile")} />}
      </Field>
      <Field
        label="Their email"
        hint="Optional. The link goes here too, and they may prove either contact."
        error={form.formState.errors.nominee_email?.message}
      >
        {(p) => <Input {...p} type="email" autoComplete="off" {...form.register("nominee_email")} />}
      </Field>
      <CheckboxGroup
        label="Which of your rights they may exercise"
        hint="You can name somebody to ask for access without letting them ask for erasure."
        error={form.formState.errors.rights?.message}
        options={RIGHTS_REQUEST_TYPES.map((t) => ({
          value: t,
          label: `${REQUEST_TYPE_COPY[t].label} (${REQUEST_TYPE_COPY[t].section})`,
        }))}
        value={rights}
        onChange={(next) =>
          form.setValue("rights", next as NominationFormValues["rights"], { shouldValidate: true })
        }
      />
      <Button type="submit" variant="primary" loading={nominate.isPending}>
        Nominate
      </Button>
    </form>
  );
}
