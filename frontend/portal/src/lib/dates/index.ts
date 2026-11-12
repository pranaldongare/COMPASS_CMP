/**
 * What a date or time input may offer, in the person's own calendar
 * (2026-11-11).
 *
 * A record of something done - an approval, a breach noticed, a mail sent -
 * cannot be dated after now, and a deadline or an expiry cannot be set before
 * it. The inputs say so with `max` and `min`, so the picker greys out what
 * would only be refused.
 *
 * Local, not UTC: `toISOString()` is Greenwich's date, which in India until
 * 05:30 is still yesterday, so a picker bounded by it refused today.
 */

/** `n` as two digits. */
const two = (n: number) => String(n).padStart(2, "0");

/** Today, as a date input's value (`YYYY-MM-DD`). */
export function todayLocal(at: Date = new Date()): string {
  return `${at.getFullYear()}-${two(at.getMonth() + 1)}-${two(at.getDate())}`;
}

/** The end of a chosen day, as the moment a ticket due that day falls due:
 *  due today is overdue tomorrow. */
export function endOfDay(date: string): string {
  return new Date(`${date}T23:59:00`).toISOString();
}

/**
 * The last day a ticket may fall due, given the moment the response it feeds
 * is due: that day, if the day's end is not past it, else the day before. A
 * ticket never falls due after the response itself.
 */
export function lastDayBy(moment: string): string {
  const due = new Date(moment);
  const day = todayLocal(due);
  return new Date(endOfDay(day)).getTime() <= due.getTime()
    ? day
    : todayLocal(new Date(due.getTime() - 86_400_000));
}

/** This minute, as a datetime-local input's value (`YYYY-MM-DDTHH:mm`). */
export function nowLocal(at: Date = new Date()): string {
  return `${todayLocal(at)}T${two(at.getHours())}:${two(at.getMinutes())}`;
}
