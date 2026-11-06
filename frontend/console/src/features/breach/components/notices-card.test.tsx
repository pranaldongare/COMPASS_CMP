/**
 * Send waits for the breach to be recorded (S3-06), and says so in the
 * server's words: an incident still being validated may have its notice
 * drafted and approved, never sent. There is one button, which names who it
 * reaches and says what happens before anything goes (2026-11-06). An updated
 * draft does not take the button away: it stays for the version last approved,
 * and says which. A first draft is cut to what a notice holds, and says so.
 */
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";

import { NoticesCard } from "@/features/breach/components/notices-card";
import { render, screen, waitFor, within } from "@/test/render";
import { API, server } from "@/test/server";
import type { Breach, BreachNotices } from "@/types";

vi.mock("@/providers", () => ({
  useToast: () => ({ success: vi.fn(), error: vi.fn() }),
}));

const UUID = "44444444-4444-4444-8444-444444444444";
const REASON =
  "Record the breach before anyone is notified: validate it as a personal data breach first";

const breach = { breach_uuid: UUID, status: "open" } as Breach;

const NOTICE = "55555555-5555-4555-8555-555555555555";
const DRAFT = "66666666-6666-4666-8666-666666666666";
const WORDS = {
  what_happened: "w",
  consequences: "c",
  measures: "m",
  protective_steps: "p",
  contact: "o",
};
const CONTENTS = [
  { key: "what_happened", label: "What happened" },
  { key: "consequences", label: "What may follow" },
  { key: "measures", label: "What is being done" },
  { key: "protective_steps", label: "What you can do" },
  { key: "contact", label: "Who to ask" },
] as BreachNotices["contents"];

const approved = {
  notice_uuid: NOTICE,
  version: 1,
  state: "approved",
  ...WORDS,
  created_at: "2026-10-05T10:00:00Z",
  approved_at: "2026-10-05T10:05:00Z",
  approved_by_name: "Priya Menon",
};
const draft = { ...approved, notice_uuid: DRAFT, version: 2, state: "draft", approved_at: null, approved_by_name: null };

const withVersions = (...versions: unknown[]) => ({
  versions: versions as BreachNotices["versions"],
  contents: CONTENTS,
});

function notices(over: Partial<BreachNotices>): BreachNotices {
  return {
    versions: [approved] as unknown as BreachNotices["versions"],
    account: [],
    failures: [],
    listed: 3,
    contacts: 0,
    unnotified: 3,
    contents: [],
    duty: "Principals notified",
    send_blocked_by: null,
    ...over,
  };
}

function serve(body: BreachNotices) {
  server.use(http.get(`${API}/breaches/${UUID}/notices`, () => HttpResponse.json(body)));
}

