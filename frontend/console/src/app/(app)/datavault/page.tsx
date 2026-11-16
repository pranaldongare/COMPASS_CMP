/**
 * DataVault connection (0070, 0071): where the platform reaches DataVault.
 *
 * The administrator's page. The addresses could not be written into the
 * code, so they are set here with the key DataVault asks for: the lookup's,
 * and the one erasures and consent changes go to. The key is stored
 * encrypted and never shown again: the page says only that one is set, and a
 * new one replaces it. Switched off, the platform calls nothing and a rights
 * request says DataVault is not set up.
 *
 * How a person, a consent, a project and a request are named in every call
 * is one switch: the numbers the console shows (the request by its
 * reference), or uuids. And consent changes go out by themselves only once
 * they are switched on here; what was on record before that is never sent.
 */
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as React from "react";

import { PageHeader } from "@/components/layout/app-shell";
import {
  Alert,
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  Field,
  Input,
  Skeleton,
} from "@/components/ui/primitives";
import {
  datavaultKeys,
  getConnection,
  saveConnection,
  type DataVaultConnection,
  type DataVaultIdFormat,
} from "@/features/datavault/api";
import { formatDateTime } from "@/lib/format";
import { useToast } from "@/providers";

function said(err: unknown, fallback: string): string {
  return err && typeof err === "object" && "userMessage" in err
    ? (err as { userMessage: () => string }).userMessage()
    : fallback;
}

function ConnectionForm({ saved }: { saved: DataVaultConnection }) {
  const toast = useToast();
  const client = useQueryClient();
  const [address, setAddress] = React.useState(saved.base_url ?? "");
  const [erasureAddress, setErasureAddress] = React.useState(saved.erasure_url ?? "");
  const [header, setHeader] = React.useState(saved.api_key_header);
  const [key, setKey] = React.useState("");
  const [removeKey, setRemoveKey] = React.useState(false);
  const [enabled, setEnabled] = React.useState(saved.enabled);
  const [idFormat, setIdFormat] = React.useState<DataVaultIdFormat>(saved.id_format);
  const [changes, setChanges] = React.useState(saved.consent_changes);
  const [problem, setProblem] = React.useState<string | null>(null);

  const save = useMutation({
    mutationFn: saveConnection,
    onSuccess: (now) => {
      client.setQueryData(datavaultKeys.connection, now);
      setKey("");
      setRemoveKey(false);
      setAddress(now.base_url ?? "");
      setErasureAddress(now.erasure_url ?? "");
      setHeader(now.api_key_header);
      setEnabled(now.enabled);
      setIdFormat(now.id_format);
      setChanges(now.consent_changes);
      setProblem(null);
      toast.success(
        "DataVault connection saved",
        now.enabled ? "Switched on." : "Switched off: nothing is called.",
      );
    },
    onError: (err) => setProblem(said(err, "Not saved. Try again in a moment.")),
  });

  function submit(event: React.FormEvent) {
    event.preventDefault();
    if (enabled && !address.trim()) {
      setProblem("Enter DataVault's address before switching it on.");
      return;
    }
    if (changes && !erasureAddress.trim()) {
      setProblem(
        "Enter the erasure address before switching consent changes on: they go there.",
      );
      return;
    }
    save.mutate({
      base_url: address.trim() || null,
      erasure_url: erasureAddress.trim() || null,
      api_key_header: header.trim() || "X-API-Key",
      enabled,
      id_format: idFormat,
      consent_changes: changes,
      ...(key.trim() ? { api_key: key.trim() } : removeKey ? { clear_api_key: true } : {}),
    });
  }

  return (
    <form method="post" onSubmit={submit} className="space-y-5" noValidate>
      <Field
        label="DataVault address"
        hint="For example https://datavault.example.internal/api. The platform adds /lookup to it."
      >
        {(props) => (
          <Input
            {...props}
            type="url"
            inputMode="url"
            autoComplete="off"
            spellCheck={false}
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            placeholder="https://"
          />
        )}
      </Field>
      <Field
        label="Erasure address"
        hint="Where erasures and consent changes go. The platform adds /erasures and /consent-changes to it. Leave it empty while DataVault's team has not given it: nothing is erased or told."
      >
        {(props) => (
          <Input
            {...props}
            type="url"
            inputMode="url"
            autoComplete="off"
            spellCheck={false}
            value={erasureAddress}
            onChange={(e) => setErasureAddress(e.target.value)}
            placeholder="https://"
          />
        )}
      </Field>
      <Field
        label="API key"
        hint={
          saved.api_key_set
            ? "A key is stored. It is not shown again; type a new one to replace it."
            : "No key is stored. Leave this empty if DataVault asks for none."
        }
      >
        {(props) => (
          <Input
            {...props}
            type="password"
            autoComplete="new-password"
            value={key}
            onChange={(e) => {
              setKey(e.target.value);
              if (e.target.value) setRemoveKey(false);
            }}
            placeholder={saved.api_key_set ? "Stored" : ""}
          />
        )}
      </Field>
      {saved.api_key_set && !key && (
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={removeKey}
            onChange={(e) => setRemoveKey(e.target.checked)}
          />
          Remove the stored key
        </label>
      )}
      <Field
        label="Header the key is sent in"
        hint="X-API-Key unless DataVault's team named another."
      >
        {(props) => (
          <Input
            {...props}
            autoComplete="off"
            spellCheck={false}
            value={header}
            onChange={(e) => setHeader(e.target.value)}
          />
        )}
      </Field>
      <fieldset className="space-y-2">
        <legend className="text-sm font-medium">How IDs are sent</legend>
        <p className="text-xs text-text-muted">
          For the person, the consent and the project, in every call. Each asset goes back
          with the consent DataVault gave for it, whichever is chosen.
        </p>
        <div className="flex items-start gap-2 text-sm">
          <input
            id="datavault-ids-numeric"
            type="radio"
            name="datavault-id-format"
            className="mt-0.5"
            checked={idFormat === "numeric"}
            onChange={() => setIdFormat("numeric")}
            aria-describedby="datavault-ids-numeric-hint"
          />
          <div>
            <label htmlFor="datavault-ids-numeric" className="font-medium">
              Numeric IDs
            </label>
            <p id="datavault-ids-numeric-hint" className="text-xs text-text-muted">
              The Person ID, Consent ID and Project ID the console shows, and the
              request&apos;s reference (RR-…).
            </p>
          </div>
        </div>
        <div className="flex items-start gap-2 text-sm">
          <input
            id="datavault-ids-uuid"
            type="radio"
            name="datavault-id-format"
            className="mt-0.5"
            checked={idFormat === "uuid"}
            onChange={() => setIdFormat("uuid")}
            aria-describedby="datavault-ids-uuid-hint"
          />
          <div>
            <label htmlFor="datavault-ids-uuid" className="font-medium">
              UUIDs
            </label>
            <p id="datavault-ids-uuid-hint" className="text-xs text-text-muted">
              The platform&apos;s own identifiers, for when DataVault keys its assets by
              them.
            </p>
          </div>
        </div>
      </fieldset>
      <div className="flex items-start gap-2 text-sm">
        <input
          id="datavault-consent-changes"
          type="checkbox"
          className="mt-0.5"
          checked={changes}
          onChange={(e) => setChanges(e.target.checked)}
          aria-describedby="datavault-consent-changes-hint"
        />
        <div>
          <label htmlFor="datavault-consent-changes" className="font-medium">
            Tell DataVault of consent changes
          </label>
          <p id="datavault-consent-changes-hint" className="text-xs text-text-muted">
            A withdrawal in full or in part, a consent given again, and a validity that runs
            out go to DataVault by themselves, as a restriction on the assets - never a
            deletion. Nothing on record before this is first switched on is sent.
          </p>
        </div>
      </div>
      <div className="flex items-start gap-2 text-sm">
        <input
          id="datavault-enabled"
          type="checkbox"
          className="mt-0.5"
          checked={enabled}
          onChange={(e) => setEnabled(e.target.checked)}
          aria-describedby="datavault-enabled-hint"
        />
        <div>
          <label htmlFor="datavault-enabled" className="font-medium">
            Switched on
          </label>
          <p id="datavault-enabled-hint" className="text-xs text-text-muted">
            Off: the platform calls nothing, and a rights request says DataVault is not set
            up.
          </p>
        </div>
      </div>
      {problem && <Alert tone="danger">{problem}</Alert>}
      <div className="flex flex-wrap items-center gap-3">
        <Button type="submit" disabled={save.isPending}>
          {save.isPending ? "Saving…" : "Save"}
        </Button>
        {saved.updated_at && (
          <span className="text-xs text-text-muted">
            Last changed {formatDateTime(saved.updated_at)}
            {saved.updated_by_name ? ` by ${saved.updated_by_name}` : ""}
          </span>
        )}
      </div>
    </form>
  );
}

