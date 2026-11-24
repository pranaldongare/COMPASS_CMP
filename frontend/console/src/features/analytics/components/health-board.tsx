/**
 * "Right now" on the health tab (2026-11-24 redesign): one tile per part of
 * the platform, each judged from the health figures the tab already holds -
 * nothing here is counted twice, and nothing is a probe of its own. A tile
 * opens the figure it rests on.
 */
"use client";

import { CircleAlert, CircleCheck, CircleX } from "lucide-react";
import Link from "next/link";
import * as React from "react";

import { formatValue } from "@/features/analytics/format";
import { cn } from "@/lib/format";
import type { Figure, Figures } from "@/types";

type Health = "ok" | "watch" | "bad";

interface Tile {
  key: string;
  name: string;
  state: Health;
  word: string;
  detail: string;
}

const LOOK: Record<Health, { icon: typeof CircleCheck; cls: string; text: string }> = {
  ok: { icon: CircleCheck, cls: "border-border bg-surface", text: "text-success-text" },
  watch: {
    icon: CircleAlert,
    cls: "border-warning-border bg-warning-subtle",
    text: "text-warning-text",
  },
  bad: {
    icon: CircleX,
    cls: "border-danger-border bg-danger-subtle",
    text: "text-danger-text",
  },
};

function n(f: Figure | undefined): number | null {
  return f && !f.suppressed ? f.value : null;
}

export function tilesFor(data: Figures): Tile[] {
  const get = (k: string) => data.metrics.find((m) => m.key === k);
  const tiles: Tile[] = [];
  const breaks = get("health.audit_breaks");
  if (breaks) {
    const b = n(breaks) ?? 0;
    const checks = n(get("health.audit_checks")) ?? 0;
    // No check in the period proves nothing either way: say so, rather than
    // call a chain nobody looked at intact.
    tiles.push({
      key: breaks.key,
      name: "Audit trail chain",
      state: b > 0 ? "bad" : checks === 0 ? "watch" : "ok",
      word: b > 0 ? "Broken" : checks === 0 ? "Not checked" : "Intact",
      detail:
        checks === 0
          ? "No nightly check ran in the period"
          : `${checks} nightly ${checks === 1 ? "check" : "checks"} · ${b} ${b === 1 ? "break" : "breaks"}`,
    });
  }
  const codes = get("health.otp_success_rate");
  if (codes) {
    const s = codes.status;
    const none = codes.value === null && !codes.suppressed;
    tiles.push({
      key: codes.key,
      name: "Sign-in codes",
      state: s === "red" ? "bad" : s === "amber" ? "watch" : "ok",
      word: none
        ? "No codes yet"
        : s === "red"
          ? "Failing"
          : s === "amber"
            ? "Slow"
            : "Healthy",
      detail: none
        ? "No codes were sent in the period"
        : `${formatValue(codes.value, "percent")} entered correctly`,
    });
  }
  for (const [k, name] of [
    ["health.breach_notice_failures", "Breach notice delivery"],
    ["health.board_mail_failures", "Board report mail"],
    ["health.reports_failed", "Reports"],
  ] as const) {
    const f = get(k);
    if (!f) continue;
    const v = n(f) ?? 0;
    tiles.push({
      key: k,
      name,
      state: v > 0 ? "watch" : "ok",
      word: v > 0 ? "Failures" : "Healthy",
      detail: v > 0 ? `${v} not delivered in the period` : "Nothing failed in the period",
    });
  }
  const failing = get("health.datavault_failing");
  const pending = get("health.datavault_pending");
  if (failing || pending) {
    const fv = n(failing) ?? 0;
    const pv = n(pending) ?? 0;
    tiles.push({
      key: (failing ?? pending)!.key,
      name: "DataVault sync",
      state: fv > 0 ? "bad" : "ok",
      word: fv > 0 ? "Refusing" : "Healthy",
      detail: `${pv} waiting · ${fv} refused`,
    });
  }
  const queues = get("health.queue_depth");
  if (queues) {
    const v = n(queues) ?? 0;
    tiles.push({
      key: queues.key,
      name: "Workers and queues",
      state: v > 500 ? "watch" : "ok",
      word: v > 500 ? "Backed up" : "Healthy",
      detail: `${v} ${v === 1 ? "job" : "jobs"} waiting`,
    });
  }
  return tiles;
}

export function HealthBoard({
  data,
  hrefOf,
}: {
  data: Figures;
  hrefOf: (key: string) => string;
}) {
  const tiles = tilesFor(data);
  if (tiles.length === 0) return null;
  const healthy = tiles.filter((t) => t.state === "ok").length;
  return (
    <section aria-labelledby="health-now" className="space-y-2.5">
      <h2 id="health-now" className="text-sm font-semibold text-text">
        At a glance{" "}
        <span className="font-normal text-text-muted">
          · {healthy} of {tiles.length} healthy
        </span>
      </h2>
      <ul className="grid [grid-template-columns:repeat(auto-fill,minmax(13rem,1fr))] gap-3">
        {tiles.map((t) => {
          const look = LOOK[t.state];
          const Icon = look.icon;
          return (
            <li key={t.name}>
              <Link
                href={hrefOf(t.key)}
                className={cn(
                  "flex h-full flex-col gap-1.5 rounded-xl border p-3.5 transition-shadow hover:shadow-[var(--shadow-raised)]",
                  "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus",
                  look.cls,
                )}
              >
                <span
                  className={cn(
                    "inline-flex items-center gap-1.5 text-xs font-semibold",
                    look.text,
                  )}
                >
                  <Icon className="size-3.5" aria-hidden="true" />
                  {t.word}
                </span>
                <span className="font-semibold text-text">{t.name}</span>
                <span className="text-xs text-text-muted">{t.detail}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
