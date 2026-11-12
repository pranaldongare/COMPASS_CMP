/**
 * My consents: a list, and the one chosen beside it (2026-11-12, mock-up B).
 *
 * Withdrawing one purpose is not withdrawing the consent. The record it writes
 * is marked as a withdrawal - that is the act - but while anything is still
 * granted it reads Partial and can still be withdrawn from here.
 *
 * The page was a card per consent with four buttons and two panels that
 * opened inside it. It is now a list; the chosen consent shows its purposes,
 * notice and history as tabs, in fewer words - "View notice" was "Show the
 * exact notice I was given". Withdrawing asks first, one purpose or all.
 */
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";

import MyConsentsPage from "@/app/(app)/my-consents/page";
import { ToastProvider } from "@/providers/toast-provider";
import { render, screen, within } from "@/test/render";
import { API, server } from "@/test/server";
import type { MyConsent } from "@/types";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(window.location.search),
  usePathname: () => "/my-consents",
}));

const GAIT = "11111111-1111-4111-8111-111111111111";
const SPEECH = "44444444-4444-4444-8444-444444444444";
const TRAINING = "55555555-5555-4555-8555-555555555555";

function consent(overrides: Partial<MyConsent>): MyConsent {
  return {
    consent_uuid: GAIT,
    project_uuid: "22222222-2222-4222-8222-222222222222",
    project_name: "Gait Identification Study 2026",
    notice_uuid: "33333333-3333-4333-8333-333333333333",
    notice_code: "NTC-GAIT-2026",
    version: 1,
    language_code: "english",
    affirmative_action_at: "2026-09-20T10:00:00Z",
    is_withdrawal: false,
    granted_count: 2,
    purpose_count: 2,
    ...overrides,
  } as MyConsent;
}

const grants = [
  {
    purpose_uuid: TRAINING,
    name: "Gait model training",
    description: "Train and evaluate gait recognition models.",
    granted: true,
    data_categories: ["video"],
    retention_period: "P3Y",
  },
  {
    purpose_uuid: "66666666-6666-4666-8666-666666666666",
    name: "Benchmark publication",
    description: "Publish benchmark results.",
    granted: false,
    data_categories: ["gait_signature"],
    retention_period: "P5Y",
  },
];

function serve(...consents: MyConsent[]) {
  server.use(
    http.get(`${API}/me/consents`, () => HttpResponse.json(consents)),
    http.get(`${API}/me/consents/:uuid/grants`, () => HttpResponse.json(grants)),
    // The page's other panels, empty: not what is under test.
    http.get(`${API}/me/disclosures`, () => HttpResponse.json([])),
    http.get(`${API}/me/nominations`, () => HttpResponse.json([])),
    http.get(`${API}/me/nominee-of`, () => HttpResponse.json([])),
    http.get(`${API}/me/requests`, () => HttpResponse.json([])),
  );
}

function page() {
  return render(
    <ToastProvider>
      <MyConsentsPage />
    </ToastProvider>,
  );
}

/** The chosen consent, beside the list. */
function detail(): HTMLElement {
  return document.getElementById("consent-detail") as HTMLElement;
}

/** The same, once the consents have loaded and one is beside the list. */
async function loaded(): Promise<ReturnType<typeof within>> {
  await screen.findByRole("list", { name: "Your consents" });
  return within(detail());
}

