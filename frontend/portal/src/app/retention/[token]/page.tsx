/**
 * The link a processor outside the organisation receives for a retention
 * review (ADR 0047).
 *
 * Consents of people whose data the processor holds have ended, and the time
 * the data may be kept has passed. The processor says here what it did:
 * erased it, anonymised it (with the reason), kept it (with the reason and a
 * date), or holds none. The link alone shows which review it is and where a
 * code will go; the code goes to the address the link was sent to and opens
 * the review here for an hour. Every failure of the link is the same "not
 * valid" screen, as for every link on the portal. No person is named.
 */
"use client";

import { LogOut } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import * as React from "react";

import { BrandMark } from "@/components/ui/graphics";
import {
  Alert,
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  DescriptionItem,
  DescriptionList,
  Field,
  Input,
  Skeleton,
} from "@/components/ui/primitives";
import { AnswerForm } from "@/features/retention/answer-form";
import {
  answerRetention,
  getRetentionAction,
  getRetentionLink,
  sendRetentionCode,
  signOutRetention,
  uploadRetentionEvidence,
  verifyRetentionCode,
  type RetentionLink,
  type RetentionLinkAction,
} from "@/features/retention/link-api";
import type { RetentionAnswer } from "@/features/retention/types";
import { ApiError } from "@/lib/errors";
import { formatDate } from "@/lib/format";

type Phase = "loading" | "invalid" | "code" | "open";

const DONE: Record<string, string> = {
  erased: "erased",
  anonymised: "anonymised",
  kept: "kept",
  not_held: "not held",
  reviewed: "reviewed",
};

export default function RetentionLinkPage() {
  const params = useParams<{ token: string }>();
  const token = params?.token ?? "";
  const [phase, setPhase] = React.useState<Phase>("loading");
  const [link, setLink] = React.useState<RetentionLink | null>(null);
  const [detail, setDetail] = React.useState<RetentionLinkAction | null>(null);

  const openAction = React.useCallback(async () => {
    try {
      setDetail(await getRetentionAction(token));
      setPhase("open");
    } catch (err) {
      setPhase(err instanceof ApiError && err.status === 401 ? "code" : "invalid");
    }
  }, [token]);

  React.useEffect(() => {
    if (!token) return;
    getRetentionLink(token)
      .then(async (found) => {
        setLink(found);
        if (found.signed_in) await openAction();
        else setPhase("code");
      })
      .catch(() => setPhase("invalid"));
  }, [token, openAction]);

  return (
    <div className="min-h-dvh bg-bg-subtle">
      <header className="brand-gradient">
        <div className="mx-auto max-w-3xl px-4 py-10">
          <span className="grid size-11 place-items-center rounded-xl bg-white/15 ring-1 ring-white/25">
            <BrandMark className="size-6 text-white" />
          </span>
          <h1 className="mt-4 text-3xl font-semibold tracking-tight text-white">
            {link ? `Retention review for ${link.holder_label}` : "A retention review"}
          </h1>
          <p className="mt-3 max-w-xl text-sm leading-relaxed text-white/80">
            The time some personal data you hold for us may be kept has passed. The Privacy
            Office asks what you did with it.
          </p>
        </div>
      </header>

      <main id="main" className="mx-auto max-w-3xl px-4 py-8">
        {phase === "loading" && <Skeleton className="h-64" />}

        {phase === "invalid" && (
          <Alert tone="warning" title="This link is not valid">
            <p>
              It may have been replaced, or never existed. Ask the Privacy Office for a new
              link.
            </p>
          </Alert>
        )}

        {phase === "code" && link && (
          <CodeStep token={token} link={link} onOpened={openAction} />
        )}

        {phase === "open" && detail && (
          <div className="space-y-4">
            <div className="flex justify-end">
              <Button
                variant="ghost"
                size="sm"
                onClick={async () => {
                  await signOutRetention(token).catch(() => undefined);
                  setDetail(null);
                  setPhase("code");
                }}
              >
                <LogOut className="size-4" aria-hidden="true" />
                Close the review on this device
              </Button>
            </div>
            <Opened token={token} detail={detail} onChange={setDetail} />
          </div>
        )}
      </main>
    </div>
  );
}

