/**
 * A breach notice by its link, for somebody with no account (2026-11-20).
 *
 * A person a personal data breach may affect, and who has no account here, is
 * sent a text with a link to this page rather than the whole notice: a notice
 * can run to thousands of characters, and a text cannot. The link alone shows
 * the breach's reference and, masked, the mobile a code will go to. The code,
 * sent by text to the number on the breach's list - never one typed here -
 * opens the notice, so the link has to be read on that phone.
 *
 * Every failure of the link - wrong, cut short, for a notice since replaced -
 * is the same "not valid" screen, as for every link here. Nothing is kept:
 * the notice and the code are in this page's memory only, and are gone when
 * it closes or the person closes the notice.
 */
"use client";

import { ShieldAlert, X } from "lucide-react";
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
  NOTICE_SECTIONS,
  getNoticeLink,
  isNoticeToken,
  openNotice,
  sendNoticeCode,
  stillSealed,
  type BreachNoticeByLink,
  type BreachNoticeLink,
} from "@/features/breach-notices";
import { ApiError } from "@/lib/errors";
import { formatDate } from "@/lib/format";

type Phase = "loading" | "invalid" | "code" | "open";

export default function BreachNoticeLinkPage() {
  const params = useParams<{ token: string }>();
  const token = params?.token ?? "";
  const valid = isNoticeToken(token);
  const [phase, setPhase] = React.useState<Phase>("loading");
  const [link, setLink] = React.useState<BreachNoticeLink | null>(null);
  const [notice, setNotice] = React.useState<BreachNoticeByLink | null>(null);

  React.useEffect(() => {
    // A link of the wrong shape is not asked about: it is not valid.
    if (!valid) return;
    getNoticeLink(token)
      .then((found) => {
        setLink(found);
        setPhase("code");
      })
      .catch(() => setPhase("invalid"));
  }, [token, valid]);

  const shown: Phase = valid ? phase : "invalid";

  return (
    <div className="min-h-dvh bg-bg-subtle">
      <header className="brand-gradient">
        <div className="mx-auto max-w-3xl px-4 py-8 sm:py-10">
          <span className="grid size-11 place-items-center rounded-xl bg-white/15 ring-1 ring-white/25">
            <BrandMark className="size-6 text-white" />
          </span>
          <h1 className="mt-4 text-2xl font-semibold tracking-tight text-white sm:text-3xl">
            A personal data breach notice
          </h1>
          <p className="mt-3 max-w-xl text-sm leading-relaxed text-white/80">
            A personal data breach may affect your personal data. This notice says what
            happened, what it may mean for you, what we are doing about it, what you can do,
            and whom to ask.
          </p>
        </div>
      </header>

      <main id="main" className="mx-auto max-w-3xl px-4 py-8">
        {shown === "loading" && <Skeleton className="h-48" />}

        {shown === "invalid" && (
          <Alert tone="warning" title="This link is not valid">
            <p>
              It may have been cut short when it was copied, or replaced by a newer one.
              Check the text we sent you, or contact the Privacy Office.
            </p>
          </Alert>
        )}

        {shown === "code" && link && (
          <CodeStep
            token={token}
            link={link}
            onOpened={(opened) => {
              setNotice(opened);
              setPhase("open");
            }}
            onInvalid={() => setPhase("invalid")}
          />
        )}

        {shown === "open" && notice && (
          <NoticeView
            notice={notice}
            onClose={() => {
              setNotice(null);
              setPhase("code");
            }}
          />
        )}
      </main>
    </div>
  );
}

function CodeStep({
  token,
  link,
  onOpened,
  onInvalid,
}: {
  token: string;
  link: BreachNoticeLink;
  onOpened: (notice: BreachNoticeByLink) => void;
  onInvalid: () => void;
}) {
  const [sent, setSent] = React.useState<string | null>(null);
  const [code, setCode] = React.useState("");
  const [pending, setPending] = React.useState<"send" | "open" | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  async function send() {
    setPending("send");
    setError(null);
    try {
      const result = await sendNoticeCode(token);
      setSent(result.message ?? "A code is on its way.");
      setCode("");
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) return onInvalid();
      setError(err instanceof ApiError ? err.userMessage() : "We could not send a code.");
    } finally {
      setPending(null);
    }
  }

  async function open(e: React.FormEvent) {
    e.preventDefault();
    if (code.length !== 6) return;
    setPending("open");
    setError(null);
    try {
      const opened = await openNotice(token, code);
      if (stillSealed(opened)) {
        setError(
          "The notice could not be shown just now. Try again in a few minutes, or contact the Privacy Office.",
        );
        return;
      }
      onOpened(opened);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) return onInvalid();
      setError(err instanceof ApiError ? err.userMessage() : "That code did not work.");
    } finally {
      setPending(null);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Breach {link.reference}</CardTitle>
      </CardHeader>
      <CardBody className="space-y-4 text-sm">
        <p>
          The notice is shown once you enter a code we send by text. We will send a
          six-digit code to <span className="font-medium">{link.code_goes_to}</span>, the
          mobile we sent this link to.
        </p>
        {error && <Alert tone="danger">{error}</Alert>}
        <Button
          variant={sent ? "secondary" : "primary"}
          className="w-full sm:w-auto"
          loading={pending === "send"}
          disabled={pending !== null}
          onClick={send}
        >
          {sent ? "Resend code" : "Send code"}
        </Button>
        {sent && (
          <p className="text-text-muted" role="status">
            {sent} It expires in ten minutes, or after five wrong tries; then send a new
            one.
          </p>
        )}
        {sent && (
          <form method="post" noValidate onSubmit={open} className="space-y-3">
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
              className="w-full sm:w-auto"
              loading={pending === "open"}
              disabled={code.length !== 6 || pending !== null}
            >
              Open the notice
            </Button>
          </form>
        )}
      </CardBody>
    </Card>
  );
}

function NoticeView({
  notice,
  onClose,
}: {
  notice: BreachNoticeByLink;
  onClose: () => void;
}) {
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>
            <ShieldAlert className="mr-2 inline size-4" aria-hidden="true" />
            Breach {notice.reference}
            {notice.version > 1 && ` - update ${notice.version - 1}`}
          </CardTitle>
          {notice.approved_at && (
            <p className="mt-1 text-xs text-text-muted">
              Issued {formatDate(notice.approved_at)}
            </p>
          )}
        </CardHeader>
        <CardBody className="space-y-5">
          {NOTICE_SECTIONS.map((s) => (
            <section key={s.key} aria-labelledby={`notice-${s.key}`}>
              {/* Under the card's title, which is the page's second level. */}
              <h3 id={`notice-${s.key}`} className="text-base font-semibold">
                {s.heading}
              </h3>
              <p className="mt-1 text-sm leading-relaxed whitespace-pre-wrap">
                {notice[s.key]}
              </p>
            </section>
          ))}
        </CardBody>
      </Card>
      <p className="text-xs text-text-subtle">
        Nothing is saved on this device. To read the notice again, open the link in our text
        and ask for a new code.
      </p>
      <Button variant="ghost" size="sm" onClick={onClose}>
        <X className="size-4" aria-hidden="true" />
        Close the notice
      </Button>
    </div>
  );
}