describe("My consents", () => {
  it("reads a one-of-two withdrawal as Partial, and still offers to withdraw the rest", async () => {
    serve(consent({ is_withdrawal: true, granted_count: 1, purpose_count: 2 }));
    page();
    const row = await screen.findByRole("button", { name: /gait identification study 2026/i });
    expect(row).toHaveTextContent(/partial/i);
    expect(row).toHaveTextContent("1 of 2 purposes");
    expect(row).not.toHaveTextContent(/withdrawn/i);
    expect(within(detail()).getByRole("button", { name: "Withdraw consent" })).toBeInTheDocument();
  });

  it("reads a withdrawal that left nothing as Withdrawn, with nothing left to withdraw", async () => {
    serve(consent({ is_withdrawal: true, granted_count: 0, purpose_count: 2 }));
    page();
    const row = await screen.findByRole("button", { name: /gait identification study 2026/i });
    expect(row).toHaveTextContent(/withdrawn/i);
    expect(row).toHaveTextContent("0 of 2 purposes");
    expect(within(detail()).queryByRole("button", { name: /^withdraw/i })).not.toBeInTheDocument();
  });

  it("says it could not load where her data was shared, never that it was shared with nobody", async () => {
    serve(consent({}));
    let calls = 0;
    server.use(
      http.get(`${API}/me/disclosures`, () => {
        calls += 1;
        return calls === 1
          ? HttpResponse.json({ error: { code: "internal_error", message: "Down" } }, { status: 500 })
          : HttpResponse.json([]);
      }),
    );
    const { user } = page();
    await user.click(await screen.findByRole("button", { name: /data sharing/i }));
    expect(await screen.findByText(/could not load where your data was shared/i)).toBeInTheDocument();
    expect(screen.queryByText("No sharing recorded")).not.toBeInTheDocument();

    // Asked again, and answered: only now may it say nobody.
    await user.click(screen.getByRole("button", { name: /try again/i }));
    expect(await screen.findByText("No sharing recorded")).toBeInTheDocument();
  });

  it("opens the consent a link names (UX review 2026-10-05)", async () => {
    // A request "about one consent only" linked to the top of this page.
    serve(
      consent({}),
      consent({ consent_uuid: SPEECH, project_name: "Hindi Speech Corpus", notice_code: "NTC-HSC" }),
    );
    window.history.replaceState(null, "", `/my-consents?consent=${SPEECH}`);
    page();
    const named = await screen.findByRole("button", { name: /hindi speech corpus/i });
    expect(named).toHaveAttribute("aria-current", "true");
    expect(within(detail()).getByRole("heading", { name: "Hindi Speech Corpus" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /gait identification study 2026/i })).not.toHaveAttribute(
      "aria-current",
    );
    window.history.replaceState(null, "", "/");
  });

  it("shows the first consent beside the list, and another when it is chosen", async () => {
    serve(
      consent({}),
      consent({ consent_uuid: SPEECH, project_name: "Hindi Speech Corpus", notice_code: "NTC-HSC" }),
    );
    const { user } = page();
    expect(
      (await loaded()).getByRole("heading", { name: "Gait Identification Study 2026" }),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /hindi speech corpus/i }));
    expect(within(detail()).getByRole("heading", { name: "Hindi Speech Corpus" })).toBeInTheDocument();
    expect(within(detail()).getByText(/NTC-HSC v1 · English · given/)).toBeInTheDocument();
  });

  it("keeps the purposes, the notice and the history on three tabs, in short words", async () => {
    serve(consent({}));
    server.use(
      http.get(`${API}/me/consents/${GAIT}/notice`, () =>
        HttpResponse.json({
          rendered_text: "We record how you walk.",
          notice_content_hash: "ab".repeat(32),
          served_at: "2026-09-20T09:58:00Z",
          integrity: "",
          hash_matches: true,
        }),
      ),
      http.get(`${API}/me/consents/${GAIT}/trail`, () => HttpResponse.json([])),
    );
    const { user } = page();
    const panel = await loaded();
    expect(await panel.findByText("Gait model training")).toBeInTheDocument();
    expect(panel.getByRole("tab", { name: /purposes/i })).toHaveAttribute("aria-selected", "true");
    expect(panel.getByRole("button", { name: "Download record" })).toBeInTheDocument();
    // The long labels are gone.
    for (const old of [/exact notice i was given/i, /what was recorded/i, /withdraw everything/i, /just this one/i]) {
      expect(screen.queryByText(old)).not.toBeInTheDocument();
    }

    await user.click(panel.getByRole("tab", { name: "Notice" }));
    expect(await panel.findByText("We record how you walk.")).toBeInTheDocument();
    expect(panel.getByText("Integrity verified")).toBeInTheDocument();

    await user.click(panel.getByRole("tab", { name: "History" }));
    expect(await panel.findByText("Every change to this consent, oldest first.")).toBeInTheDocument();
  });

  it("asks before withdrawing one purpose, and withdraws only that one", async () => {
    let sent: unknown = null;
    serve(consent({}));
    server.use(
      http.post(`${API}/me/consents/${GAIT}/withdraw`, async ({ request }) => {
        sent = await request.json();
        return HttpResponse.json({
          consent_uuid: SPEECH,
          supersedes: GAIT,
          withdrawn_at: "2026-11-12T10:00:00Z",
          stopped: ["Gait model training"],
          continuing: [],
          continuing_under_other_basis: [],
          note: "",
        });
      }),
    );
    const { user } = page();
    const panel = await loaded();
    await user.click(await panel.findByRole("button", { name: "Withdraw Gait model training" }));
    // Asked first; Cancel leaves it as it was.
    expect(panel.getByText("Withdraw “Gait model training”?")).toBeInTheDocument();
    await user.click(panel.getByRole("button", { name: "Cancel" }));
    expect(sent).toBeNull();

    await user.click(panel.getByRole("button", { name: "Withdraw Gait model training" }));
    await user.click(panel.getByRole("button", { name: "Withdraw" }));
    await vi.waitFor(() => expect(sent).toEqual({ purposes: [TRAINING] }));
  });
});
