/**
 * Ending somebody's access asks first (2026-11-12): it happens at once, a
 * member of staff is emailed, and staff access is not given back from the
 * console. The pop-up says what they lose; Cancel changes nothing.
 */
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";

import { useAccountActions } from "@/features/users/components/account-actions";
import { makeUser } from "@/test/fixtures";
import { render, screen, within } from "@/test/render";
import { API, server } from "@/test/server";
import type { User } from "@/types";

vi.mock("@/providers", () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn() }),
  useAuth: () => ({ me: { role: "admin", uuid: "00000000-0000-4000-8000-000000000001" } }),
}));

function Actions({ user }: { user: User }) {
  const account = useAccountActions();
  return (
    <>
      {account.actionsFor(user).map((a) => (
        <button key={a.label} type="button" onClick={a.onSelect}>
          {a.label}
        </button>
      ))}
      {account.dialogs}
    </>
  );
}

const UUID = "99999999-9999-4999-8999-999999999999";

describe("ending access", () => {
  it("asks before staff access ends, says what is lost and that they are emailed, and does nothing on Cancel", async () => {
    let ended = 0;
    server.use(
      http.post(`${API}/users/${UUID}/deactivate`, () => {
        ended += 1;
        return HttpResponse.json({ message: "Staff access ended." });
      }),
    );
    const { user } = render(
      <Actions user={makeUser({ uuid: UUID, full_name: "Kavya Rao", role: "dco", status: "active" })} />,
    );

    await user.click(screen.getByRole("button", { name: "End staff access" }));
    const question = await screen.findByRole("dialog", { name: "End staff access for Kavya Rao?" });
    expect(within(question).getByText(/They are emailed that their staff access has ended\./)).toBeInTheDocument();
    expect(within(question).getByText(/staff access is not given back from here/)).toBeInTheDocument();
    await user.click(within(question).getByRole("button", { name: "Cancel" }));
    await vi.waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(ended).toBe(0);

    await user.click(screen.getByRole("button", { name: "End staff access" }));
    await user.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "End staff access" }));
    await vi.waitFor(() => expect(ended).toBe(1));
  });

  it("ends an invited account that never signed in, and does not activate it", async () => {
    // "End staff access" on a pending account used to call reactivate.
    const called: string[] = [];
    server.use(
      http.post(`${API}/users/${UUID}/deactivate`, () => {
        called.push("deactivate");
        return HttpResponse.json({ message: "Staff access ended." });
      }),
      http.post(`${API}/users/${UUID}/reactivate`, () => {
        called.push("reactivate");
        return HttpResponse.json({});
      }),
    );
    const { user } = render(
      <Actions user={makeUser({ uuid: UUID, full_name: "Kavya Rao", role: "rco", status: "pending" })} />,
    );
    await user.click(screen.getByRole("button", { name: "End staff access" }));
    await user.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "End staff access" }));
    await vi.waitFor(() => expect(called).toEqual(["deactivate"]));
  });

  it("says a data principal's account can be reactivated", async () => {
    const { user } = render(
      <Actions user={makeUser({ uuid: UUID, full_name: "Meera Iyer", role: "data_subject", status: "active" })} />,
    );
    await user.click(screen.getByRole("button", { name: "Deactivate" }));
    const question = await screen.findByRole("dialog", { name: "Deactivate Meera Iyer's account?" });
    expect(within(question).getByText(/the account can be reactivated/)).toBeInTheDocument();
  });
});
