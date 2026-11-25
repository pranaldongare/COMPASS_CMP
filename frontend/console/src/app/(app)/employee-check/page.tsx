/**
 * Employee check (ADR 0046): VerifyEmail, and the organisation's email domains.
 *
 * The administrator's page. Three things on it:
 *  - **VerifyEmail**: where the organisation's call is (the platform adds
 *    /VerifyEmail), its key - stored encrypted, never shown again - and the
 *    switch. Off, nothing is asked anywhere.
 *  - **The organisation's domains**: who is checked, and who counts as inside
 *    the organisation for breach and rights tickets. One list.
 *  - **Check an address**: ask about one address now, to see the call works;
 *    nothing is recorded against any account.
 *
 * What the answer does is said on the page in plain words, because it decides
 * who may sign in: on the console a leaver, or no answer, is refused (the
 * administrator never is); on the portal nobody is refused.
 */
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, CircleAlert, Trash2, XCircle } from "lucide-react";
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
  addDomain,
  employeeCheckKeys,
  getEmployeeCheck,
  removeDomain,
  saveEmployeeCheck,
  testAddress,
  type EmployeeCheckSettings,
  type EmployeeCheckTest,
} from "@/features/employee-check/api";
import { cn, formatDateTime } from "@/lib/format";
import { useToast } from "@/providers";

function said(err: unknown, fallback: string): string {
  return err && typeof err === "object" && "userMessage" in err
    ? (err as { userMessage: () => string }).userMessage()
    : fallback;
}

