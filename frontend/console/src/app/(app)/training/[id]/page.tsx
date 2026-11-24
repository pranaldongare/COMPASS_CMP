/**
 * One training module (2026-11-24): its steps in order, then its questions.
 *
 * The steps are a stepper - a list down the side, one step at a time beside
 * it - because the work is a sequence, and seeing where you are in it is half
 * of learning it. A step names the page it happens on; "Open" goes there only
 * when the reader's role reaches it, and says the page is the live one.
 * The questions are answered all together and checked together, with each
 * answer explained, right or wrong; all right completes the module.
 */
"use client";

import {
  ArrowLeft,
  ArrowRight,
  Check,
  CheckCircle2,
  ExternalLink,
  Lightbulb,
  RotateCcw,
  XCircle,
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import * as React from "react";

import { PageHeader } from "@/components/layout/app-shell";
import { labelFor, sectionsFor, type NavItem } from "@/components/layout/nav";
import { Alert, Button, Card, CardBody, EmptyState } from "@/components/ui/primitives";
import { Rich } from "@/features/help/components/help-manual";
import { modulesFor, moduleById, type TrainingModule } from "@/features/training/content";
import { useTrainingProgress } from "@/features/training/progress";
import { cn } from "@/lib/format";
import { useAuth } from "@/providers";

export default function TrainingModulePage() {
  const params = useParams<{ id: string }>();
  const { me } = useAuth();
  const mod = moduleById(params.id);
  const mine = modulesFor(me?.role);

  if (!mod || !mine.some((m) => m.id === mod.id)) {
    return (
      <>
        <PageHeader title="Training" />
        <EmptyState
          title="This module is not part of your training"
          description="Your course lists the modules for your role."
          action={
            <Link
              href="/training"
              className="text-sm font-semibold text-accent-text underline"
            >
              Back to your course
            </Link>
          }
        />
      </>
    );
  }
  return <ModuleRunner mod={mod} course={mine} />;
}

function ModuleRunner({ mod, course }: { mod: TrainingModule; course: TrainingModule[] }) {
  const { me } = useAuth();
  const { progress, markStep, pass, reset } = useTrainingProgress(me?.uuid);
  const p = progress[mod.id];
  const total = mod.steps.length;
  // `total` is the questions; 0..total-1 the steps. Until the person
  // chooses, the module opens where they left off: the first step not done,
  // or the questions once every step is - or the first step of one finished.
  const [chosen, setAt] = React.useState<number | null>(null);
  const resume =
    p && !p.completedAt ? mod.steps.findIndex((_, i) => !p.done.includes(i)) : 0;
  const at = chosen ?? (resume === -1 ? total : resume);
  const heading = React.useRef<HTMLHeadingElement>(null);

  const go = (index: number) => {
    setAt(index);
    // Move focus to the new step's heading, so a keyboard or screen reader
    // user is where the content changed, not left on the button.
    requestAnimationFrame(() => heading.current?.focus());
  };

  const pages = React.useMemo(() => {
    const items = sectionsFor(me).flatMap((s) => s.items);
    return new Map<string, NavItem>(items.map((i) => [i.key, i]));
  }, [me]);

  const position = course.findIndex((m) => m.id === mod.id);
  const nextModule = course[position + 1];

  return (
    <>
      <PageHeader title={mod.title} />

      <div className="flex flex-wrap items-start gap-6">
        {/* The steps, down the side; on a phone, above. */}
        <nav
          aria-label="Steps in this module"
          className="w-full lg:sticky lg:top-20 lg:w-72 lg:flex-none"
        >
          <Card>
            <CardBody className="space-y-3">
              <div>
                <p className="text-xs font-medium text-text-subtle">
                  Module {position + 1} of {course.length} · {mod.minutes} min
                </p>
                <p className="mt-1 text-sm text-text-muted">{mod.summary}</p>
              </div>
              <ol className="space-y-1">
                {mod.steps.map((step, i) => {
                  const done = p?.done.includes(i) ?? false;
                  return (
                    <li key={step.title}>
                      <StepButton
                        number={i + 1}
                        label={step.title}
                        done={done}
                        current={at === i}
                        onClick={() => go(i)}
                      />
                    </li>
                  );
                })}
                <li>
                  <StepButton
                    number={total + 1}
                    label="Check your understanding"
                    done={p?.passed ?? false}
                    current={at === total}
                    onClick={() => go(total)}
                  />
                </li>
              </ol>
            </CardBody>
          </Card>
        </nav>

        <section className="min-w-0 flex-[999_1_32rem]" aria-live="polite">
          <Card>
            <CardBody className="space-y-5">
              {at < total ? (
                <StepView
                  mod={mod}
                  index={at}
                  heading={heading}
                  pages={pages}
                  role={me?.role}
                  onBack={at > 0 ? () => go(at - 1) : undefined}
                  onNext={() => {
                    markStep(mod, at);
                    go(at + 1);
                  }}
                />
              ) : (
                <CheckView
                  mod={mod}
                  heading={heading}
                  passed={p?.passed ?? false}
                  onBack={() => go(total - 1)}
                  onPass={() => pass(mod)}
                  onRestart={() => {
                    reset(mod);
                    go(0);
                  }}
                  nextModule={nextModule}
                />
              )}
            </CardBody>
          </Card>
        </section>
      </div>
    </>
  );
}

function StepButton({
  number,
  label,
  done,
  current,
  onClick,
}: {
  number: number;
  label: string;
  done: boolean;
  current: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-current={current ? "step" : undefined}
      className={cn(
        "flex min-h-10 w-full items-center gap-3 rounded-lg px-2 py-1.5 text-left text-sm transition-colors",
        "focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-focus",
        current
          ? "bg-accent-subtle font-semibold text-accent-text"
          : "text-text-muted hover:bg-bg-subtle hover:text-text",
      )}
    >
      <span
        className={cn(
          "flex size-6 flex-none items-center justify-center rounded-full border text-xs font-semibold",
          done
            ? "border-success-border bg-success-subtle text-success-text"
            : current
              ? "border-accent bg-accent text-accent-contrast"
              : "border-border-strong bg-surface",
        )}
        aria-hidden="true"
      >
        {done ? <Check className="size-3.5" /> : number}
      </span>
      <span className="min-w-0">
        {label}
        {done && <span className="sr-only"> (done)</span>}
      </span>
    </button>
  );
}

function StepView({
  mod,
  index,
  heading,
  pages,
  role,
  onBack,
  onNext,
}: {
  mod: TrainingModule;
  index: number;
  heading: React.RefObject<HTMLHeadingElement | null>;
  pages: Map<string, NavItem>;
  role: string | undefined;
  onBack?: () => void;
  onNext: () => void;
}) {
  const step = mod.steps[index];
  const page = step.where ? pages.get(step.where) : undefined;
  const last = index === mod.steps.length - 1;
  return (
    <>
      <div>
        <p className="text-xs font-semibold tracking-wider text-accent-text uppercase">
          Step {index + 1} of {mod.steps.length}
        </p>
        <h2
          ref={heading}
          tabIndex={-1}
          className="mt-1 text-xl font-semibold text-text outline-none"
        >
          {step.title}
        </h2>
      </div>

      <p className="text-base leading-relaxed text-text">
        <Rich text={step.body} />
      </p>

      {step.actions && (
        <ol className="list-decimal space-y-1 pl-5 text-sm text-text">
          {step.actions.map((a) => (
            <li key={a}>
              <Rich text={a} />
            </li>
          ))}
        </ol>
      )}

      {step.tip && (
        <div className="flex gap-3 rounded-lg border border-warning-border bg-warning-subtle p-3 text-sm text-text">
          <Lightbulb
            className="mt-0.5 size-4 flex-none text-warning-text"
            aria-hidden="true"
          />
          <p>
            <span className="font-semibold">Worth knowing: </span>
            <Rich text={step.tip} />
          </p>
        </div>
      )}

      {page && (
        <div className="flex flex-wrap items-center gap-3 rounded-lg border border-border bg-bg-subtle p-3">
          <p className="min-w-0 flex-1 basis-56 text-sm text-text-muted">
            This happens on{" "}
            <span className="font-medium text-text">{labelFor(page, role)}</span>. It is the
            live page: anything you do there is real.
          </p>
          <Link
            href={page.href}
            target="_blank"
            rel="noopener"
            className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-border-strong bg-surface px-3 text-sm font-semibold text-text hover:bg-surface-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
          >
            Open {labelFor(page, role)}
            <ExternalLink className="size-3.5" aria-hidden="true" />
            <span className="sr-only">(opens in a new tab)</span>
          </Link>
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4">
        {onBack ? (
          <Button variant="secondary" onClick={onBack}>
            <ArrowLeft className="size-4" aria-hidden="true" />
            Previous
          </Button>
        ) : (
          <Link
            href="/training"
            className="text-sm text-text-muted underline underline-offset-2"
          >
            Back to your course
          </Link>
        )}
        <Button variant="primary" onClick={onNext}>
          {last ? "Done - check your understanding" : "Done - next step"}
          <ArrowRight className="size-4" aria-hidden="true" />
        </Button>
      </div>
    </>
  );
}

function CheckView({
  mod,
  heading,
  passed,
  onBack,
  onPass,
  onRestart,
  nextModule,
}: {
  mod: TrainingModule;
  heading: React.RefObject<HTMLHeadingElement | null>;
  passed: boolean;
  onBack: () => void;
  onPass: () => void;
  onRestart: () => void;
  nextModule: TrainingModule | undefined;
}) {
  const [chosen, setChosen] = React.useState<(number | null)[]>(() =>
    mod.check.map(() => null),
  );
  const [checked, setChecked] = React.useState(false);
  const allAnswered = chosen.every((c) => c !== null);
  const right = chosen.filter((c, i) => c === mod.check[i].answer).length;
  const allRight = right === mod.check.length;

  if (passed && !checked) {
    return (
      <Complete mod={mod} heading={heading} nextModule={nextModule} onRestart={onRestart} />
    );
  }

  return (
    <form
      method="post"
      onSubmit={(e) => {
        e.preventDefault();
        setChecked(true);
        if (allRight) onPass();
      }}
      className="space-y-5"
      noValidate
    >
      <div>
        <p className="text-xs font-semibold tracking-wider text-accent-text uppercase">
          Last step
        </p>
        <h2
          ref={heading}
          tabIndex={-1}
          className="mt-1 text-xl font-semibold text-text outline-none"
        >
          Check your understanding
        </h2>
        <p className="mt-1 text-sm text-text-muted">
          {mod.check.length === 1 ? "One question." : `${mod.check.length} questions.`}{" "}
          Answer all of them, then check. You can try again as often as you like.
        </p>
      </div>

      {mod.check.map((q, qi) => {
        const pick = chosen[qi];
        const correct = pick === q.answer;
        return (
          <fieldset key={q.question} className="space-y-2">
            <legend className="mb-2 font-medium text-text">
              {qi + 1}. <Rich text={q.question} />
            </legend>
            {q.options.map((o, oi) => (
              <label
                key={o}
                className={cn(
                  "flex min-h-11 cursor-pointer items-center gap-3 rounded-lg border px-3 py-2 text-sm",
                  pick === oi
                    ? "border-accent bg-accent-subtle"
                    : "border-border hover:bg-bg-subtle",
                )}
              >
                <input
                  type="radio"
                  name={`q${qi}`}
                  checked={pick === oi}
                  onChange={() => {
                    setChecked(false);
                    setChosen((c) => c.map((v, i) => (i === qi ? oi : v)));
                  }}
                  className="size-4 accent-[var(--accent)]"
                />
                <span>
                  <Rich text={o} />
                </span>
              </label>
            ))}
            {checked && pick !== null && (
              <p
                className={cn(
                  "flex gap-2 rounded-lg p-3 text-sm",
                  correct
                    ? "bg-success-subtle text-success-text"
                    : "bg-danger-subtle text-danger-text",
                )}
              >
                {correct ? (
                  <CheckCircle2 className="mt-0.5 size-4 flex-none" aria-hidden="true" />
                ) : (
                  <XCircle className="mt-0.5 size-4 flex-none" aria-hidden="true" />
                )}
                <span>
                  <span className="font-semibold">
                    {correct ? "Right. " : "Not quite. "}
                  </span>
                  <Rich text={q.why} />
                </span>
              </p>
            )}
          </fieldset>
        );
      })}

      {checked && !allRight && (
        <Alert tone="warning">
          {right} of {mod.check.length} right. Change the answers marked and check again.
        </Alert>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4">
        <Button type="button" variant="secondary" onClick={onBack}>
          <ArrowLeft className="size-4" aria-hidden="true" />
          Previous
        </Button>
        <Button type="submit" variant="primary" disabled={!allAnswered}>
          Check answers
        </Button>
      </div>

      {checked && allRight && (
        <Complete mod={mod} heading={null} nextModule={nextModule} onRestart={onRestart} />
      )}
    </form>
  );
}

function Complete({
  mod,
  heading,
  nextModule,
  onRestart,
}: {
  mod: TrainingModule;
  heading: React.RefObject<HTMLHeadingElement | null> | null;
  nextModule: TrainingModule | undefined;
  onRestart: () => void;
}) {
  return (
    <div className="space-y-4 rounded-xl border border-success-border bg-success-subtle p-5">
      <div className="flex items-start gap-3">
        <CheckCircle2
          className="mt-0.5 size-6 flex-none text-success-text"
          aria-hidden="true"
        />
        <div>
          <h2
            ref={heading ?? undefined}
            tabIndex={-1}
            className="text-lg font-semibold text-text outline-none"
          >
            Module complete
          </h2>
          <p className="text-sm text-text-muted">
            You have finished “{mod.title}”. Help keeps the same steps for when you need
            them again.
          </p>
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        {nextModule ? (
          <Link
            href={`/training/${nextModule.id}`}
            className="inline-flex min-h-10 items-center gap-2 rounded-lg bg-accent px-4 text-sm font-semibold text-accent-contrast hover:bg-accent-hover"
          >
            Next: {nextModule.title}
            <ArrowRight className="size-4" aria-hidden="true" />
          </Link>
        ) : (
          <Link
            href="/training"
            className="inline-flex min-h-10 items-center gap-2 rounded-lg bg-accent px-4 text-sm font-semibold text-accent-contrast hover:bg-accent-hover"
          >
            Back to your course
          </Link>
        )}
        <Button type="button" variant="secondary" onClick={onRestart}>
          <RotateCcw className="size-4" aria-hidden="true" />
          Take it again
        </Button>
      </div>
    </div>
  );
}
