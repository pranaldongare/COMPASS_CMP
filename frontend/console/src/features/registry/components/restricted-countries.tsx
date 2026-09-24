/**
 * The Government's s.16 restricted-country list, as the Privacy Office keeps it
 * (S2-04).
 *
 * Data, not code: a country, the notification that restricts it, and - once -
 * when it was lifted. What belongs on it is Legal's to say; the platform holds
 * it and applies it to every export, refusing a row whose processor is in a
 * listed country. Shown to whoever the server says may write the list.
 */
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Globe2, Plus, Undo2 } from "lucide-react";
import * as React from "react";

import { Button, Card, CardBody, CardHeader, CardTitle, Field, Input } from "@/components/ui/primitives";
import { liftRestriction, listRestrictedCountries, restrictCountry } from "@/features/registry/api";
import { formatDate } from "@/lib/format";
import { useToast } from "@/providers";

const KEY = ["restricted-countries"] as const;

function messageOf(err: unknown, fallback: string): string {
  return err && typeof err === "object" && "userMessage" in err
    ? (err as { userMessage: () => string }).userMessage()
    : fallback;
}

export function RestrictedCountries() {
  const toast = useToast();
  const qc = useQueryClient();
  const list = useQuery({ queryKey: KEY, queryFn: listRestrictedCountries });
  const onChange = () => qc.invalidateQueries({ queryKey: KEY });
  const restrict = useMutation({ mutationFn: restrictCountry, onSuccess: onChange });
  const lift = useMutation({ mutationFn: liftRestriction, onSuccess: onChange });
  const [code, setCode] = React.useState("");
  const [notification, setNotification] = React.useState("");

  async function add() {
    try {
      await restrict.mutateAsync({ country_code: code, notification_ref: notification });
      setCode("");
      setNotification("");
      toast.success("Country restricted", "Exports whose rows would go there are refused from now on.");
    } catch (err) {
      toast.error("Not restricted", messageOf(err, "The server refused."));
    }
  }

  async function doLift(uuid: string, country: string) {
    try {
      await lift.mutateAsync(uuid);
      toast.success(`${country} lifted`, "Exports there are judged by the purposes again.");
    } catch (err) {
      toast.error("Not lifted", messageOf(err, "The server refused."));
    }
  }

  return (
    <Card className="mt-6">
      <CardHeader>
        <CardTitle>
          <Globe2 className="mr-2 inline size-4" aria-hidden="true" />
          Restricted countries (s.16)
        </CardTitle>
        <p className="mt-1 text-xs text-text-muted">
          Countries the Government has notified that personal data may not be transferred to. An
          export is refused if any row would go to a processor there. Record each with the
          notification that lists it.
        </p>
      </CardHeader>
      <CardBody className="space-y-4">
        {list.data && list.data.length > 0 ? (
          <ul className="divide-y divide-border text-sm">
            {list.data.map((r) => (
              <li key={r.country_uuid} className="flex flex-wrap items-center justify-between gap-2 py-2">
                <span>
                  <span className="font-mono font-medium">{r.country_code}</span>
                  <span className="ml-2 text-text-muted">{r.notification_ref}</span>
                  <span className="ml-2 text-xs text-text-subtle">since {formatDate(r.listed_at)}</span>
                </span>
                <Button variant="ghost" size="sm" loading={lift.isPending} onClick={() => doLift(r.country_uuid, r.country_code)}>
                  <Undo2 className="size-4" />
                  Lift
                </Button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-text-muted">{list.isLoading ? "Loading…" : "No country is restricted."}</p>
        )}
        <div className="grid gap-2 sm:grid-cols-[6rem_minmax(0,1fr)_auto]">
          <Field label="Country" hint="Two letters">
            {(p) => <Input {...p} value={code} maxLength={2} onChange={(e) => setCode(e.target.value)} />}
          </Field>
          <Field label="Notification" hint="As it is cited">
            {(p) => <Input {...p} value={notification} onChange={(e) => setNotification(e.target.value)} />}
          </Field>
          <div className="flex items-end">
            <Button variant="secondary" size="sm" disabled={code.trim().length !== 2 || !notification.trim()} loading={restrict.isPending} onClick={add}>
              <Plus className="size-4" />
              Restrict
            </Button>
          </div>
        </div>
      </CardBody>
    </Card>
  );
}
