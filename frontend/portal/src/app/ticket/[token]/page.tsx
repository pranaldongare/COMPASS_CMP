/**
 * The link a holder outside the organisation receives for a rights ticket
 * (0049, 2026-10-08).
 *
 * A vendor or processor holding the person's data answers here, with no
 * account. The link alone shows whose ticket it is and where a code will go;
 * the code goes to the address the ticket was sent to, and opens the ticket
 * for an hour in this browser. Every failure of the link - wrong, replaced,
 * never existed - is the same "not valid" screen, as for every link here.
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
  Field,
  Input,
  Skeleton,
} from "@/components/ui/primitives";
import {
  getLink,
  getTicket,
  sendCode,
  signOut,
  verifyCode,
  type HolderLink,
  type HolderTicketDetail,
} from "@/features/holder-ticket/api";
import { TicketView } from "@/features/holder-ticket/components/ticket-view";
import { ApiError } from "@/lib/errors";
import { formatDate } from "@/lib/format";

type Phase = "loading" | "invalid" | "code" | "open";

export default function HolderTicketPage() {
  const params = useParams<{ token: string }>();
  const token = params?.token ?? "";
  const [phase, setPhase] = React.useState<Phase>("loading");
  const [link, setLink] = React.useState<HolderLink | null>(null);
  const [detail, setDetail] = React.useState<HolderTicketDetail | null>(null);

  const openTicket = React.useCallback(async () => {
    try {
      setDetail(await getTicket(token));
      setPhase("open");
    } catch (err) {
      // The hour ran out: back to the code, not to "invalid".
      setPhase(err instanceof ApiError && err.status === 401 ? "code" : "invalid");
    }
  }, [token]);

  React.useEffect(() => {
    if (!token) return;
    getLink(token)
      .then(async (found) => {
        setLink(found);
        if (found.signed_in) await openTicket();
        else setPhase("code");
      })
      .catch(() => setPhase("invalid"));
  }, [token, openTicket]);

  return (
    <div className="min-h-dvh bg-bg-subtle">
      <header className="brand-gradient">
        <div className="mx-auto max-w-3xl px-4 py-10">
          <span className="grid size-11 place-items-center rounded-xl bg-white/15 ring-1 ring-white/25">
            <BrandMark className="size-6 text-white" />
          </span>
          <h1 className="mt-4 text-3xl font-semibold tracking-tight text-white">
            {link ? `A ticket for ${link.holder_label}` : "A ticket from the Privacy Office"}
          </h1>
          <p className="mt-3 max-w-xl text-sm leading-relaxed text-white/80">
            The Privacy Office is answering a person&apos;s request about their personal data,
            and has asked you for your part of the answer.
          </p>
        </div>
      </header>

      <main id="main" className="mx-auto max-w-3xl px-4 py-8">
        {phase === "loading" && <Skeleton className="h-64" />}

        {phase === "invalid" && (
          <Alert tone="warning" title="This link is not valid">
            <p>
              It may have been replaced by a newer one, or never existed. Ask the Privacy Office
              for a new link.
            </p>
          </Alert>
        )}

        {phase === "code" && link && (
          <CodeStep token={token} link={link} onOpened={openTicket} />
        )}

        {phase === "open" && detail && (
          <div className="space-y-4">
            <div className="flex justify-end">
              <Button
                variant="ghost"
                size="sm"
                onClick={async () => {
                  await signOut(token).catch(() => undefined);
                  setDetail(null);
                  setPhase("code");
                }}
              >
                <LogOut className="size-4" aria-hidden="true" />
                Close the ticket on this device
              </Button>
            </div>
            <TicketView token={token} detail={detail} onChange={setDetail} />
          </div>
        )}
      </main>
    </div>
  );
}

function CodeStep({
  token,
  link,
  onOpened,
}: {
  token: string;
  link: HolderLink;
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
      const result = await sendCode(token);
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
      await verifyCode(token, code);
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
        <CardTitle>Rights request {link.reference}</CardTitle>
        <p className="mt-1 text-sm text-text-muted">
          {link.state_label}
          {link.due_at && ` · answer by ${formatDate(link.due_at)}`}
        </p>
      </CardHeader>
      <CardBody className="space-y-4 text-sm">
        <p>
          What the ticket asks is shown once you prove you read the address it was sent to. We
          send a six-digit code to{" "}
          <span className="font-medium">{link.code_goes_to ?? "the address on the ticket"}</span>; it
          opens the ticket on this device for an hour.
        </p>
        {error && <Alert tone="danger">{error}</Alert>}
        <Button variant={sent ? "secondary" : "primary"} loading={pending && !sent} onClick={send}>
          {sent ? "Send a new code" : "Send me a code"}
        </Button>
        {sent && <p className="text-text-muted" role="status">{sent}</p>}
        <p className="text-xs text-text-subtle">
          <Link href="/help#ticket-link" className="underline underline-offset-2">
            How answering a ticket works
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
            <Button type="submit" variant="primary" loading={pending} disabled={code.length !== 6}>
              Open the ticket
            </Button>
          </form>
        )}
      </CardBody>
    </Card>
  );
}
