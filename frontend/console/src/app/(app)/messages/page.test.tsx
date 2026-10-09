/**
 * Message templates, found rather than scrolled to (2026-10-09): categories
 * with their counts, a search, a channel and "changed from the default", and
 * an index that jumps to a message.
 */
import { HttpResponse, http } from "msw";
import { beforeEach, describe, expect, it, vi } from "vitest";

import MessagesPage from "@/app/(app)/messages/page";
import { render, screen, within } from "@/test/render";
import { API, server } from "@/test/server";
import type { MessageTemplate } from "@/types";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(window.location.search),
  usePathname: () => window.location.pathname,
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
}));

vi.mock("@/providers", () => ({
  useAuth: () => ({ me: null }),
  useToast: () => ({ success: vi.fn(), error: vi.fn(), warning: vi.fn() }),
}));

function message(key: string, title: string, group: string, opts: { sms?: boolean; customised?: boolean } = {}): MessageTemplate {
  const channel = (c: "email" | "sms") => ({
    channel: c,
    default_subject: c === "email" ? title : null,
    default_body: "Hello",
    subject: c === "email" ? title : null,
    body: "Hello",
    customised: Boolean(opts.customised) && c === "email",
    updated_at: null,
    updated_by_name: null,
  });
  return {
    key,
    title,
    description: `About ${title.toLowerCase()}`,
    group,
    copyable: false,
    attachable: false,
    copies: [],
    variables: [],
    channels: opts.sms ? [channel("email"), channel("sms")] : [channel("email")],
  };
}

const MESSAGES = [
  message("staff_otp", "Staff sign-in code", "Sign-in", { sms: true }),
  message("password_reset", "Password reset code", "Sign-in"),
  message("consent_receipt", "Consent receipt", "Consent", { customised: true }),
  message("rights_ack", "Rights request acknowledged", "Rights"),
];

beforeEach(() => {
  window.history.replaceState(null, "", "/messages");
  server.use(http.get(`${API}/messages`, () => HttpResponse.json(MESSAGES)));
});

describe("Message templates", () => {
  it("opens on its categories, each counted, and an index of every message", async () => {
    render(<MessagesPage />);

    const categories = await screen.findByRole("navigation", { name: "Message categories" });
    expect(within(categories).getByRole("button", { name: /All\s*4/ })).toHaveAttribute("aria-pressed", "true");
    expect(within(categories).getByRole("button", { name: /Sign-in\s*2/ })).toBeInTheDocument();
    const index = screen.getByRole("navigation", { name: "Messages on this page" });
    expect(within(index).getByRole("link", { name: "Consent receipt" })).toHaveAttribute(
      "href",
      "#message-consent_receipt",
    );
    expect(screen.getByText("4 messages in 3 categories")).toBeInTheDocument();
  });

  it("narrows to a category, kept in the address", async () => {
    const { user } = render(<MessagesPage />);
    await user.click(await screen.findByRole("button", { name: /Sign-in\s*2/ }));

    expect(new URLSearchParams(window.location.search).get("group")).toBe("Sign-in");
    expect(screen.getByText("2 of 4 messages")).toBeInTheDocument();
    expect(screen.queryByText("Consent receipt", { selector: "h3" })).toBeNull();
  });

  it("finds by words, by channel and by changed words, and clears", async () => {
    const { user } = render(<MessagesPage />);
    await user.type(await screen.findByLabelText("Find a message"), "receipt{Enter}");
    expect(await screen.findByText("1 of 4 messages")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Clear filters" }));
    await user.selectOptions(screen.getByLabelText("Sent by"), "sms");
    expect(await screen.findByText("1 of 4 messages")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Staff sign-in code" })).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Sent by"), "");
    await user.selectOptions(screen.getByLabelText("Words"), "changed");
    expect(await screen.findByText("1 of 4 messages")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Consent receipt" })).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Words"), "default");
    expect(await screen.findByText("3 of 4 messages")).toBeInTheDocument();
  });

  it("says so when nothing matches", async () => {
    const { user } = render(<MessagesPage />);
    await user.type(await screen.findByLabelText("Find a message"), "nothing like this{Enter}");
    expect(await screen.findByText(/No message matches these filters/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Show every message" }));
    expect(await screen.findByText("4 messages in 3 categories")).toBeInTheDocument();
  });
});
