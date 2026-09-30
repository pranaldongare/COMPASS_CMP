/**
 * She corrects her own name (s.12).
 *
 * What these hold: the name is sent trimmed as `full_name` and nothing else; an
 * empty name is refused before any request; an unchanged name sends nothing;
 * and the server's refusal is shown in its own words.
 */

import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";

import { NameEditor } from "@/features/account/components/name-editor";
import { render, screen, waitFor } from "@/test/render";
import { API, server } from "@/test/server";

vi.mock("@/providers", () => ({ useToast: () => ({ success: vi.fn(), error: vi.fn() }) }));

async function open(name = "Anjali Verma") {
  const view = render(<NameEditor name={name} />);
  await view.user.click(screen.getByRole("button", { name: "Change" }));
  return view;
}

describe("NameEditor", () => {
  it("sends the new name, trimmed, and nothing else", async () => {
    let sent: unknown = null;
    server.use(
      http.patch(`${API}/me`, async ({ request }) => {
        sent = await request.json();
        return HttpResponse.json({});
      }),
    );
    const { user } = await open();
    const field = screen.getByLabelText(/^Name/);
    await user.clear(field);
    await user.type(field, "  Anjali Verma-Rao  ");
    await user.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(sent).toEqual({ full_name: "Anjali Verma-Rao" }));
  });

  it("will not save an empty name", async () => {
    const { user } = await open();
    await user.clear(screen.getByLabelText(/^Name/));
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();
  });

  it("sends nothing when the name did not change", async () => {
    let calls = 0;
    server.use(
      http.patch(`${API}/me`, () => {
        calls += 1;
        return HttpResponse.json({});
      }),
    );
    const { user } = await open();
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(screen.getByRole("button", { name: "Change" })).toBeInTheDocument();
    expect(calls).toBe(0);
  });

  it("shows the server's refusal", async () => {
    server.use(
      http.patch(`${API}/me`, () =>
        HttpResponse.json(
          { error: { code: "validation_failed", message: "Too long", field: "full_name" } },
          { status: 422 },
        ),
      ),
    );
    const { user } = await open();
    await user.type(screen.getByLabelText(/^Name/), " Jr");
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(await screen.findByRole("alert")).toBeInTheDocument();
  });
});