function SettingsForm({ saved }: { saved: EmployeeCheckSettings }) {
  const toast = useToast();
  const client = useQueryClient();
  const [address, setAddress] = React.useState(saved.base_url ?? "");
  const [header, setHeader] = React.useState(saved.api_key_header);
  const [key, setKey] = React.useState("");
  const [removeKey, setRemoveKey] = React.useState(false);
  const [enabled, setEnabled] = React.useState(saved.enabled);
  const [others, setOthers] = React.useState(saved.allow_other_domains);
  const [problem, setProblem] = React.useState<string | null>(null);

  const save = useMutation({
    mutationFn: saveEmployeeCheck,
    onSuccess: (now) => {
      client.setQueryData(employeeCheckKeys.settings, now);
      setKey("");
      setRemoveKey(false);
      setAddress(now.base_url ?? "");
      setHeader(now.api_key_header);
      setEnabled(now.enabled);
      setOthers(now.allow_other_domains);
      setProblem(null);
      toast.success(
        "Employee check saved",
        now.enabled ? "Switched on." : "Switched off: nothing is asked.",
      );
    },
    onError: (err) => setProblem(said(err, "Not saved. Try again in a moment.")),
  });

  function submit(event: React.FormEvent) {
    event.preventDefault();
    if (enabled && !address.trim()) {
      setProblem("Enter VerifyEmail's address before switching it on.");
      return;
    }
    save.mutate({
      base_url: address.trim() || null,
      api_key_header: header.trim() || "X-API-Key",
      enabled,
      allow_other_domains: others,
      ...(key.trim() ? { api_key: key.trim() } : removeKey ? { clear_api_key: true } : {}),
    });
  }

  return (
    <form method="post" onSubmit={submit} className="space-y-5" noValidate>
      <Field
        label="VerifyEmail address"
        hint='For example https://hr.example.internal/api. The platform adds /VerifyEmail to it and sends {"MySingleID": the email}.'
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
        label="API key"
        hint={
          saved.api_key_set
            ? "A key is stored. It is not shown again; type a new one to replace it."
            : "No key is stored. Leave this empty if VerifyEmail asks for none."
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
        hint="X-API-Key unless the organisation named another."
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

      <div className="flex items-start gap-2 text-sm">
        <input
          id="employee-check-enabled"
          type="checkbox"
          className="mt-0.5"
          checked={enabled}
          onChange={(e) => setEnabled(e.target.checked)}
          aria-describedby="employee-check-enabled-hint"
        />
        <div>
          <label htmlFor="employee-check-enabled" className="font-medium">
            Check employees at sign-in
          </label>
          <p id="employee-check-enabled-hint" className="text-xs text-text-muted">
            Off: nothing is asked, and sign-in works as it did before.
          </p>
        </div>
      </div>

      <div className="flex items-start gap-2 text-sm">
        <input
          id="employee-check-others"
          type="checkbox"
          className="mt-0.5"
          checked={others}
          onChange={(e) => setOthers(e.target.checked)}
          aria-describedby="employee-check-others-hint"
        />
        <div>
          <label htmlFor="employee-check-others" className="font-medium">
            Let staff on other domains sign in to the console
          </label>
          <p id="employee-check-others-hint" className="text-xs text-text-muted">
            For testing, with addresses such as cmp.local: they sign in without being
            checked. Switch this off before production, so only the organisation&apos;s own
            addresses can sign in. The administrator can always sign in.
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

function Domains({ saved }: { saved: EmployeeCheckSettings }) {
  const client = useQueryClient();
  const toast = useToast();
  const [domain, setDomain] = React.useState("");
  const [problem, setProblem] = React.useState<string | null>(null);
  const put = (domains: EmployeeCheckSettings["domains"]) =>
    client.setQueryData<EmployeeCheckSettings>(employeeCheckKeys.settings, (old) =>
      old ? { ...old, domains } : old,
    );
  const add = useMutation({
    mutationFn: addDomain,
    onSuccess: (domains) => {
      put(domains);
      setDomain("");
      setProblem(null);
      toast.success("Domain added");
    },
    onError: (err) => setProblem(said(err, "Not added. Try again in a moment.")),
  });
  const remove = useMutation({
    mutationFn: removeDomain,
    onSuccess: (domains) => {
      put(domains);
      setProblem(null);
      toast.success("Domain removed");
    },
    onError: (err) => setProblem(said(err, "Not removed. Try again in a moment.")),
  });

  return (
    <div className="space-y-4">
      {saved.domains.length === 0 ? (
        <p className="text-sm text-text-muted">
          No domains yet: nobody is checked, and nobody counts as inside the organisation
          for breach and rights tickets.
        </p>
      ) : (
        <ul
          className="divide-y divide-border rounded-lg border border-border"
          aria-label="Domains"
        >
          {saved.domains.map((d) => (
            <li
              key={d.domain}
              className="flex items-center justify-between gap-3 px-3 py-2"
            >
              <div className="min-w-0">
                <p className="font-mono text-sm text-text">{d.domain}</p>
                <p className="text-xs text-text-muted">
                  Added {formatDateTime(d.added_at)}
                  {d.added_by_name ? ` by ${d.added_by_name}` : ""}
                </p>
              </div>
              <Button
                variant="ghost"
                size="sm"
                aria-label={`Remove ${d.domain}`}
                disabled={remove.isPending}
                onClick={() => remove.mutate(d.domain)}
              >
                <Trash2 className="size-4" aria-hidden="true" />
              </Button>
            </li>
          ))}
        </ul>
      )}
      <form
        method="post"
        noValidate
        className="flex flex-wrap items-end gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          if (domain.trim()) add.mutate(domain.trim());
        }}
      >
        <div className="min-w-56 flex-1">
          <Field
            label="Add a domain"
            hint="Just the part after @, such as company.example. Its subdomains count too."
          >
            {(props) => (
              <Input
                {...props}
                autoComplete="off"
                spellCheck={false}
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                placeholder="company.example"
              />
            )}
          </Field>
        </div>
        <Button
          type="submit"
          variant="secondary"
          disabled={add.isPending || !domain.trim()}
        >
          Add
        </Button>
      </form>
      {problem && <Alert tone="danger">{problem}</Alert>}
    </div>
  );
}

function TryAddress({ enabled }: { enabled: boolean }) {
  const [email, setEmail] = React.useState("");
  const [answer, setAnswer] = React.useState<EmployeeCheckTest | null>(null);
  const [problem, setProblem] = React.useState<string | null>(null);
  const ask = useMutation({
    mutationFn: testAddress,
    onSuccess: (a) => {
      setAnswer(a);
      setProblem(null);
    },
    onError: (err) => {
      setAnswer(null);
      setProblem(said(err, "Could not ask. Try again in a moment."));
    },
  });
  const look = answer
    ? answer.result === "active"
      ? {
          Icon: CheckCircle2,
          cls: "border-success-border bg-success-subtle text-success-text",
        }
      : answer.result === "inactive"
        ? {
            Icon: XCircle,
            cls: "border-warning-border bg-warning-subtle text-warning-text",
          }
        : {
            Icon: CircleAlert,
            cls: "border-danger-border bg-danger-subtle text-danger-text",
          }
    : null;
  return (
    <div className="space-y-3">
      <form
        method="post"
        noValidate
        className="flex flex-wrap items-end gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          if (email.trim()) ask.mutate(email.trim());
        }}
      >
        <div className="min-w-56 flex-1">
          <Field label="Email address">
            {(props) => (
              <Input
                {...props}
                type="email"
                autoComplete="off"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="someone@company.example"
              />
            )}
          </Field>
        </div>
        <Button
          type="submit"
          variant="secondary"
          disabled={!enabled || ask.isPending || !email.trim()}
          title={enabled ? undefined : "Switch the check on first"}
        >
          {ask.isPending ? "Asking…" : "Ask VerifyEmail"}
        </Button>
      </form>
      {!enabled && (
        <p className="text-xs text-text-muted">
          Save an address and switch the check on to try it.
        </p>
      )}
      {answer && look && (
        <div
          role="status"
          className={cn("flex items-start gap-2 rounded-lg border p-3 text-sm", look.cls)}
        >
          <look.Icon className="mt-0.5 size-4 flex-none" aria-hidden="true" />
          <div>
            <p className="font-semibold">{answer.message}</p>
            {!answer.on_company_domain && (
              <p className="text-xs text-text-muted">
                This address is on none of the organisation&apos;s domains, so it would not
                be checked at sign-in.
              </p>
            )}
          </div>
        </div>
      )}
      {problem && <Alert tone="danger">{problem}</Alert>}
    </div>
  );
}