/** How the consent-change queue stands: counts and times, nothing of anybody. */
function ConsentChangeQueue({ saved }: { saved: DataVaultConnection }) {
  if (!saved.consent_changes && saved.consent_changes_waiting === 0) return null;
  return (
    <Card>
      <CardHeader>
        <CardTitle>Consent changes</CardTitle>
        <p className="mt-1 text-xs text-text-muted">
          Each is tried until DataVault answers. Every one is on the audit trail, against
          the consent, the person and the project.
        </p>
      </CardHeader>
      <CardBody className="space-y-2 text-sm">
        <p>
          {saved.consent_changes_waiting === 0
            ? "Nothing waiting."
            : `${saved.consent_changes_waiting} waiting to be delivered.`}
          {saved.consent_changes_last_delivered_at && (
            <span className="text-text-muted">
              {" "}
              Last delivered {formatDateTime(saved.consent_changes_last_delivered_at)}.
            </span>
          )}
        </p>
        {saved.consent_changes_last_failure && saved.consent_changes_waiting > 0 && (
          <Alert tone="warning" title="The last try was not delivered">
            {saved.consent_changes_last_failure} It is tried again by itself.
          </Alert>
        )}
        {!saved.consent_changes && (
          <p className="text-xs text-text-muted">
            Switched off: nothing is sent until consent changes are switched on again.
          </p>
        )}
      </CardBody>
    </Card>
  );
}

export default function DataVaultConnectionPage() {
  const found = useQuery({ queryKey: datavaultKeys.connection, queryFn: getConnection });
  return (
    <>
      <PageHeader
        title="DataVault connection"
        description="Where the platform asks DataVault what it holds of a person, tells it to erase, and tells it of consent changes."
      />
      <div className="max-w-2xl space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Connection</CardTitle>
            <p className="mt-1 text-xs text-text-muted">
              On a check the platform sends the request and the person, named as chosen
              below, and nothing else. Every call, and every change made here, is on the
              audit trail; the addresses and the key never are.
            </p>
          </CardHeader>
          <CardBody>
            {found.isLoading ? (
              <Skeleton className="h-64" />
            ) : found.error || !found.data ? (
              <Alert tone="danger">
                {said(found.error, "The connection could not be loaded.")}
              </Alert>
            ) : (
              <ConnectionForm saved={found.data} />
            )}
          </CardBody>
        </Card>
        {found.data && <ConsentChangeQueue saved={found.data} />}
      </div>
    </>
  );
}
