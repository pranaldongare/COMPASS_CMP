/**
 * The words and badges the breach pages share.
 *
 * A duty's clock is the server's: `seconds_remaining`, `overdue`,
 * `seconds_elapsed`, `past_target`. This module turns those into a sentence
 * and computes nothing about when anything is due.
 */
import { Badge } from "@/components/ui/primitives";
import type {
  BreachClock,
  BreachDuty,
  BreachDutyState,
  BreachLocation,
  BreachOutcome,
  BreachStatus,
} from "@/types";

export const OUTCOME_COPY: Record<BreachOutcome, string> = {
  pending: "Still validating",
  yes: "A personal data breach",
  no: "Not a personal data breach",
};

export const LOCATION_COPY: Record<BreachLocation["kind"], string> = {
  platform: "The platform's own database",
  processor: "A processor",
  data_source: "A data source",
  other: "Elsewhere",
};

export function locationText(l: BreachLocation): string {
  if (l.kind === "processor") return `Processor: ${l.processor_name ?? "unknown"}`;
  if (l.kind === "data_source") return `Data source: ${l.source_name ?? "unknown"}`;
  return LOCATION_COPY[l.kind];
}

export function BreachStatusBadge({ status }: { status: BreachStatus }) {
  return (
    <Badge tone={status === "open" ? "warning" : "neutral"} dot>
      {status === "open" ? "Open" : "Closed"}
    </Badge>
  );
}

export function OutcomeBadge({ outcome }: { outcome: BreachOutcome }) {
  const tone = outcome === "yes" ? "danger" : outcome === "no" ? "success" : "info";
  return (
    <Badge tone={tone} dot>
      {OUTCOME_COPY[outcome]}
    </Badge>
  );
}

const STATE_COPY: Record<BreachDutyState, string> = {
  outstanding: "Outstanding",
  done: "Done",
  not_applicable: "Not applicable",
};

export function DutyStateBadge({ duty }: { duty: BreachDuty }) {
  const late = duty.clock.overdue || duty.clock.past_target;
  const tone =
    duty.state === "done"
      ? "success"
      : duty.state === "not_applicable"
        ? "neutral"
        : late
          ? "danger"
          : "warning";
  return (
    <Badge tone={tone} dot>
      {STATE_COPY[duty.state]}
    </Badge>
  );
}

/** "3 h 20 min", from seconds. Whole minutes; the sign is the caller's. */
export function span(seconds: number): string {
  const s = Math.abs(seconds);
  const days = Math.floor(s / 86_400);
  const hours = Math.floor((s % 86_400) / 3_600);
  const minutes = Math.floor((s % 3_600) / 60);
  if (days > 0) return `${days} d ${hours} h`;
  if (hours > 0) return `${hours} h ${minutes} min`;
  return `${minutes} min`;
}

/** The clock as a sentence: time left or overdue for a dated duty; time since
 *  awareness for one due without delay, against the target when there is one. */
export function clockText(state: BreachDutyState, clock: BreachClock): string {
  if (state !== "outstanding") return "";
  if (!clock.without_delay && clock.seconds_remaining !== null) {
    return clock.overdue
      ? `Overdue by ${span(clock.seconds_remaining)}`
      : `${span(clock.seconds_remaining)} left`;
  }
  if (clock.seconds_elapsed === null) return "Without delay";
  const elapsed = `${span(clock.seconds_elapsed)} since awareness`;
  if (clock.past_target) return `${elapsed} - past the internal target`;
  return clock.target_at ? elapsed : `${elapsed} (no internal target set)`;
}
