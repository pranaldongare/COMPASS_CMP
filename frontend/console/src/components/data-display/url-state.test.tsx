/**
 * A list's filters and page live in the URL (review 2026-10-01, UX-5).
 *
 * They were read from the query string once, at mount, and then kept in
 * component state - and the cursor stack never left it. Reload, share the
 * link, or open a row and come Back, and the list was on its first page with
 * no filter. Now the URL is the state: a remount (which is what reload and
 * Back are, to the list) finds the same filter on the same page.
 */
import { act } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useCursorStack, useFilterParam } from "@/components/data-display/resource-list";
import { renderHook } from "@/test/render";

vi.mock("next/navigation", () => ({
  // What Next does with the History API: the hook reads the live URL.
  useSearchParams: () => new URLSearchParams(window.location.search),
}));

beforeEach(() => {
  window.history.replaceState(null, "", "/projects");
});

describe("useFilterParam", () => {
  it("writes the filter to the URL and reads it back after a remount", () => {
    const first = renderHook(() => useFilterParam("status"));
    act(() => first.result.current[1]("approved"));
    expect(first.result.current[0]).toBe("approved");
    expect(new URLSearchParams(window.location.search).get("status")).toBe("approved");
    first.unmount();

    const again = renderHook(() => useFilterParam("status"));
    expect(again.result.current[0]).toBe("approved");
  });

  it("clears the filter from the URL when set back to everything", () => {
    window.history.replaceState(null, "", "/projects?status=approved");
    const { result } = renderHook(() => useFilterParam("status"));
    act(() => result.current[1](""));
    expect(window.location.search).toBe("");
  });
});

describe("useCursorStack", () => {
  it("keeps the page and the way back in the URL", () => {
    const first = renderHook(() => useCursorStack());
    act(() => first.result.current.next("c2"));
    act(() => first.result.current.next("c3"));
    expect(first.result.current.cursor).toBe("c3");
    first.unmount();

    const again = renderHook(() => useCursorStack());
    expect(again.result.current.cursor).toBe("c3");
    expect(again.result.current.canGoBack).toBe(true);
    act(() => again.result.current.back());
    expect(again.result.current.cursor).toBe("c2");
    act(() => again.result.current.back());
    expect(again.result.current.cursor).toBeUndefined();
    expect(again.result.current.canGoBack).toBe(false);
  });

  it("goes back to the first page when a filter changes", () => {
    const { result } = renderHook(() => ({
      stack: useCursorStack(),
      status: useFilterParam("status"),
    }));
    act(() => result.current.stack.next("c2"));
    act(() => result.current.status[1]("approved"));
    expect(result.current.stack.cursor).toBeUndefined();
    expect(result.current.stack.canGoBack).toBe(false);
    expect(result.current.status[0]).toBe("approved");
  });
});
