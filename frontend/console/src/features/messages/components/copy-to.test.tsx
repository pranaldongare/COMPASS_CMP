/**
 * Copy to (2026-10-08): the office sets who a message is copied to, and a
 * message that carries a code, a link or a person's own record says it never
 * is.
 */
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";

import { CopyTo } from "@/features/messages/components/copy-to";
import { render, screen, waitFor } from "@/test/render";
import { API, server } from "@/test/server";
import type { MessageTemplate } from "@/types";

vi.mock("@/providers", () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn() }),
}));

const message = (over: Partial<MessageTemplate>): MessageTemplate => ({
  key: "project_submitted",
  title: "A project is waiting for approval",
  description: "d",
  group: "Projects",
  variables: [],
  channels: [],
  copyable: true,
  attachable: false,
  copies: [],
  ...over,
});

describe("CopyTo", () => {
  it("saves the addresses, one per line", async () => {
    let sent: unknown = null;
    server.use(
      http.put(`${API}/messages/project_submitted/copies`, async ({ request }) => {
        sent = await request.json();
        return HttpResponse.json(message({ copies: [{ email: "approvals@example.org" }] }));
      }),
    );
    const { user } = render(<CopyTo message={message({})} />);
    await user.type(screen.getByLabelText(/Copy to/), "approvals@example.org\nteam@example.org");
    await user.click(screen.getByRole("button", { name: /Save copies/ }));
    await waitFor(() =>
      expect(sent).toEqual({ addresses: ["approvals@example.org", "team@example.org"] }),
    );
  });

  it("says why a message with a code is never copied", () => {
    render(<CopyTo message={message({ key: "mfa_code", copyable: false })} />);
    expect(screen.getByText(/Never copied/)).toBeInTheDocument();
    expect(screen.queryByLabelText(/Copy to/)).not.toBeInTheDocument();
  });

  it("says when the platform's settings copy it too, by count", () => {
    render(<CopyTo message={message({ deployment_copies: 2 })} />);
    expect(screen.getByText(/also copied to 2 addresses/i)).toBeInTheDocument();
  });

  it("says nothing of the platform's copies when there are none", () => {
    render(<CopyTo message={message({ deployment_copies: 0 })} />);
    expect(screen.queryByText(/also copied to/i)).not.toBeInTheDocument();
  });

  it("warns in test mode that the message goes only to the redirect addresses", () => {
    render(<CopyTo message={message({ copyable: false, redirected_to: 1 })} />);
    expect(screen.getByText(/test mode: this message goes only to the 1 address/i)).toBeInTheDocument();
  });
});
