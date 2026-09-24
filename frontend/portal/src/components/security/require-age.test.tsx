/**
 * The age question, asked at the next sign-in (S2-01).
 *
 * What these hold: an unknown age is asked before any other page; the two
 * pages a person must always reach - withdrawing and making a request - stay
 * open with a reminder; a known age, adult or not, asks nothing; and the answer
 * goes to `PATCH /me` and the session is re-read.
 */

import { HttpResponse, http } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { RequireAge } from "@/components/security/require-age";
import { makeMe } from "@/test/fixtures";
import { render, screen, waitFor } from "@/test/render";
import { API, server } from "@/test/server";
import type { Me } from "@/types";

const refresh = vi.fn();
let currentMe: Me | null = makeMe();
let pathname = "/";

vi.mock("@/providers", () => ({
  useAuth: () => ({ me: currentMe, refresh }),
}));
vi.mock("next/navigation", () => ({ usePathname: () => pathname }));

beforeEach(() => {
  refresh.mockReset();
  pathname = "/";
});

describe("RequireAge", () => {
  it("asks an unknown age before showing the page", () => {
    currentMe = makeMe({ is_minor: null });
    render(
      <RequireAge>
        <p>Your notifications</p>
      </RequireAge>,
    );
    expect(screen.getByRole("heading", { name: /your date of birth/i })).toBeInTheDocument();
    expect(screen.queryByText("Your notifications")).not.toBeInTheDocument();
  });

  it.each(["/my-consents", "/my-consents/abc", "/my-requests"])(
    "leaves %s open, with a reminder",
    (path) => {
      pathname = path;
      currentMe = makeMe({ is_minor: null });
      render(
        <RequireAge>
          <p>The page</p>
        </RequireAge>,
      );
      expect(screen.getByText("The page")).toBeInTheDocument();
      expect(screen.getByText(/we need your date of birth/i)).toBeInTheDocument();
      // To a page that asks. The home page only redirects to My consents.
      expect(screen.getByRole("link", { name: /add it now/i })).toHaveAttribute("href", "/account");
    },
  );

  it.each([false, true])("asks nothing when the age is known (is_minor %s)", (isMinor) => {
    currentMe = makeMe({ is_minor: isMinor });
    render(
      <RequireAge>
        <p>The page</p>
      </RequireAge>,
    );
    expect(screen.getByText("The page")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /date of birth/i })).not.toBeInTheDocument();
  });

  it("says nothing about a guardian", () => {
    currentMe = makeMe({ is_minor: null });
    render(
      <RequireAge>
        <p>x</p>
      </RequireAge>,
    );
    expect(document.body.textContent?.toLowerCase()).not.toMatch(/guardian|parent/);
  });

  it("saves the answer to /me and re-reads the session", async () => {
    currentMe = makeMe({ is_minor: null });
    let sent: unknown = null;
    server.use(
      http.patch(`${API}/me`, async ({ request }) => {
        sent = await request.json();
        return HttpResponse.json({});
      }),
    );
    const { user } = render(
      <RequireAge>
        <p>x</p>
      </RequireAge>,
    );

    await user.type(screen.getByLabelText(/date of birth/i), "1990-05-17");
    await user.click(screen.getByRole("button", { name: /save and continue/i }));

    await waitFor(() => expect(refresh).toHaveBeenCalled());
    expect(sent).toEqual({ dob: "1990-05-17" });
  });

  it("refuses a date in the future before sending it", async () => {
    currentMe = makeMe({ is_minor: null });
    const patched = vi.fn();
    server.use(
      http.patch(`${API}/me`, () => {
        patched();
        return HttpResponse.json({});
      }),
    );
    const { user } = render(
      <RequireAge>
        <p>x</p>
      </RequireAge>,
    );

    await user.type(screen.getByLabelText(/date of birth/i), "2999-01-01");
    await user.click(screen.getByRole("button", { name: /save and continue/i }));

    expect(await screen.findByText(/must be in the past/i)).toBeInTheDocument();
    expect(patched).not.toHaveBeenCalled();
  });
});
