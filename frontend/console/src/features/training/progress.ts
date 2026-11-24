/**
 * Where a person is in their training, kept in this browser.
 *
 * A mock course (2026-11-24): nothing here is a record the organisation
 * relies on, so it stays with the person, keyed by their account so two
 * colleagues on one machine do not share progress. Storage can be missing -
 * a private window, blocked site data - and every read and write is guarded:
 * the course then works, it just does not remember.
 *
 * When completion has to be evidence (who was trained, when), this moves to
 * the API behind the same hook, and the pages do not change.
 */
"use client";

import * as React from "react";

import type { TrainingModule } from "@/features/training/content";

export interface ModuleProgress {
  /** Indexes of the steps marked done. */
  done: number[];
  /** Every question answered correctly at least once. */
  passed: boolean;
  completedAt: string | null;
}

export type Progress = Record<string, ModuleProgress>;

const EMPTY: ModuleProgress = { done: [], passed: false, completedAt: null };

function key(userId: string): string {
  return `cmp.training.v1.${userId}`;
}

function read(userId: string): Progress {
  try {
    const raw = window.localStorage.getItem(key(userId));
    if (!raw) return {};
    const parsed: unknown = JSON.parse(raw);
    return parsed && typeof parsed === "object" ? (parsed as Progress) : {};
  } catch {
    return {};
  }
}

function write(userId: string, progress: Progress): void {
  try {
    window.localStorage.setItem(key(userId), JSON.stringify(progress));
  } catch {
    // Not remembered; the course still works.
  }
}

export type ModuleState = "not-started" | "in-progress" | "complete";

export function stateOf(mod: TrainingModule, p: ModuleProgress | undefined): ModuleState {
  if (!p || (p.done.length === 0 && !p.passed)) return "not-started";
  return p.completedAt ? "complete" : "in-progress";
}

/** Share of a module done: its steps, and its questions as one more step. */
export function shareOf(mod: TrainingModule, p: ModuleProgress | undefined): number {
  if (!p) return 0;
  const total = mod.steps.length + 1;
  const done = Math.min(p.done.length, mod.steps.length) + (p.passed ? 1 : 0);
  return done / total;
}

/*
 * A tiny store over localStorage, read with `useSyncExternalStore`: one
 * parsed snapshot per account, kept until it is written, so every reader gets
 * the same object and a change in another tab arrives through `storage`.
 */
const listeners = new Set<() => void>();
const cache = new Map<string, Progress>();
const NONE: Progress = {};

function snapshot(userId: string | undefined): Progress {
  if (!userId) return NONE;
  let value = cache.get(userId);
  if (!value) {
    value = read(userId);
    cache.set(userId, value);
  }
  return value;
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  const onStorage = (e: StorageEvent) => {
    if (e.key?.startsWith("cmp.training.")) {
      cache.clear();
      listener();
    }
  };
  window.addEventListener("storage", onStorage);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("storage", onStorage);
  };
}

function save(userId: string, next: Progress): void {
  cache.set(userId, next);
  write(userId, next);
  listeners.forEach((l) => l());
}

export function useTrainingProgress(userId: string | undefined) {
  const progress = React.useSyncExternalStore(
    subscribe,
    () => snapshot(userId),
    () => NONE,
  );

  const update = React.useCallback(
    (moduleId: string, change: (p: ModuleProgress) => ModuleProgress) => {
      if (!userId) return;
      const current = snapshot(userId);
      save(userId, { ...current, [moduleId]: change(current[moduleId] ?? EMPTY) });
    },
    [userId],
  );

  const markStep = React.useCallback(
    (mod: TrainingModule, index: number) =>
      update(mod.id, (p) =>
        p.done.includes(index)
          ? p
          : { ...p, done: [...p.done, index].sort((a, b) => a - b) },
      ),
    [update],
  );

  const pass = React.useCallback(
    (mod: TrainingModule) =>
      update(mod.id, (p) => ({
        done: mod.steps.map((_, i) => i),
        passed: true,
        completedAt: p.completedAt ?? new Date().toISOString(),
      })),
    [update],
  );

  const reset = React.useCallback(
    (mod: TrainingModule) => update(mod.id, () => EMPTY),
    [update],
  );

  return { progress, markStep, pass, reset };
}