export default function EmployeeCheckPage() {
  const found = useQuery({
    queryKey: employeeCheckKeys.settings,
    queryFn: getEmployeeCheck,
  });
  return (
    <>
      <PageHeader
        title="Employee check"
        description="Whether somebody signing in on the organisation's domains is an active employee, asked of VerifyEmail."
      />
      <div className="max-w-2xl space-y-6">
        <Alert tone="info" title="What the answer does">
          <ul className="mt-1 list-disc space-y-1 pl-5">
            <li>
              <strong>Console:</strong> staff on the organisation&apos;s domains are checked
              when they sign in. An inactive employee is refused, and so is everyone on
              those domains while VerifyEmail cannot be reached. The administrator is never
              checked.
            </li>
            <li>
              <strong>Portal:</strong> a person is checked after signing in, and is never
              refused - a former employee keeps their rights over their consents. Links made
              for employees refuse somebody found not active.
            </li>
          </ul>
        </Alert>
        <Card>
          <CardHeader>
            <CardTitle>VerifyEmail</CardTitle>
            <p className="mt-1 text-xs text-text-muted">
              The platform sends the email address and nothing else. Every answer, and every
              change made here, is on the audit trail; the address asked about, the key and
              the address of VerifyEmail never are.
            </p>
          </CardHeader>
          <CardBody>
            {found.isLoading ? (
              <Skeleton className="h-64" />
            ) : found.error || !found.data ? (
              <Alert tone="danger">
                {said(found.error, "The settings could not be loaded.")}
              </Alert>
            ) : (
              <SettingsForm saved={found.data} />
            )}
          </CardBody>
        </Card>
        {found.data && (
          <>
            <Card>
              <CardHeader>
                <CardTitle>The organisation&apos;s email domains</CardTitle>
                <p className="mt-1 text-xs text-text-muted">
                  Who is checked, and who counts as inside the organisation for breach and
                  rights tickets.
                </p>
              </CardHeader>
              <CardBody>
                <Domains saved={found.data} />
              </CardBody>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Check an address</CardTitle>
                <p className="mt-1 text-xs text-text-muted">
                  Asks VerifyEmail now, to see the connection works. Nothing is recorded
                  against any account.
                </p>
              </CardHeader>
              <CardBody>
                <TryAddress enabled={found.data.enabled} />
              </CardBody>
            </Card>
          </>
        )}
      </div>
    </>
  );
}
