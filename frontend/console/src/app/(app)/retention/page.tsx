/**
 * Retention (ADR 0047): the officer's register of what is running out.
 *
 * Two kinds of review, never mixed with rights or breach tickets:
 *  - **Consent validity** - consents whose validity is about to run out. The
 *    owner is asked at once whether the people should be invited to consent
 *    again, while the project is active.
 *  - **Data retention** - consents that ended (withdrawn or run out) whose
 *    retention has passed, counted from the consent's end. The owner and
 *    every processor holding the data are asked to erase it, anonymise it
 *    with a reason, or keep it with a reason and a date.
 *
 * One row per project, purpose and month, with the people counted. The
 * tiles filter the list; the settings say when people are reminded and told.
 */
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import Link from "next/link";
import * as React from "react";

import { PageHeader } from "@/components/layout/app-shell";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  EmptyState,
  Field,
  Input,
  Select,
  Skeleton,
  Table,
  TableSkeleton,
  Td,
  Th,
  Tr,
} from "@/components/ui/primitives";
import { Tab, TabList, TabPanel, Tabs, useHashTab } from "@/components/ui/tabs";
import {
  KIND_LABEL,
  STATUS_LABEL,
  getRetentionSettings,
  listReviews,
  refreshReviews,
  retentionKeys,
  said,
  saveRetentionSettings,
  type RetentionReview,
  type RetentionSettings,
  type ReviewStatus,
} from "@/features/retention/api";
import { cn, formatDate, formatDateTime } from "@/lib/format";
import { useToast } from "@/providers";

const STATUS_TONE: Record<ReviewStatus, "neutral" | "warning" | "info" | "success"> = {
  upcoming: "neutral",
  due: "warning",
  in_progress: "info",
  closed: "success",
};

function Tiles({
  reviews,
  status,
  onPick,
}: {
  reviews: RetentionReview[];
  status: string;
  onPick: (s: string) => void;
}) {
  const count = (s: ReviewStatus) => reviews.filter((r) => r.status === s).length;
  const toReview = reviews.reduce((n, r) => n + r.actions_to_review, 0);
  const tiles: { key: string; label: string; value: number; hint: string }[] = [
    {
      key: "upcoming",
      label: "Upcoming",
      value: count("upcoming"),
      hint: "Seen, not due yet",
    },
    { key: "due", label: "Due", value: count("due"), hint: "Nobody asked yet" },
    {
      key: "in_progress",
      label: "In progress",
      value: count("in_progress"),
      hint: `${toReview} answer${toReview === 1 ? "" : "s"} to review`,
    },
    {
      key: "closed",
      label: "Closed",
      value: count("closed"),
      hint: "Settled, on the record",
    },
  ];
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {tiles.map((t) => (
        <button
          key={t.key}
          type="button"
          aria-pressed={status === t.key}
          onClick={() => onPick(status === t.key ? "" : t.key)}
          className={cn(
            "bg-bg-raised rounded-xl border p-4 text-left transition hover:border-accent-border",
            status === t.key
              ? "border-accent-border ring-2 ring-accent-subtle"
              : "border-border",
          )}
        >
          <p className="text-xs font-medium text-text-muted">{t.label}</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums">{t.value}</p>
          <p className="mt-1 text-xs text-text-muted">{t.hint}</p>
        </button>
      ))}
    </div>
  );
}

function Register() {
  const toast = useToast();
  const client = useQueryClient();
  const [kind, setKind] = React.useState("");
  const [status, setStatus] = React.useState("");
  const all = useQuery({
    queryKey: retentionKeys.reviews(kind, ""),
    queryFn: () => listReviews(kind, ""),
  });
  const refresh = useMutation({
    mutationFn: refreshReviews,
    onSuccess: (r) => {
      void client.invalidateQueries({ queryKey: retentionKeys.all });
      toast.success(
        "Looked again",
        `${r.reviews_made} new review${r.reviews_made === 1 ? "" : "s"}, ${r.people_added} people added, ${r.actions_opened} asked.`,
      );
    },
    onError: (err) => toast.error("Not done", said(err, "Try again in a moment.")),
  });
  const rows = (all.data ?? []).filter((r) => !status || r.status === status);

  return (
    <div className="space-y-4">
      {all.data && <Tiles reviews={all.data} status={status} onPick={setStatus} />}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="w-56">
          <Field label="Kind">
            {(props) => (
              <Select {...props} value={kind} onChange={(e) => setKind(e.target.value)}>
                <option value="">Both kinds</option>
                <option value="validity">{KIND_LABEL.validity}</option>
                <option value="retention">{KIND_LABEL.retention}</option>
              </Select>
            )}
          </Field>
        </div>
        <Button
          variant="secondary"
          onClick={() => refresh.mutate()}
          disabled={refresh.isPending}
        >
          <RefreshCw className="size-4" aria-hidden="true" />
          {refresh.isPending ? "Looking…" : "Look again now"}
        </Button>
      </div>
      <Card>
        {all.isLoading ? (
          <CardBody>
            <TableSkeleton rows={5} cols={6} />
          </CardBody>
        ) : all.error ? (
          <CardBody>
            <Alert tone="danger">
              {said(all.error, "The reviews could not be loaded.")}
            </Alert>
          </CardBody>
        ) : rows.length === 0 ? (
          <CardBody>
            <EmptyState
              title="Nothing is running out"
              description="A review appears here when consents for a purpose are about to run out, or their data must go."
            />
          </CardBody>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <thead>
                <tr>
                  <Th>Reference</Th>
                  <Th>Project and purpose</Th>
                  <Th>Kind</Th>
                  <Th>Falls due</Th>
                  <Th className="text-right">People</Th>
                  <Th>Answers</Th>
                  <Th>Status</Th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <Tr key={r.review_uuid}>
                    <Td>
                      <Link
                        href={`/retention/${r.review_uuid}`}
                        className="font-mono text-xs text-accent-text hover:underline"
                      >
                        {r.reference}
                      </Link>
                    </Td>
                    <Td>
                      <p className="font-medium">{r.project_name}</p>
                      <p className="text-xs text-text-muted">
                        {r.purpose_code} · {r.purpose_name}
                      </p>
                    </Td>
                    <Td>{KIND_LABEL[r.kind]}</Td>
                    <Td>
                      {formatDate(r.first_due_at)}
                      {r.last_due_at && r.last_due_at !== r.first_due_at && (
                        <span className="text-text-muted">
                          {" "}
                          – {formatDate(r.last_due_at)}
                        </span>
                      )}
                    </Td>
                    <Td className="text-right tabular-nums">
                      {r.people}
                      {r.held > 0 && (
                        <span className="block text-xs text-text-muted">
                          {r.held} on hold
                        </span>
                      )}
                    </Td>
                    <Td className="text-xs">
                      {r.actions === 0
                        ? "Nobody asked yet"
                        : `${r.actions - r.actions_open - r.actions_to_review} of ${r.actions} settled`}
                      {r.actions_to_review > 0 && (
                        <span className="block font-medium text-info-text">
                          {r.actions_to_review} to review
                        </span>
                      )}
                    </Td>
                    <Td>
                      <Badge tone={STATUS_TONE[r.status]} dot>
                        {STATUS_LABEL[r.status]}
                      </Badge>
                    </Td>
                  </Tr>
                ))}
              </tbody>
            </Table>
          </div>
        )}
      </Card>
    </div>
  );
}