describe("NoticesCard", () => {
  it("holds Send while the incident is not recorded, and says why", async () => {
    serve(notices({ send_blocked_by: REASON }));
    render(<NoticesCard breach={breach} />);

    const send = await screen.findByRole("button", { name: "Send to all 3 affected people" });
    expect(send).toBeDisabled();
    expect(screen.getByText(REASON)).toBeInTheDocument();
  });

  it("offers Send once the breach is recorded", async () => {
    serve(notices({ send_blocked_by: null }));
    render(<NoticesCard breach={breach} />);

    expect(await screen.findByRole("button", { name: "Send to all 3 affected people" })).toBeEnabled();
    expect(screen.queryByText(REASON)).not.toBeInTheDocument();
  });

  it("says one person in the singular", async () => {
    serve(notices({ listed: 1, unnotified: 1 }));
    render(<NoticesCard breach={breach} />);

    expect(await screen.findByRole("button", { name: "Send to 1 affected person" })).toBeEnabled();
  });

  it("says exactly what happens, and sends only once that is agreed to", async () => {
    let sends = 0;
    serve(notices({}));
    server.use(
      http.post(`${API}/breaches/${UUID}/notices/send`, () => {
        sends += 1;
        return HttpResponse.json(notices({ unnotified: 0 }));
      }),
    );
    const { user } = render(<NoticesCard breach={breach} />);

    await user.click(await screen.findByRole("button", { name: "Send to all 3 affected people" }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText(/has not yet had version 1 is emailed/)).toBeInTheDocument();
    expect(within(dialog).getByText(/sent an SMS\s+where a mobile number is on file/)).toBeInTheDocument();
    expect(within(dialog).getByText(/in the account of anyone who has one/)).toBeInTheDocument();
    expect(within(dialog).getByText(/A second press never sends twice/)).toBeInTheDocument();
    expect(sends).toBe(0);

    await user.click(within(dialog).getByRole("button", { name: "Cancel" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(sends).toBe(0);

    await user.click(screen.getByRole("button", { name: "Send to all 3 affected people" }));
    await user.click(
      within(await screen.findByRole("dialog")).getByRole("button", { name: "Send to all 3 affected people" }),
    );
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(sends).toBe(1);
  });

  it("asks for the people first, in plain words", async () => {
    serve(notices({ listed: 0, unnotified: 0 }));
    render(<NoticesCard breach={breach} />);

    expect(await screen.findByText("Notice to the affected people")).toBeInTheDocument();
    expect(await screen.findByText("Nobody is listed as affected yet.")).toBeInTheDocument();
    expect(screen.getByText("Confirm the affected people first")).toBeInTheDocument();
    expect(screen.getByText("A notice goes to the people listed under Affected people.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send to the affected people" })).toBeDisabled();
    expect(document.body.textContent).not.toMatch(/touched/i);
  });

  describe("beside an updated draft", () => {
    const open = notices(withVersions(approved, draft));
    const label = "Send version 1 to all 3 affected people";

    it("keeps the button for the version approved, and names it", async () => {
      let sends = 0;
      serve(open);
      server.use(
        http.post(`${API}/breaches/${UUID}/notices/send`, () => {
          sends += 1;
          return HttpResponse.json(open);
        }),
      );
      const { user } = render(<NoticesCard breach={breach} />);

      await user.click(await screen.findByRole("button", { name: label }));
      const dialog = await screen.findByRole("dialog");
      expect(within(dialog).getByText(/has not yet had version 1 is emailed/)).toBeInTheDocument();
      await user.click(within(dialog).getByRole("button", { name: label }));
      await waitFor(() => expect(sends).toBe(1));
      expect(screen.queryByRole("button", { name: "Start an updated notice" })).not.toBeInTheDocument();
    });

    it("shows what that version says, so nobody sends it unread", async () => {
      serve(open);
      render(<NoticesCard breach={breach} />);
      expect(await screen.findByText(/Approved$/)).toBeInTheDocument();
      expect(screen.getByText("Draft")).toBeInTheDocument();
    });

    it("leaves words being typed into the draft where they are", async () => {
      serve(open);
      server.use(http.post(`${API}/breaches/${UUID}/notices/send`, () => HttpResponse.json(open)));
      const { user } = render(<NoticesCard breach={breach} />);

      const box = await screen.findByLabelText(/What happened/);
      await user.type(box, " and more");
      await user.click(screen.getByRole("button", { name: label }));
      await user.click(within(await screen.findByRole("dialog")).getByRole("button", { name: label }));
      await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
      expect(box).toHaveValue("w and more");
    });

    it("offers nothing to send with no version approved", async () => {
      serve(notices(withVersions({ ...draft, version: 1 })));
      render(<NoticesCard breach={breach} />);
      await screen.findByLabelText(/What happened/);
      expect(screen.queryByRole("button", { name: /Send/ })).not.toBeInTheDocument();
    });
  });

  describe("a first draft", () => {
    const assessed = (over: object) =>
      ({ ...breach, assessment: { contact_point: "privacy@example.org", ...over } }) as Breach;

    function serveDrafting() {
      const sent: Record<string, string>[] = [];
      let now = notices(withVersions());
      server.use(
        http.get(`${API}/breaches/${UUID}/notices`, () => HttpResponse.json(now)),
        http.post(`${API}/breaches/${UUID}/notices`, async ({ request }) => {
          sent.push((await request.json()) as Record<string, string>);
          now = notices(withVersions({ ...draft, version: 1 }));
          return HttpResponse.json(now);
        }),
      );
      return sent;
    }

    it("is cut to what a notice holds, not refused, and says what was cut", async () => {
      const sent = serveDrafting();
      const { user } = render(
        <NoticesCard breach={assessed({ nature_extent: "x".repeat(5000), mitigation: "😀".repeat(4001) })} />,
      );

      await user.click(await screen.findByRole("button", { name: "Draft the notice" }));
      const alert = await screen.findByText(/stop at 4,000 characters/);
      expect(sent).toHaveLength(1);
      expect(sent[0].what_happened).toHaveLength(4000);
      // Counted as the API counts: whole characters, none cut in half.
      expect(Array.from(sent[0].measures)).toHaveLength(4000);
      expect(sent[0].measures.endsWith("😀")).toBe(true);
      expect(sent[0].contact).toBe("privacy@example.org");
      expect(alert).toHaveTextContent(/What happened, What is being done\./);
      expect(alert).not.toHaveTextContent(/Who to ask/);
    });

    it("says nothing of cutting when nothing was", async () => {
      const sent = serveDrafting();
      const { user } = render(<NoticesCard breach={assessed({ nature_extent: "x".repeat(4000) })} />);

      await user.click(await screen.findByRole("button", { name: "Draft the notice" }));
      await screen.findByLabelText(/What happened/);
      expect(sent[0].what_happened).toHaveLength(4000);
      expect(screen.queryByText(/stop at/)).not.toBeInTheDocument();
    });
  });

  describe("the draft's boxes", () => {
    const open = notices(withVersions({ ...draft, version: 1 }));

    it("hold no more than a notice can", async () => {
      serve(open);
      render(<NoticesCard breach={breach} />);
      expect(await screen.findByLabelText(/What happened/)).toHaveAttribute("maxlength", "4000");
    });

    it("cannot be typed in while a save is on its way", async () => {
      let answer = () => {};
      serve(open);
      server.use(
        http.put(`${API}/breaches/${UUID}/notices/${DRAFT}`, async () => {
          await new Promise<void>((resolve) => {
            answer = resolve;
          });
          return HttpResponse.json(open);
        }),
      );
      const { user } = render(<NoticesCard breach={breach} />);

      const box = await screen.findByLabelText(/What happened/);
      await user.type(box, "!");
      await user.click(screen.getByRole("button", { name: "Save draft" }));
      await waitFor(() => expect(box).toBeDisabled());
      answer();
      await waitFor(() => expect(box).toBeEnabled());
    });
  });
});
