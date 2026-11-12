/**
 * The second half of the public rights form: the code, against the reference.
 * A wrong code, a spent one and one never sent are answered alike (review
 * 2026-11-08): after five wrong tries the server discards the code and says
 * only "Invalid or expired code", so the form says how to get a new one, in
 * words true for anybody, and never whether the contact is known.
 */
import { describe, expect, it, vi } from "vitest";

import { NEW_CODE, VerifyForm } from "@/features/rights/components/verify-form";
import { render, screen } from "@/test/render";
import { API, errorResponse, HttpResponse, http, server } from "@/test/server";

const REFERENCE = "RR-2026-000123";

function refusing() {
  const tries = { n: 0 };
  server.use(
    http.post(`${API}/rights/requests/verify`, () => {
      tries.n += 1;
      return errorResponse("otp_invalid", "Invalid or expired code", 400, {
        field: "code",
      });
    }),
  );
  return tries;
}

describe("VerifyForm", () => {
  it("says how to get a new code once a code is refused, and offers the request again", async () => {
    const tries = refusing();
    const onNewRequest = vi.fn();
    const { user } = render(
      <VerifyForm reference={REFERENCE} onDone={() => {}} onNewRequest={onNewRequest} />,
    );
    expect(screen.queryByText(NEW_CODE)).not.toBeInTheDocument();

    await user.type(screen.getByLabelText(/the code we sent/i), "000000");
    await user.click(screen.getByRole("button", { name: "Verify identity" }));

    expect(await screen.findByText("Invalid or expired code")).toBeInTheDocument();
    expect(screen.getByText(NEW_CODE)).toBeInTheDocument();
    // Where a new code goes, as the server's reply says: the contact held,
    // which for an account is its email whichever contact was typed.
    expect(
      screen.getByText(
        /if we hold records for the contact you gave, a new code is sent to the contact we hold for you\.$/,
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText(/a new code is sent to it\./)).not.toBeInTheDocument();
    expect(tries.n).toBe(1);
    await user.click(screen.getByRole("button", { name: "Make the request again" }));
    expect(onNewRequest).toHaveBeenCalledTimes(1);
  });

  it("says the same after the fifth wrong code as after the first, and names no contact", async () => {
    const tries = refusing();
    const { user } = render(<VerifyForm reference={REFERENCE} onDone={() => {}} />);
    const code = screen.getByLabelText(/the code we sent/i);

    for (let i = 0; i < 6; i += 1) {
      await user.clear(code);
      await user.type(code, `00000${i}`);
      await user.click(screen.getByRole("button", { name: "Verify identity" }));
      await vi.waitFor(() => expect(tries.n).toBe(i + 1));
      expect(await screen.findByText(NEW_CODE)).toBeInTheDocument();
    }
    // No "too many" of its own, and nothing that says a code was sent.
    expect(document.body).not.toHaveTextContent(
      /too many incorrect|we sent you a code|your account/i,
    );
    // Without a way back given, it offers none of its own.
    expect(
      screen.queryByRole("button", { name: "Make the request again" }),
    ).not.toBeInTheDocument();
  });

  it("says nothing of a new code when the code is accepted", async () => {
    server.use(
      http.post(`${API}/rights/requests/verify`, () =>
        HttpResponse.json({
          ok: true,
          reference: REFERENCE,
          message: "Thank you, your identity is verified.",
        }),
      ),
    );
    const onDone = vi.fn();
    const { user } = render(<VerifyForm reference={REFERENCE} onDone={onDone} />);

    await user.type(screen.getByLabelText(/the code we sent/i), "123456");
    await user.click(screen.getByRole("button", { name: "Verify identity" }));

    await vi.waitFor(() => expect(onDone).toHaveBeenCalled());
    expect(screen.queryByText(NEW_CODE)).not.toBeInTheDocument();
  });
});
