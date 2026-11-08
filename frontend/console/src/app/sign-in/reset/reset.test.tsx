/**
 * The password reset and invitation page, once a code is cancelled
 * (2026-11-08).
 *
 * `POST /auth/password/reset/confirm` refuses a wrong code, an expired one and
 * one cancelled by its fifth wrong try in the same words, on the Code field,
 * to everybody. The fifth used to answer "Too many incorrect attempts. Request
 * a new code."; now nothing the server says tells the person that the code is
 * gone, and the only way to another was a link named "Use a different
 * address". So the page says, in both modes and to everybody alike, that a
 * code stops working, and sends a new one to the address already shown.
 */
import { describe, expect, it, vi } from "vitest";

import ResetPage from "@/app/sign-in/reset/page";
import { render, screen } from "@/test/render";
import { API, HttpResponse, errorResponse, http, server } from "@/test/server";

const search = { value: "" };
vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(search.value),
  usePathname: () => "/sign-in/reset",
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn(), refresh: vi.fn() }),
}));

const INVITED = "invited@organisation.example";
const HINT =
  "A code stops working once it expires, or after five wrong tries; then send a new one.";
const RESENT = (email: string) =>
  `If ${email} is registered, a new code is on its way, and the earlier one no longer works.`;

function answer() {
  const asked: unknown[] = [];
  server.use(
    http.post(`${API}/auth/password/reset/request`, async ({ request }) => {
      asked.push(await request.json());
      return HttpResponse.json({
        ok: true,
        message: "If that account exists, a reset code has been sent.",
      });
    }),
    http.post(`${API}/auth/password/reset/confirm`, () =>
      errorResponse("otp_invalid", "Invalid or expired code", 400, { field: "code" }),
    ),
  );
  return asked;
}

async function tryCode(user: ReturnType<typeof render>["user"], code: string) {
  await user.type(screen.getByLabelText(/^code/i), code);
  await user.type(screen.getByLabelText(/^new password/i), "a long enough phrase");
  await user.type(screen.getByLabelText(/^confirm new password/i), "a long enough phrase");
  await user.click(screen.getByRole("button", { name: "Set the new password" }));
}

describe("a code that no longer works", () => {
  it("from the invitation: says so to everybody, and sends a new code to the address shown", async () => {
    search.value = `email=${encodeURIComponent(INVITED)}`;
    const asked = answer();
    const { user } = render(<ResetPage />);

    expect(await screen.findByText(HINT)).toBeInTheDocument();
    await tryCode(user, "123456");

    // The server's one refusal, on the field, and the line still beside it.
    expect(await screen.findByText("Invalid or expired code")).toBeInTheDocument();
    expect(screen.getByLabelText(/^code/i)).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByText(HINT)).toBeInTheDocument();
    // Nothing was asked for until the person chose to.
    expect(asked).toEqual([]);

    await user.click(screen.getByRole("button", { name: "Send a new code" }));

    expect(await screen.findByText(RESENT(INVITED))).toBeInTheDocument();
    expect(asked).toEqual([{ email: INVITED }]);
    expect(screen.getByLabelText(/^code/i)).toHaveValue("");
    expect(screen.queryByText("Invalid or expired code")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Set your password" })).toBeInTheDocument();
  });

  it("from a reset: the same line, and the new code goes to the address typed", async () => {
    search.value = "";
    const asked = answer();
    const { user } = render(<ResetPage />);

    await user.type(
      await screen.findByLabelText(/email address/i),
      "staff@organisation.example",
    );
    await user.click(screen.getByRole("button", { name: "Send the code" }));

    expect(await screen.findByText(HINT)).toBeInTheDocument();
    await tryCode(user, "123456");
    expect(await screen.findByText("Invalid or expired code")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Send a new code" }));

    expect(
      await screen.findByText(RESENT("staff@organisation.example")),
    ).toBeInTheDocument();
    expect(asked).toEqual([
      { email: "staff@organisation.example" },
      { email: "staff@organisation.example" },
    ]);
  });

  it("shows the server's words when a new code cannot be sent", async () => {
    search.value = `email=${encodeURIComponent(INVITED)}`;
    server.use(
      http.post(`${API}/auth/password/reset/request`, () =>
        errorResponse("rate_limited", "Too many reset requests.", 429),
      ),
    );
    const { user } = render(<ResetPage />);

    await user.click(await screen.findByRole("button", { name: "Send a new code" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Too many reset requests.");
    expect(screen.queryByText(RESENT(INVITED))).not.toBeInTheDocument();
  });
});