function SettingsForm({ saved }: { saved: RetentionSettings }) {
  const toast = useToast();
  const client = useQueryClient();
  const [days, setDays] = React.useState(saved.reminder_days.join(", "));
  const [hours, setHours] = React.useState(String(saved.notice_hours));
  const [act, setAct] = React.useState(String(saved.action_days));
  const [esc, setEsc] = React.useState(String(saved.escalate_after_days));
  const [problem, setProblem] = React.useState<string | null>(null);
  const save = useMutation({
    mutationFn: saveRetentionSettings,
    onSuccess: (now) => {
      client.setQueryData(retentionKeys.settings, now);
      setProblem(null);
      toast.success("Retention settings saved");
    },
    onError: (err) => setProblem(said(err, "Not saved. Try again in a moment.")),
  });

  function submit(event: React.FormEvent) {
    event.preventDefault();
    const reminder = days
      .split(/[\s,]+/)
      .filter(Boolean)
      .map(Number);
    if (
      !reminder.length ||
      reminder.some((d) => !Number.isInteger(d) || d < 1 || d > 365)
    ) {
      setProblem("Reminder days are whole numbers from 1 to 365, separated by commas.");
      return;
    }
    save.mutate({
      reminder_days: reminder,
      notice_hours: Number(hours),
      action_days: Number(act),
      escalate_after_days: Number(esc),
    });
  }

  return (
    <form method="post" noValidate onSubmit={submit} className="space-y-5">
      <Field
        label="Remind the people responsible, days before"
        hint="For example 90, 30, 7. Each reminder goes once."
      >
        {(props) => (
          <Input {...props} value={days} onChange={(e) => setDays(e.target.value)} />
        )}
      </Field>
      <Field
        label="Tell each person, hours before their data is erased"
        hint="Only for purposes that say so; 0 tells nobody."
      >
        {(props) => (
          <Input
            {...props}
            type="number"
            min={0}
            max={720}
            value={hours}
            onChange={(e) => setHours(e.target.value)}
          />
        )}
      </Field>
      <Field label="Days the people asked have to answer">
        {(props) => (
          <Input
            {...props}
            type="number"
            min={1}
            max={365}
            value={act}
            onChange={(e) => setAct(e.target.value)}
          />
        )}
      </Field>
      <Field
        label="Tell the Privacy Office when an answer is this many days late"
        hint="The one asked is reminded on the day it falls due."
      >
        {(props) => (
          <Input
            {...props}
            type="number"
            min={1}
            max={365}
            value={esc}
            onChange={(e) => setEsc(e.target.value)}
          />
        )}
      </Field>
      {problem && <Alert tone="danger">{problem}</Alert>}
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs text-text-muted">
          {saved.updated_by_name
            ? `Last changed by ${saved.updated_by_name}, ${formatDateTime(saved.updated_at)}.`
            : "Not changed since it was set up."}
        </p>
        <Button type="submit" disabled={save.isPending}>
          {save.isPending ? "Saving…" : "Save"}
        </Button>
      </div>
    </form>
  );
}

function Settings() {
  const found = useQuery({
    queryKey: retentionKeys.settings,
    queryFn: getRetentionSettings,
  });
  return (
    <Card className="max-w-2xl">
      <CardHeader>
        <CardTitle>Reminders, notice and deadlines</CardTitle>
        <p className="mt-1 text-xs text-text-muted">
          The same for both offices. Every change is on the audit trail.
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
  );
}

const TABS = ["reviews", "settings"] as const;

export default function RetentionPage() {
  const [tab, setTab] = useHashTab(TABS, "reviews");
  return (
    <>
      <PageHeader title="Retention" />
      <Tabs value={tab} onValueChange={setTab} label="Retention" layout="underline">
        <TabList>
          <Tab value="reviews">Reviews</Tab>
          <Tab value="settings">Settings</Tab>
        </TabList>
        <TabPanel value="reviews" className="pt-4">
          <Register />
        </TabPanel>
        <TabPanel value="settings" className="pt-4">
          <Settings />
        </TabPanel>
      </Tabs>
    </>
  );
}