function Opened({
  token,
  detail,
  onChange,
}: {
  token: string;
  detail: RetentionLinkAction;
  onChange: (d: RetentionLinkAction) => void;
}) {
  const [pending, setPending] = React.useState(false);
  const [problem, setProblem] = React.useState<string | null>(null);
  const { action, review } = detail;
  const open = action.status === "open" || action.status === "sent_back";

  async function answer(body: RetentionAnswer, proof: File | null) {
    setPending(true);
    setProblem(null);
    try {
      if (proof) await uploadRetentionEvidence(token, proof);
      onChange(await answerRetention(token, body));
    } catch (err) {
      setProblem(
        err instanceof ApiError ? err.userMessage() : "Not sent. Try again in a moment.",
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Review {review.reference}</CardTitle>
        <p className="mt-1 text-sm text-text-muted">
          Answer by {formatDate(action.due_at)}
        </p>
      </CardHeader>
      <CardBody className="space-y-5 text-sm">
        <DescriptionList>
          <DescriptionItem term={review.is_activity ? "Activity" : "Project"}>
            {review.project_name}
          </DescriptionItem>
          <DescriptionItem term="Purpose">{review.purpose_name}</DescriptionItem>
          <DescriptionItem term="People">{review.people}</DescriptionItem>
          <DescriptionItem term="Data due to go">
            {formatDate(review.first_due_at)}
            {review.last_due_at && review.last_due_at !== review.first_due_at
              ? ` – ${formatDate(review.last_due_at)}`
              : ""}
          </DescriptionItem>
        </DescriptionList>
        <p className="text-text-muted">
          Which people are in the review is in the export you received for this project, by
          their consent IDs. Answer for all of the data you hold for them under this
          purpose.
        </p>
        {action.status === "sent_back" && action.sent_back_reason && (
          <Alert tone="warning" title="Your earlier answer was sent back">
            {action.sent_back_reason}
          </Alert>
        )}
        {open ? (
          <AnswerForm
            kind={review.kind}
            pending={pending}
            problem={problem}
            onAnswer={answer}
          />
        ) : (
          <Alert tone="success" title="Thank you">
            {action.outcome
              ? `You answered: ${DONE[action.outcome] ?? action.outcome}. `
              : "Your answer is with the Privacy Office. "}
            {action.status === "answered"
              ? "The Privacy Office will accept it, or tell you what is missing."
              : "Nothing more is needed."}
          </Alert>
        )}
      </CardBody>
    </Card>
  );
}

function CodeStep({
  token,
  link,
  onOpened,
}: {
  token: string;
  link: RetentionLink;
  onOpened: () => Promise<void>;
}) {
  const [sent, setSent] = React.useState<string | null>(null);
  const [code, setCode] = React.useState("");
  const [pending, setPending] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  async function send() {
    setPending(true);
    setError(null);
    try {
      const result = await sendRetentionCode(token);
      setSent(result.message ?? "A code is on its way.");
    } catch (err) {
      setError(err instanceof ApiError ? err.userMessage() : "Could not send a code.");
    } finally {
      setPending(false);
    }
  }

  async function verify(e: React.FormEvent) {
    e.preventDefault();
    if (code.length !== 6) return;
    setPending(true);
    setError(null);
    try {
      await verifyRetentionCode(token, code);
      await onOpened();
    } catch (err) {
      setError(err instanceof ApiError ? err.userMessage() : "That code did not work.");
    } finally {
      setPending(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Review {link.reference}</CardTitle>
        <p className="mt-1 text-sm text-text-muted">Answer by {formatDate(link.due_at)}</p>
      </CardHeader>
      <CardBody className="space-y-4 text-sm">
        <p>
          The review opens once you prove you read the address it was sent to. We send a
          six-digit code to{" "}
          <span className="font-medium">{link.code_goes_to ?? "that address"}</span>; it
          opens the review on this device for an hour.
        </p>
        {error && <Alert tone="danger">{error}</Alert>}
        <Button
          variant={sent ? "secondary" : "primary"}
          loading={pending && !sent}
          onClick={send}
        >
          {sent ? "Resend code" : "Send code"}
        </Button>
        {sent && (
          <p className="text-text-muted" role="status">
            {sent}
          </p>
        )}
        <p className="text-xs text-text-subtle">
          <Link href="/help#retention-link" className="underline underline-offset-2">
            How answering a retention review works
          </Link>
        </p>
        {sent && (
          <form method="post" noValidate onSubmit={verify} className="space-y-3">
            <Field label="Six-digit code" required>
              {(p) => (
                <Input
                  {...p}
                  value={code}
                  onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  placeholder="000000"
                  className="text-center font-mono text-lg tracking-[0.4em]"
                />
              )}
            </Field>
            <Button
              type="submit"
              variant="primary"
              loading={pending}
              disabled={code.length !== 6}
            >
              Open the review
            </Button>
          </form>
        )}
      </CardBody>
    </Card>
  );
}
